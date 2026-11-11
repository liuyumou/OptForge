"""Independent CPU contracts for SPEC-0025; no numerical libraries or devices."""

from copy import deepcopy
from fractions import Fraction as F
import itertools
import json
from pathlib import Path
import random
import struct
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
import lp_fp4_contract as c
import lp_fp4_protocol as p


def checkpoint():
    block = c.encode([F(1, 2), -1] + [0] * 30, 4)
    return dict(schema_version=1, kind='lp-fp4-checkpoint',
                binding={k: ch * 64 for k, ch in zip(('model', 'operator', 'settings', 'proposal'), 'abcd')},
                rows=2, columns=2, components=4, generation=3,
                vectors={k: [deepcopy(block)] for k in ('x', 'y', 'bar', 'anchor_x', 'anchor_y')},
                errors={k: c.rational(0) for k in ('x', 'y', 'bar', 'anchor_x', 'anchor_y')},
                controller=dict(weight=c.float_bits(1), integral=c.float_bits(-0.0),
                                previous_error=None, anchor_error=c.float_bits(1),
                                last_check_error=c.float_bits(1), iterations=0, restarts=0,
                                since_restart=0, checked_iteration=0))


def candidate():
    result = checkpoint()
    result['controller']['iterations'] = 200
    result['controller']['since_restart'] = 200
    result['vectors']['x'][0] = c.encode([F(3, 4), -F(1, 2)] + [0] * 30, 4)
    return result


def synthetic_cost():
    # Explicit synthetic arithmetic fixture, never passed as retained evidence.
    return dict(trial_id='synthetic', total_ns=1000,
                phases_ns=dict(import_=0), accepted=True, candidate=None)


class RepresentationContracts(unittest.TestCase):
    def test_all_codes_and_signed_zero_policy(self):
        expected = [F(0), F(1, 2), F(1), F(3, 2), F(2), F(3), F(4), F(6)]
        self.assertEqual([c.code_value(i) for i in range(8)], expected)
        self.assertEqual([c.code_value(i) for i in range(9, 16)], [-x for x in expected[1:]])
        for bad in (8, -1, 16, True, 1.0):
            with self.assertRaises(c.ContractError):
                c.code_value(bad)
        self.assertEqual(c.nearest_code(-0.0), 0)

    def test_all_rounding_ties_and_neighbors(self):
        expected = [F(0), F(1, 2), F(1), F(3, 2), F(2), F(3), F(4), F(6)]
        for i in range(7):
            middle = (expected[i] + expected[i + 1]) / 2
            even = i if i % 2 == 0 else i + 1
            for sign in (1, -1):
                self.assertEqual(c.nearest_code(sign * middle), even | (8 if sign < 0 and even else 0))
            self.assertEqual(c.nearest_code(middle - F(1, 1024)), i)
            self.assertEqual(c.nearest_code(middle + F(1, 1024)), i + 1)

    def test_packing_order_padding_and_malformed_bytes(self):
        self.assertEqual(c.pack([1, 2, 15]), '210f')
        self.assertEqual(c.unpack('210f', 3), [1, 2, 15])
        for data in ('21ff', '210F', '21 0f', '21', '2180'):
            with self.assertRaises(c.ContractError):
                c.unpack(data, 3)

    def test_residual_bound_against_independent_sum(self):
        rng = random.Random(37)
        values = [F(rng.randrange(-100000, 100000), 1 << rng.randrange(0, 20)) for _ in range(32)]
        previous = None
        for count in (2, 4, 8):
            block = c.encode(values, count)
            decoded = c.decode(block)
            errors = [abs(x - y) for x, y in zip(values, decoded)]
            self.assertEqual(c.read_rational(block['remainder_bound']), max(errors))
            if previous is not None:
                self.assertLessEqual(max(errors), previous)
            previous = max(errors)
            # The encoder's bound encloses the actual original values.
            self.assertTrue(all(abs(x - y) <= previous for x, y in zip(values, decoded)))

    def test_scale_tail_and_range_refusal(self):
        tiny = F(1, 1 << 1074)
        block = c.encode([tiny], 8)
        self.assertEqual(c.decode(block), [0])
        self.assertEqual(c.read_rational(block['remainder_bound']), tiny)
        self.assertEqual(c.decode(c.encode([6 * (1 << 48)], 2)), [6 * (1 << 48)])
        for bad in (6 * (1 << 48) + 1, float('nan'), float('inf'), True):
            with self.assertRaises(c.ContractError):
                c.encode([bad], 2)

    def test_rational_canonicality_and_parser_bounds(self):
        for value in ({'numerator': '2', 'denominator': '4'}, {'numerator': '0', 'denominator': '0'},
                      {'numerator': '01', 'denominator': '1'}, {'numerator': '١', 'denominator': '1'},
                      {'numerator': '1' * 401, 'denominator': '1'}):
            with self.assertRaises(c.ContractError):
                c.read_rational(value)

    def test_transpose_reuses_scales_and_exact_operator(self):
        original = [F(((r + 3) * (j + 5)) % 71 - 35, 13) for r in range(32) for j in range(32)]
        block = c.encode(original, 4)
        transposed = c.transpose_tile(block)
        values = c.decode(block)
        self.assertEqual(c.decode(transposed), [values[j * 32 + r] for r in range(32) for j in range(32)])
        self.assertEqual([v['exponent'] for v in block['planes']], [v['exponent'] for v in transposed['planes']])
        self.assertEqual(c.transpose_tile(transposed), block)
        x, y = list(range(32)), [(-1) ** i for i in range(32)]
        tvalues = c.decode(transposed)
        ax_y = sum(y[r] * sum(values[r * 32 + j] * x[j] for j in range(32)) for r in range(32))
        aty_x = sum(x[j] * sum(tvalues[j * 32 + r] * y[r] for r in range(32)) for j in range(32))
        self.assertEqual(ax_y, aty_x)

    def test_matrix_error_is_row_sum_and_column_sum(self):
        original = [F(1, 3)] * 1024
        block = c.encode(original, 2)
        per_entry = abs(original[0] - c.decode(block)[0])
        self.assertEqual(c.tile_errors(original, block), (32 * per_entry, 32 * per_entry))

    def test_group_oracle_enumerates_pairs_and_extreme_exponents(self):
        codes = [0, 1, 2, 3, 4, 5, 6, 7, 9, 10, 11, 12, 13, 14, 15]
        for a, b in itertools.product(codes, repeat=2):
            result = c.group_product([a] * 32, [b] * 32, 0, 0)
            self.assertEqual(result, 32 * c.code_value(a) * c.code_value(b))
        for ex, ey in itertools.product((-48, 48), repeat=2):
            for codes_a, codes_b in [([7] * 32, [7] * 32), ([1] + [0] * 31, [1] * 32),
                                     ([7, 15] * 16, [7] * 32)]:
                result = c.group_product(codes_a, codes_b, ex, ey)
                as_f32 = struct.unpack('f', struct.pack('f', float(result)))[0]
                self.assertEqual(F(as_f32), result)  # mathematical representability only

    def test_payload_counts_planes_and_scales_not_fp64_compression(self):
        self.assertEqual(c.payload_bytes(32, 8), {'packed': 128, 'scales': 8})
        self.assertEqual(c.payload_bytes(3, 4), {'packed': 8, 'scales': 4})


class ErrorContracts(unittest.TestCase):
    def test_projection_combines_components_before_clipping(self):
        center = F(1) - F(1, 2)
        result = c.project_interval(center, 0, 0, 1)
        self.assertEqual(result, dict(lower=F(1, 2), upper=F(1, 2), decision='interior'))
        self.assertNotEqual(result['lower'], max(0, min(1, F(1))) + max(0, min(1, -F(1, 2))))

    def test_projection_straddles_kinks_and_fixed_bounds(self):
        self.assertEqual(c.project_interval(0, F(1, 10), 0, 1)['decision'], 'ambiguous')
        self.assertEqual(c.project_interval(10, 100, 2, 2), dict(lower=2, upper=2, decision='fixed'))
        self.assertEqual(c.project_interval(-2, 1, 0, None)['decision'], 'lower')
        self.assertEqual(c.project_interval(2, 1, None, 0)['decision'], 'upper')
        for lower, upper in ((2, 1), (float('-inf'), 1), (0, float('nan'))):
            with self.assertRaises(c.ContractError):
                c.project_interval(0, 0, lower, upper)

    def test_projection_and_dual_prox_nonexpansiveness(self):
        for lower, upper in ((None, None), (None, 3), (-2, None), (-2, 3), (1, 1)):
            def clamp(x):
                return c.project_interval(x, 0, lower, upper)['lower']
            for x, y in itertools.product(map(F, range(-5, 6)), repeat=2):
                self.assertLessEqual(abs(clamp(x) - clamp(y)), abs(x - y))
                self.assertLessEqual(abs((x - clamp(x)) - (y - clamp(y))), abs(x - y))

    def test_product_bound_covers_matrix_and_state_errors(self):
        a, h, x, xhat, computed_error = F(3), F(29, 10), F(2), F(21, 10), F(1, 100)
        product = h * xhat + computed_error
        bound = c.product_error(abs(a), abs(a - h), abs(xhat), abs(x - xhat), computed_error)
        self.assertLessEqual(abs(a * x - product), bound)

    def test_step_recurrence_and_preblend_extrapolation(self):
        local = {k: 0 for k in ('transpose', 'primal', 'extrapolate', 'forward', 'dual', 'blend_x', 'blend_y')}
        result = c.step_error(primal=F(1, 100), dual=F(2, 100), anchor_primal=0, anchor_dual=0,
                              norm_a=2, norm_at=2, error_a=0, error_at=0, norm_y=1, norm_bar=1,
                              tau=F(1, 4), sigma=F(1, 4), toward=F(1, 2), back=F(1, 2), local=local)
        # u error=.02; preblend bar error=.05; v error=.045, then blend.
        self.assertEqual(result, dict(primal=F(1, 100), dual=F(9, 400), extrapolate=F(1, 20)))
        with self.assertRaises(c.ContractError):
            c.product_error(1, -1, 1, 1, 1)

    def test_original_unit_bound_and_progress(self):
        self.assertEqual(c.original_error(F(1, 100), 1000), 10)
        self.assertEqual(c.progress_action([1, 1, 1, 1], 2), 'promote_4')
        self.assertEqual(c.progress_action([1, 1, 1, 1], 4), 'promote_8')
        self.assertEqual(c.progress_action([1, 1, 1, 1], 8), 'native')
        self.assertEqual(c.progress_action([1, 1, 1, 1], 8, certified=True), 'complete')
        self.assertEqual(c.progress_action([1, F(9, 10), F(81, 100), F(729, 1000)], 2), 'continue')

    def test_error_envelope_covers_independent_scalar_pdhg_steps(self):
        rng = random.Random(127)
        for _ in range(64):
            x, y, a, objective = (F(rng.randrange(-20, 21), 7) for _ in range(4))
            xhat, yhat, h = x + F(1, 100), y - F(1, 80), a + F(1, 90)
            tau, sigma, toward, back = F(1, 8), F(1, 16), F(4, 5), F(1, 5)
            anchor_x, anchor_y = F(1, 3), F(-1, 5)

            def step(xv, yv, av):
                u = min(F(2), max(F(-1), xv - tau * (objective - av * yv)))
                bar = 2 * u - xv
                raw = yv - sigma * av * bar
                v = raw - min(sigma, max(-2 * sigma, raw))
                return toward * u + back * anchor_x, toward * v + back * anchor_y, bar

            reference, approximate = step(x, y, a), step(xhat, yhat, h)
            local = {k: 0 for k in ('transpose', 'primal', 'extrapolate', 'forward', 'dual', 'blend_x', 'blend_y')}
            bound = c.step_error(primal=abs(x - xhat), dual=abs(y - yhat),
                                 anchor_primal=0, anchor_dual=0, norm_a=abs(a), norm_at=abs(a),
                                 error_a=abs(a - h), error_at=abs(a - h), norm_y=abs(yhat),
                                 norm_bar=abs(approximate[2]), tau=tau, sigma=sigma,
                                 toward=toward, back=back, local=local)
            for i, field in enumerate(('primal', 'dual', 'extrapolate')):
                self.assertLessEqual(abs(reference[i] - approximate[i]), bound[field])


class TransactionContracts(unittest.TestCase):
    def test_observation_preserves_all_component_bytes_and_input(self):
        saved, proposed = checkpoint(), candidate()
        before = deepcopy(proposed)
        accepted = c.observe(saved, proposed, inverse_scale_x=1, inverse_scale_y=1)
        self.assertEqual(accepted, before)
        self.assertEqual(proposed, before)
        accepted['vectors']['x'][0]['planes'][0]['data_hex'] = '0' * 32
        self.assertEqual(proposed, before)

    def test_all_rollback_state_restored_but_work_is_not_refunded(self):
        saved, proposed = checkpoint(), candidate()
        proposed['controller']['integral'] = c.float_bits(17)
        proposed['errors']['bar'] = c.rational(F(1, 100))
        proposed['vectors']['anchor_y'][0] = c.encode([2] + [0] * 31, 4)
        ledger = dict(generation=3, physical_updates=211, deadline_ns=99999)
        restored, updated = c.restore(saved, proposed, ledger)
        expected = deepcopy(saved)
        expected['generation'] = 4
        self.assertEqual(restored, expected)
        self.assertEqual(updated, dict(generation=4, physical_updates=211, deadline_ns=99999))
        self.assertEqual(ledger['generation'], 3)

    def test_stale_binding_generation_and_cross_boundary_refuse(self):
        for mutate in (lambda s: s['binding'].update(model='f' * 64),
                       lambda s: s.update(generation=4),
                       lambda s: s['controller'].update(iterations=201)):
            proposed = candidate()
            mutate(proposed)
            with self.assertRaises(c.ContractError):
                c.observe(checkpoint(), proposed, inverse_scale_x=1, inverse_scale_y=1)
        saved, proposed = checkpoint(), candidate()
        saved['controller'].update(iterations=199, since_restart=199)
        proposed['controller'].update(iterations=201, since_restart=201)
        with self.assertRaises(c.ContractError):
            c.observe(saved, proposed, inverse_scale_x=1, inverse_scale_y=1)

    def test_cancellation_and_error_guard_refuse_without_mutation(self):
        proposed = candidate()
        before = deepcopy(proposed)
        with self.assertRaises(c.ContractError):
            c.observe(checkpoint(), proposed, inverse_scale_x=1, inverse_scale_y=1, cancelled=True)
        self.assertEqual(proposed, before)
        proposed['errors']['x'] = c.rational(F(1, 1000))
        with self.assertRaises(c.ContractError):
            c.observe(checkpoint(), proposed, inverse_scale_x=1, inverse_scale_y=1)

    def test_heterogeneous_scaling_does_not_inflate_normalizer(self):
        proposed = candidate()
        proposed['vectors']['x'][0] = c.encode([1, 0] + [0] * 30, 4)
        proposed['errors']['x'] = c.rational(F(1, 10**9))
        with self.assertRaises(c.ContractError):
            c.observe(checkpoint(), proposed, inverse_scale_x=[1, 1000], inverse_scale_y=1)

    def test_checkpoint_rejects_missing_state_nonfinite_and_padding(self):
        for mutate in (lambda s: s['errors'].pop('anchor_y'),
                       lambda s: s['controller'].update(weight='7ff0000000000000'),
                       lambda s: s['vectors']['bar'].clear(),
                       lambda s: s['vectors']['x'].__setitem__(0, c.encode([1] * 32, 4))):
            value = checkpoint()
            mutate(value)
            with self.assertRaises(c.ContractError):
                c.validate_checkpoint(value)

    def test_snapshot_rounding_is_explicit(self):
        state = checkpoint()
        block = state['vectors']['x'][0]
        for plane in block['planes']:
            plane['data_hex'] = c.pack([0] * 32)
        block['planes'][0].update(exponent=48, data_hex=c.pack([7] + [0] * 31))
        block['planes'][1].update(exponent=-48, data_hex=c.pack([1] + [0] * 31))
        values, rounding = c.snapshot(state)
        self.assertEqual(rounding['x'], F(1, 1 << 49))
        self.assertEqual(values['x'][0], 6 * (1 << 48))
        self.assertEqual(c.float_bits(-0.0), '8000000000000000')

    def test_cross_window_errors_cannot_reset_and_controller_updates_are_explicit(self):
        saved = checkpoint()
        saved['errors']['x'] = c.rational(F(1, 10**9))
        for proposed in (candidate(), candidate()):
            with self.assertRaises(c.ContractError):
                c.observe(saved, proposed, inverse_scale_x=1, inverse_scale_y=1)
        proposed = candidate()
        proposed['errors']['x'] = deepcopy(saved['errors']['x'])
        accepted = c.observe(saved, proposed, inverse_scale_x=1, inverse_scale_y=1)
        accepted['controller']['checked_iteration'] = 200  # explicit host observation
        following = deepcopy(accepted)
        following['controller'].update(iterations=400, since_restart=400)
        self.assertEqual(c.observe(accepted, following, inverse_scale_x=1, inverse_scale_y=1), following)
        following['controller']['weight'] = c.float_bits(2)
        with self.assertRaises(c.ContractError):
            c.observe(accepted, following, inverse_scale_x=1, inverse_scale_y=1)


class ProtocolContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.proposal = p.read(ROOT / 'benchmarks/configs/lp-fp4-proposal-v1.json')

    def test_frozen_proposal_is_portable_and_nonexecutable(self):
        verdict = p.validate_proposal(self.proposal)
        self.assertFalse(verdict['execution_authorized'])
        self.assertFalse(verdict['hardware_admitted'])
        cells = p.study_cells(self.proposal)
        self.assertEqual((len(cells), sum(x['solves'] for x in cells)), (192, 288))
        self.assertEqual(len({tuple(sorted(x.items())) for x in cells}), 192)
        self.assertTrue(all(not r['path'].startswith('artifacts/') for r in self.proposal['sources']))

    def test_retained_costs_keep_all_models_and_uncertified_endpoints(self):
        costs = p.cost_input(self.proposal['retained_result'])
        review = p.review_cost(costs)
        self.assertEqual(len(review['rows']), 24)
        self.assertEqual(review['counts']['ineligible_quality'], 3)
        self.assertEqual(review['counts']['forecast_admitted'], 0)
        self.assertGreater(review['counts']['reject_ideal_bound'], 0)
        self.assertGreater(review['counts']['needs_profile'], 0)

    def test_schema_roster_hash_and_resource_changes_refuse(self):
        for mutate in (lambda d: d.update(execution_authorized=True),
                       lambda d: d.update(unknown=1),
                       lambda d: d['models'][0].update(sha256='f' * 64),
                       lambda d: d['resources']['prototype'].update(cpu_seconds=1),
                       lambda d: d['lanes'][1].update(components=2),
                       lambda d: d['sources'][0].update(sha256='f' * 64),
                       lambda d: d['policy'].update(final_tolerance=1e-6)):
            value = deepcopy(self.proposal)
            mutate(value)
            with self.assertRaises(c.ContractError):
                p.validate_proposal(value)

    def test_duplicate_missing_or_edited_cost_evidence_refuses(self):
        for mutate in (lambda d: d['rows'].__setitem__(1, deepcopy(d['rows'][0])),
                       lambda d: d['rows'].pop(),
                       lambda d: d['rows'][0].update(accepted=False),
                       lambda d: d['rows'][0]['phases_ns'].update(native=0)):
            value = p.cost_input(self.proposal['retained_result'])
            mutate(value)
            with self.assertRaises(c.ContractError):
                p.review_cost(value)

    def test_worst_interval_endpoint_and_all_overheads_are_charged(self):
        row = synthetic_cost()
        row['phases_ns'] = {'native': 800, 'other': 200}
        row['candidate'] = dict(accelerated_ns=dict(lower=400, upper=800),
                                work_ratio=dict(lower=2, upper=4), speedup=dict(lower=8, upper=16),
                                incremental_ns={'audit': dict(lower=0, upper=50)})
        self.assertEqual(p.forecast(row)['worst_candidate_ns'], 850)
        self.assertEqual(p.forecast(row)['decision'], 'forecast_admitted')
        row['candidate']['work_ratio']['upper'] = 16
        self.assertEqual(p.forecast(row)['worst_candidate_ns'], 1850)
        self.assertEqual(p.forecast(row)['decision'], 'reject_forecast')
        self.assertFalse(p.forecast(row)['execution_authorized'])

    def test_impossible_gain_and_missing_profiles_are_distinct(self):
        row = synthetic_cost()
        row['phases_ns'] = {'native': 10, 'other': 990}
        self.assertEqual(p.forecast(row)['decision'], 'reject_ideal_bound')
        row['phases_ns'] = {'native': 500, 'other': 500}
        self.assertEqual(p.forecast(row)['decision'], 'needs_profile')
        row['phases_ns']['other'] = 501
        with self.assertRaises(c.ContractError):
            p.forecast(row)

    def test_json_duplicates_nonfinite_and_path_traversal_refuse(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'bad.json'
            for data in ('{"x":1,"x":2}', '{"x":NaN}', '{"x":1e999}'):
                path.write_text(data)
                with self.assertRaises(c.ContractError):
                    p.read(path)
        for path in ('../outside', '/tmp/absolute', 'docs/../README.md'):
            with self.assertRaises(c.ContractError):
                p.verify_reference(dict(path=path, sha256='0' * 64))


if __name__ == '__main__':
    unittest.main()
