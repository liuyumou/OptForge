"""New prototype software contracts; the frozen 600-update admission runs separately."""

from copy import deepcopy
from fractions import Fraction as F
import json
import math
from pathlib import Path
import random
import struct
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
import lp_fp4_admission as admission
import lp_fp4_contract as contract
import lp_fp4_protocol as protocol
import lp_fp4_reference as reference


def model():
    return dict(id='software-fixture', matrix=[[1]], objective=[0.125],
                column_lower=[-2], column_upper=[2], row_lower=[0.75], row_upper=[0.75],
                tau=0.25, sigma=0.25, inverse_scale_x=[1], inverse_scale_y=[1])


class PairArithmetic(unittest.TestCase):
    def test_fp32_ties_and_double_rounding_counterexample(self):
        midpoint = F(1) + F(1, 1 << 24)
        self.assertEqual(reference.fp32(midpoint), 1)
        self.assertEqual(reference.fp32(midpoint + F(1, 1 << 100)), F(1) + F(1, 1 << 23))
        self.assertEqual(reference.fp32(midpoint - F(1, 1 << 100)), 1)
        self.assertEqual(reference.fp32(-midpoint - F(1, 1 << 100)), -1 - F(1, 1 << 23))
        # A binary64 intermediate loses the perturbation and incorrectly takes the even tie.
        rounded_twice = F(struct.unpack('f', struct.pack('f', float(midpoint + F(1, 1 << 100))))[0])
        self.assertNotEqual(rounded_twice, reference.fp32(midpoint + F(1, 1 << 100)))

    def test_subnormals_overflow_and_zero(self):
        self.assertEqual(reference.fp32(F(1, 1 << 149)), F(1, 1 << 149))
        self.assertEqual(reference.fp32(F(1, 1 << 150)), 0)
        self.assertEqual(reference.fp32(F(3, 1 << 150)), F(1, 1 << 148))
        maximum = F((1 << 24) - 1) * (1 << 104)
        self.assertEqual(reference.fp32(maximum), maximum)
        with self.assertRaises(reference.Refusal):
            reference.fp32(F(1 << 128))
        for value in (float('nan'), float('inf'), True):
            with self.assertRaises(contract.ContractError):
                reference.fp32(value)

    def test_binary32_matches_independent_ieee_conversion_away_from_double_rounding(self):
        rng = random.Random(811)
        for _ in range(128):
            value = F(rng.randrange(-(1 << 40), 1 << 40), 1 << rng.randrange(0, 80))
            expected = F(struct.unpack('f', struct.pack('f', float(value)))[0])
            self.assertEqual(reference.fp32(value), expected)

    def test_pair_keeps_low_component_and_charges_tail(self):
        value = F(1) + F(1, 1 << 30) + F(1, 1 << 80)
        represented, error = reference.pair_round(value)
        self.assertEqual(represented, F(1) + F(1, 1 << 30))
        self.assertEqual(error, F(1, 1 << 80))
        self.assertNotEqual(represented, reference.fp32(value))

    def test_enclosure_rounding_is_upward_at_normal_and_tiny_values(self):
        for value in (F(1, 3), F(1, 10**7), F(1, 1 << 1100), F(0), F(1 << 100)):
            upper = reference.upward(value)
            self.assertGreaterEqual(upper, value)
            self.assertEqual(F(float(upper)), upper)
            self.assertEqual(contract.read_rational(contract.rational(upper)), upper)


class OperatorContracts(unittest.TestCase):
    def test_prepare_quantizes_once_and_transpose_preserves_operator(self):
        source = model()
        source.update(matrix=[[1, 0.3], [-0.125, 2]], objective=[0.125, 0.25],
                      column_lower=[-2, -2], column_upper=[2, 2],
                      row_lower=[0.75, -0.5], row_upper=[0.75, -0.5],
                      inverse_scale_x=[1, 1], inverse_scale_y=[1, 1])
        prepared = reference.Prepared(source, 8)
        for _, _, tile, transposed in prepared.tiles:
            self.assertEqual(contract.transpose_tile(tile), transposed)
        values = [F(1, 2), F(-1, 4)]
        blocks, _ = reference.vector_encode(values, 8)
        for transpose in (False, True):
            counters = dict(modeled_mma_tiles=0, component_groups=0, nonzero_groups=0, local_pair_roundings=0)
            result, error = prepared.product(blocks, transpose, counters)
            matrix = list(zip(*prepared.approximate)) if transpose else prepared.approximate
            expected = [sum(a * b for a, b in zip(row, values)) for row in matrix]
            self.assertLessEqual(max(abs(a - b) for a, b in zip(expected, result)), error)
            self.assertEqual(counters['component_groups'], 2 * 8 * 8)
            self.assertEqual(counters['modeled_mma_tiles'], 2 * 8 * 8)

    def test_partial_tiles_and_vector_padding(self):
        source = model()
        source.update(matrix=[[1] * 33], objective=[0] * 33,
                      column_lower=[-2] * 33, column_upper=[2] * 33,
                      inverse_scale_x=[1] * 33)
        prepared = reference.Prepared(source, 2)
        blocks, _ = reference.vector_encode([F(1, 2)] * 33, 2)
        self.assertEqual(contract.decode(blocks[-1])[1:], [0] * 31)
        counters = dict(modeled_mma_tiles=0, component_groups=0, nonzero_groups=0, local_pair_roundings=0)
        result, error = prepared.product(blocks, False, counters)
        self.assertEqual(result, [F(33, 2)])
        self.assertEqual(error, 0)
        self.assertEqual(len(prepared.tiles), 2)

    def test_preparation_does_not_alias_source(self):
        source = model()
        prepared = reference.Prepared(source, 4)
        source['matrix'][0][0] = 999
        self.assertEqual(prepared.model['matrix'], [[1]])
        self.assertEqual(prepared.original['matrix'], [[1]])

    def test_nonfinite_dimensions_bounds_and_steps_refuse(self):
        for mutate in (lambda m: m.update(tau=0), lambda m: m.update(sigma=float('nan')),
                       lambda m: m.update(inverse_scale_x=[0]), lambda m: m.update(column_lower=[3]),
                       lambda m: m.update(matrix=[[]]), lambda m: m.update(objective=[float('inf')]),
                       lambda m: m.update(extra=1)):
            source = model()
            mutate(source)
            with self.assertRaises(contract.ContractError):
                reference.Prepared(source, 4)


class TrajectoryContracts(unittest.TestCase):
    def test_independent_first_step_has_known_exact_values(self):
        oracle = reference.RationalReference(model())
        values = oracle.advance()
        self.assertEqual(values, ([F(-1, 64)], [F(13, 128)], [F(-1, 16)]))
        candidate = reference.ComponentTrajectory(reference.Prepared(model(), 8))
        diagnostic = candidate.advance(values)
        self.assertEqual(candidate.values()['x'], values[0])
        self.assertEqual(candidate.values()['y'], values[1])
        self.assertEqual(diagnostic['actual_errors'], dict(x=0.0, y=0.0, bar=0.0))

    def test_short_independent_trajectory_encloses_rounding(self):
        candidate = reference.ComponentTrajectory(reference.Prepared(model(), 8))
        oracle = reference.RationalReference(model())
        for _ in range(3):
            diagnostic = candidate.advance(oracle.advance())
            for key in ('x', 'y', 'bar'):
                self.assertLessEqual(diagnostic['actual_errors'][key], diagnostic['error_bounds'][key])
        self.assertGreater(candidate.counters['nonzero_groups'], 0)
        self.assertGreater(candidate.counters['local_pair_roundings'], 0)
        self.assertGreater(diagnostic['error_bounds']['x'], 0)

    def test_two_observations_preserve_exact_zero_state_but_do_not_qualify(self):
        source = model()
        source.update(matrix=[[0]], objective=[0], row_lower=[0], row_upper=[0])
        result = admission.run_cell(source, 2, 400)
        self.assertIsNone(result['refused'])
        self.assertEqual(result['completed_updates'], 400)
        self.assertEqual(len(result['observations']), 2)
        self.assertTrue(all(obs['preserved'] for obs in result['observations']))
        self.assertFalse(result['retained_fast_path'])
        self.assertFalse(result['certified'])

    def test_cancellation_rolls_back_every_field_without_refunding_work(self):
        result = admission.run_cell(model(), 8, 3, cancel_after=1)
        self.assertEqual(result['refused']['reason'], 'cancelled')
        restored = deepcopy(result['checkpoint_before_rollback'])
        restored['generation'] += 1
        self.assertEqual(result['state'], restored)
        self.assertEqual(result['counters']['physical_updates'], 1)
        self.assertEqual(result['rollback_ledger']['physical_updates'], 1)
        self.assertEqual(result['rollback_ledger']['deadline_ns'], 1)
        self.assertEqual(result['next_precision'], 'native')
        self.assertTrue(result['rollback_executed'])
        self.assertFalse(result['precision_recovery_executed'])

    def test_projection_ambiguity_is_transactional(self):
        source = model()
        source.update(objective=[0], column_lower=[0])
        candidate = reference.ComponentTrajectory(reference.Prepared(source, 8))
        candidate.state['errors']['x'] = contract.rational(F(1, 10**9))
        before = deepcopy(candidate.state)
        with self.assertRaises(reference.Refusal) as caught:
            candidate.advance()
        self.assertEqual(caught.exception.reason, 'projection_ambiguous')
        self.assertEqual(candidate.state, before)
        self.assertEqual(candidate.counters['physical_updates'], 1)

    def test_injected_oracle_error_cannot_be_silently_accepted(self):
        candidate = reference.ComponentTrajectory(reference.Prepared(model(), 8))
        before = deepcopy(candidate.state)
        with self.assertRaises(reference.Refusal) as caught:
            candidate.advance(([100], [100], [100]))
        self.assertEqual(caught.exception.reason, 'actual_error_outside_enclosure')
        self.assertEqual(candidate.state, before)

    def test_independent_reference_cannot_drop_coordinates(self):
        candidate = reference.ComponentTrajectory(reference.Prepared(model(), 8))
        before = deepcopy(candidate.state)
        for invalid in (([], [0], [0]), ([0], [0]), ([0], [0], [0, 0])):
            with self.assertRaises(contract.ContractError):
                candidate.advance(invalid)
        self.assertEqual(candidate.state, before)

    def test_controller_bits_and_stale_rollback_binding(self):
        candidate = reference.ComponentTrajectory(reference.Prepared(model(), 8))
        candidate.state['controller']['integral'] = contract.float_bits(-0.0)
        candidate.checkpoint = deepcopy(candidate.state)
        candidate.advance(reference.RationalReference(model()).advance())
        candidate.rollback()
        self.assertEqual(candidate.state['controller']['integral'], '8000000000000000')
        candidate.state['binding']['model'] = 'f' * 64
        with self.assertRaises(contract.ContractError):
            candidate.rollback()

    def test_invalid_lengths_and_cancellation_boundaries_refuse(self):
        for value in (0, 601, True, 3.0):
            with self.assertRaises(contract.ContractError):
                admission.run_cell(model(), 8, value)
        with self.assertRaises(contract.ContractError):
            admission.run_cell(model(), 8, 3, cancel_after=True)


class AdmissionContracts(unittest.TestCase):
    def test_manifest_freezes_all_twelve_cells_and_sources_without_execution(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'manifest.json'
            admission.freeze(path)
            manifest = protocol.read(path)
            fixtures = admission.validate_manifest(manifest)
            self.assertEqual(len(manifest['cells']), 12)
            self.assertEqual(len(fixtures['fixtures']), 4)
            self.assertFalse(manifest['gpu_authorized'])
            with self.assertRaises(FileExistsError):
                admission.freeze(path)

    def test_manifest_mutations_do_not_authorize_device_or_change_coverage(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'manifest.json'
            admission.freeze(path)
            original = protocol.read(path)
            for mutate in (lambda m: m.update(gpu_authorized=True), lambda m: m['cells'].pop(),
                           lambda m: m['cells'][0].update(updates=200),
                           lambda m: m['cells'][0].update(components=2.0),
                           lambda m: m['sources'][0].update(extra=1),
                           lambda m: m['sources'][0].update(sha256='0' * 64),
                           lambda m: m.update(extra=1), lambda m: m['sources'].pop()):
                manifest = deepcopy(original)
                mutate(manifest)
                with self.assertRaises(contract.ContractError):
                    admission.validate_manifest(manifest)

    def test_all_thirty_six_profile_cells_remain_visible(self):
        proposal = protocol.read(ROOT / admission.PROPOSAL)
        cells = admission.deferred_cells(proposal)
        self.assertEqual(len(cells), 36)
        self.assertEqual(sum(cell['kind'] == 'pilot' for cell in cells), 24)
        self.assertEqual(sum(cell['kind'] == 'diagnostic' for cell in cells), 12)
        self.assertEqual({cell['status'] for cell in cells}, {'not_executed'})

    def test_fixture_contract_refuses_changed_limits_and_duplicate_json(self):
        value = protocol.read(ROOT / admission.FIXTURES)
        value['updates'] = 601
        with self.assertRaises(contract.ContractError):
            admission.validate_fixtures(value)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'duplicate.json'
            path.write_text('{"kind":1,"kind":2}')
            with self.assertRaises(contract.ContractError):
                protocol.read(path)


if __name__ == '__main__':
    unittest.main()
