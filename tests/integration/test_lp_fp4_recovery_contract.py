"""CPU contract and adversarial event tests; no old admission or device rerun."""
from copy import deepcopy
from dataclasses import replace
from fractions import Fraction as F
import json
from pathlib import Path
import random
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
import lp_fp4_contract as c
import lp_fp4_recovery_contract as r


def payload(components=2):
    values = [F(1, 3), F(-7, 11)] + [0] * 30
    block = c.encode(values, components)
    return dict(schema_version=2, kind='lp-fp4-recovery-checkpoint',
        policy_sha256=r.digest(r.policy()), error_authority='local-representation-only',
        binding=dict(model='a'*64, operator='b'*64, settings='c'*64, proposal='d'*64),
        rows=2, columns=2, components=components, generation=1,
        vectors={k: [deepcopy(block)] for k in ('x', 'y', 'bar', 'anchor_x', 'anchor_y')},
        local_representation_bounds={k: deepcopy(block['remainder_bound'])
                                    for k in ('x', 'y', 'bar', 'anchor_x', 'anchor_y')},
        controller=dict(weight=c.float_bits(1), integral=c.float_bits(-0.0),
                        previous_error=None, anchor_error=c.float_bits(1), last_check_error=c.float_bits(1),
                        iterations=0, restarts=0, since_restart=0, checked_iteration=0))


def monitor(**updates):
    p = payload()
    return replace(r.Monitor(model=p['binding']['model'], policy=p['policy_sha256'],
                            tier='certified-1e-7', checkpoint=r.digest(p), generation=1), **updates)


def event(state, residual, **updates):
    args = dict(generation=state.generation, iteration=state.iteration+200,
                candidate='e'*64, candidate_checkpoint='f'*64, residual=residual)
    args.update(updates)
    return r.audit(state, **args)


def receipt(tier='certified-1e-7', accepted=True):
    return dict(model_sha256='a'*64, candidate_sha256='e'*64, checker_sha256='9'*64,
                tier=tier, absolute=str(r.tolerance(tier)), relative=str(r.tolerance(tier)),
                eligible=True, feasible=accepted, finite_bound=True, gap_closed=accepted,
                accepted=accepted, refusal=None)


class LocalAccounting(unittest.TestCase):
    def test_cancelled_rounding_errors_cannot_hide_encoding(self):
        pair, _ = r.pair_round(F(1, 3))
        target = pair - F(1, 1 << 55)
        result = r.local_encode([target], 8)
        represented = r.vector_values(result['blocks'], 1)[0]
        self.assertLess(abs(represented-target), result['encoding'])
        self.assertGreaterEqual(result['total'], result['encoding'])
        self.assertGreaterEqual(result['total'], abs(represented-target))

    def test_independent_local_error_cover_with_padding_and_underflow(self):
        rng = random.Random(290061)
        values = [F(rng.randrange(-1000, 1000), 997) for _ in range(35)] + [F(1, 1 << 200)]
        for k in (2, 4, 8):
            got = r.local_encode(values, k)
            actual = r.vector_values(got['blocks'], len(values))
            self.assertGreaterEqual(got['total'], max(abs(a-b) for a, b in zip(values, actual)))
            self.assertEqual(got['total'], got['pair_rounding']+got['encoding'])
            self.assertEqual(got['authority'], 'exact-local-only')

    def test_product_uses_row_sum_and_original_stored_input(self):
        # A-H = [1/8,-1/8], stored input [2,-2]: max-entry is insufficient.
        got = r.local_product_budget(F(1, 4), 2, F(1, 100), F(1, 200), F(1, 400))
        self.assertEqual(got, F(207, 400))
        self.assertGreaterEqual(got, F(1, 2))
        with self.assertRaises(c.ContractError):
            r.local_product_budget(-1, 2, 0, 0)

    def test_local_guard_requires_every_term_and_preserves_authority(self):
        terms = dict.fromkeys(r.TERMS, F(0))
        terms['encoding'] = F(1, 128)
        gains = dict.fromkeys(r.TERMS, F(1))
        result = r.check_local_terms(terms, gains, 1, 1, 'certified-1e-7', 'device-observed')
        self.assertTrue(result['accepted'])
        self.assertFalse(result['trajectory_enclosure'])
        self.assertEqual(result['authority'], 'device-observed')
        gains['encoding'] = 3
        self.assertFalse(r.check_local_terms(terms, gains, 1, 1, 'certified-1e-7', 'exact-local-only')['accepted'])
        del terms['instruction']
        with self.assertRaises(c.ContractError):
            r.check_local_terms(terms, gains, 1, 1, 'certified-1e-7', 'device-observed')

    def test_allowance_floor_is_distinct_from_global_error_and_final_certificate(self):
        for tier in ('certified-1e-7', 'certified-1e-9'):
            self.assertEqual(r.local_allowance(0, tier), r.tolerance(tier)/64)
            self.assertEqual(r.local_allowance(100, tier), F(1, 64))

    def test_coupling_example_has_contraction_and_growing_absolute_bound(self):
        # Independently verify the scoped Lyapunov identity, not a general LP proof.
        a = [[F(1), F(1, 4)], [-F(1, 4), F(7, 8)]]
        p = [[F(1), F(1, 4)], [F(1, 4), F(1)]]
        diff = [[p[i][j]-sum(a[k][i]*p[k][l]*a[l][j] for k in range(2) for l in range(2))
                 for j in range(2)] for i in range(2)]
        self.assertEqual(diff, [[F(1, 16), F(1, 64)], [F(1, 64), F(1, 16)]])
        self.assertGreater(diff[0][0]*diff[1][1]-diff[0][1]**2, 0)
        # Old independent absolute recurrence has eigenvector [1,2], eigenvalue 3/2.
        self.assertEqual([1+F(1, 4)*2, F(3, 4)+F(9, 8)*2], [F(3, 2), F(3)])


class ResidualOracles(unittest.TestCase):
    def observe(self, **changes):
        args = dict(matrix=[[1]], objective=[1], row_lower=[1], row_upper=[1],
                    column_lower=[0], column_upper=[None], x=[1], y=[1])
        args.update(changes)
        return r.residual_observation(**args)

    def test_exact_equality_kkt_point(self):
        self.assertEqual(self.observe()['rho'], 0)

    def test_primal_feasible_but_dual_bad_is_not_converged(self):
        got = self.observe(y=[0])
        self.assertEqual(got['row'], 0)
        self.assertGreater(got['primal_fixed'], 0)

    def test_dual_sign_for_lower_upper_and_inactive_rows(self):
        self.assertEqual(self.observe(row_upper=[None])['rho'], 0)
        self.assertEqual(self.observe(objective=[-1], row_lower=[None], y=[-1])['rho'], 0)
        self.assertGreater(self.observe(row_upper=[None], y=[-1])['dual_fixed'], 0)
        self.assertGreater(self.observe(objective=[0], row_lower=[0], row_upper=[2])['dual_fixed'], 0)

    def test_fixed_column_and_free_row(self):
        got = self.observe(objective=[9], column_lower=[1], column_upper=[1],
                           row_lower=[None], row_upper=[None], y=[0])
        self.assertEqual(got['rho'], 0)
        self.assertGreater(self.observe(row_lower=[None], row_upper=[None])['dual_fixed'], 0)

    def test_coupled_rectangular_nonzero_problem(self):
        got = r.residual_observation([[1, 2], [3, -1]], [4, 1], [3, 2], [3, 2],
                                    [0, 0], [None, None], [1, 1], [1, 1])
        self.assertEqual(got['rho'], 0)

    def test_bad_shapes_bounds_nonfinite_and_bool_refuse(self):
        for change in (dict(x=[]), dict(matrix=[[1, 2]]), dict(row_lower=[2]),
                       dict(y=[float('nan')]), dict(x=[True]), dict(column_upper=[float('inf')])):
            with self.subTest(change=change), self.assertRaises(c.ContractError):
                self.observe(**change)


class RecoveryDecisions(unittest.TestCase):
    def test_audit_adopts_without_mutating_numerical_state(self):
        state = monitor()
        before = deepcopy(state)
        result = event(state, F(4, 5))
        self.assertEqual(state, before)
        self.assertEqual(result['action'], 'adopt')
        self.assertEqual(result['state'].checkpoint, 'f'*64)
        self.assertEqual(result['state'].generation, state.generation)

    def test_three_stalls_and_progress_reset(self):
        state = monitor()
        for expected in (1, 2):
            state = event(state, 1)['state']
            self.assertEqual(state.stalls, expected)
        improved = event(state, F(9, 10))['state']
        self.assertEqual(improved.stalls, 0)
        got = event(state, 1)
        self.assertEqual(got['action'], 'promote_restore')
        self.assertEqual(got['state'].components, 4)
        self.assertEqual(got['state'].iteration, state.iteration)

    def test_growth_strict_boundary_and_monotone_native_handoff(self):
        state = monitor()
        self.assertEqual(event(state, 2)['action'], 'adopt')
        for target in (4, 8, None):
            got = event(state, F(201, 100))
            self.assertEqual(got['target_components'], target)
            self.assertEqual(got['restore_sha256'], state.checkpoint)
            self.assertFalse(got['reset_work'])
            self.assertEqual(got['state'].generation, state.generation+1)
            state = got['state']
        self.assertEqual(got['action'], 'native_restore')

    def test_nonfinite_safety_cancel_and_exhaustion_precede_certificate(self):
        for kwargs, action in [(dict(residual=float('nan')), 'promote_restore'),
                               (dict(safety='projection_ambiguous'), 'promote_restore'),
                               (dict(safety='local_budget'), 'promote_restore'),
                               (dict(safety='audit_failure'), 'stop_restore'),
                               (dict(cancelled=True), 'stop_restore'),
                               (dict(exhausted=True), 'stop_restore')]:
            args = dict(residual=1, certificate=receipt(), checker='9'*64)
            args.update(kwargs)
            self.assertEqual(event(monitor(), **args)['action'], action)

    def test_identity_and_late_audits_cannot_be_masked_by_certificate(self):
        for changes in (dict(generation=0), dict(iteration=0), dict(iteration=201),
                        dict(iteration=True), dict(safety='unknown')):
            with self.assertRaises(c.ContractError):
                event(monitor(), 0, certificate=receipt(), checker='9'*64, **changes)

    def test_submission_stops_at_audit_controller_and_physical_limits(self):
        state = monitor()
        self.assertEqual(r.submission_size(state, 0, 1000, 1000), 32)
        self.assertEqual(r.submission_size(state, 192, 1000, 1000), 8)
        self.assertEqual(r.submission_size(state, 200, 1000, 1000), 0)
        self.assertEqual(r.submission_size(state, 20, 3, 7), 3)
        self.assertEqual(r.submission_size(state, 20, 1000, 0), 0)
        with self.assertRaises(c.ContractError):
            r.submission_size(state, 201, 10, 10)

    def test_certificate_precedes_stagnation_and_is_tier_specific(self):
        got = event(monitor(stalls=2), 1, certificate=receipt(), checker='9'*64)
        self.assertEqual(got['action'], 'certified_endpoint')
        self.assertEqual(got['state'].iteration, 200)
        self.assertEqual(got['state'].checkpoint, 'f'*64)
        with self.assertRaises(c.ContractError):
            event(monitor(tier='certified-1e-9'), 0, certificate=receipt(), checker='9'*64)
        self.assertEqual(event(monitor(tier='certified-1e-9'), 0,
                              certificate=receipt('certified-1e-9'), checker='9'*64)['action'],
                         'certified_endpoint')

    def test_checker_failure_does_not_become_success(self):
        self.assertEqual(event(monitor(), F(1, 2), certificate=receipt(accepted=False),
                              checker='9'*64)['action'], 'adopt')
        for key, value in [('model_sha256', '0'*64), ('candidate_sha256', '0'*64),
                           ('checker_sha256', '0'*64), ('finite_bound', False),
                           ('gap_closed', False), ('eligible', False), ('accepted', 1),
                           ('refusal', 'infinite variable bound')]:
            bad = receipt(); bad[key] = value
            with self.subTest(key=key), self.assertRaises(c.ContractError):
                event(monitor(), 0, certificate=bad, checker='9'*64)

    def test_zero_residual_without_certificate_still_escalates(self):
        state = monitor(residual=F(0))
        for _ in range(2):
            state = event(state, 0, certificate=receipt(accepted=False), checker='9'*64)['state']
        self.assertEqual(event(state, 0, certificate=receipt(accepted=False), checker='9'*64)['action'],
                         'promote_restore')

    def test_terminal_and_failed_conversion_cannot_loop_fp4(self):
        for got in (event(monitor(components=8), 3), event(monitor(), 1, cancelled=True),
                    event(monitor(), 1, safety='conversion_failure'),
                    event(monitor(), 0, certificate=receipt(), checker='9'*64)):
            with self.assertRaises(c.ContractError): event(got['state'], 1)
            with self.assertRaises(c.ContractError): r.submission_size(got['state'], 0, 200, 200)


class CheckpointsAndCosts(unittest.TestCase):
    def test_complete_bundle_binds_policy_history_and_full_state(self):
        p = payload(); state = monitor()
        bundle = r.checkpoint_bundle(p, state)
        self.assertEqual(bundle['monitor']['residual'], c.rational(1))
        p['controller']['integral'] = c.float_bits(9)
        self.assertNotEqual(p, bundle['payload'])
        with self.assertRaises(c.ContractError):
            r.checkpoint_bundle(p, state)
        with self.assertRaises(c.ContractError):
            r.checkpoint_bundle(payload(), replace(state, iteration=1))

    def test_restore_deep_copies_every_plane_and_controller(self):
        p = payload()
        got = r.restore(p, binding=p['binding'], policy_sha256=p['policy_sha256'], current_generation=7)
        self.assertEqual(got['generation'], 8)
        got['vectors']['anchor_y'][0]['planes'][0]['data_hex'] = '0'*32
        got['controller']['integral'] = c.float_bits(4)
        self.assertEqual(p, payload())
        with self.assertRaises(c.ContractError):
            r.restore(p, binding=p['binding'], policy_sha256='0'*64, current_generation=7)

    def test_bundle_restore_keeps_residual_and_stalls_and_rebinds_generation(self):
        p = payload(); state = monitor(residual=F(1, 3), stalls=2)
        bundle = r.checkpoint_bundle(p, state)
        got = r.restore_bundle(bundle, binding=p['binding'], policy_sha256=p['policy_sha256'],
                               current_generation=9)
        self.assertEqual(got['monitor']['residual'], c.rational(F(1, 3)))
        self.assertEqual(got['monitor']['stalls'], 2)
        self.assertEqual(got['monitor']['generation'], 10)
        self.assertEqual(got['monitor']['checkpoint'], r.digest(got['payload']))
        bundle['monitor']['generation'] = 7
        with self.assertRaises(c.ContractError):
            r.restore_bundle(bundle, binding=p['binding'], policy_sha256=p['policy_sha256'], current_generation=9)

    def test_promotion_is_exact_and_does_not_erase_prior_local_error(self):
        p = payload()
        for k in (4, 8):
            got = r.convert_checkpoint(p, k)
            self.assertEqual(got['local_representation_bounds'], p['local_representation_bounds'])
            self.assertEqual(got['controller'], p['controller'])
            for name in p['vectors']:
                self.assertEqual(c.decode(p['vectors'][name][0]), c.decode(got['vectors'][name][0]))
            p = got
        with self.assertRaises(c.ContractError):
            r.convert_checkpoint(p, 2)

    def test_malformed_checkpoint_and_forged_global_error_authority_refuse(self):
        for change in ('error_authority', 'local_representation_bounds', 'padding', 'anchor', 'controller'):
            p = payload()
            if change == 'error_authority': p[change] = 'proved-trajectory'
            elif change == 'local_representation_bounds': p[change]['x'] = c.rational(0)
            elif change == 'padding': p['vectors']['x'] = [c.encode([1]*32, 2)]
            elif change == 'anchor': del p['vectors']['anchor_y']
            else: p['controller']['checked_iteration'] = 1
            with self.subTest(change=change), self.assertRaises(c.ContractError):
                r.validate_checkpoint(p)

    def test_physical_cost_survives_rollback_and_includes_all_phases(self):
        ledger = dict.fromkeys((*r.PHASES, 'physical_updates'), 0)
        charged = r.charge(ledger, 'iteration', 400, 200)
        charged = r.charge(charged, 'rollback', 10)
        charged = r.charge(charged, 'native_recovery', 500, 30)
        self.assertEqual(charged['physical_updates'], 230)
        self.assertEqual(ledger['physical_updates'], 0)
        phases = {k: charged[k] for k in r.PHASES}
        self.assertFalse(r.complete_cost(1000, phases)['row_meets_110_percent'])
        self.assertFalse(r.complete_cost(2000, phases)['solver_retention_established'])
        del phases['checker']
        with self.assertRaises(c.ContractError): r.complete_cost(1000, phases)

    def test_proposal_has_exact_fresh_grid_and_whole_job_resources(self):
        p = r.policy()['integration_proposal']; cells = r.proposed_cells()
        self.assertFalse(p['executable'])
        self.assertEqual(len(cells), p['trajectory_cells'])
        self.assertEqual(len({v['id'] for v in cells}), 96)
        self.assertTrue(all(v['minimum_updates'] == 600 for v in cells))
        for name in ('cpu', 'gpu'):
            self.assertEqual(sum(j['jobs']*j[f'{name}_seconds_each'] for j in p['resource_jobs']), p[f'{name}_seconds'])
        self.assertTrue(all(j['cpu_seconds_each'] >= 4*j['gpu_seconds_each'] for j in p['resource_jobs']))

    def test_policy_mutations_need_new_version(self):
        for key, value in [('trajectory_enclosure', True), ('audit_max_updates', 201),
                           ('growth_ratio', '3'), ('observation_mutates_state', True)]:
            p = r.policy(); p[key] = value
            with self.assertRaises(c.ContractError): c.schema_check('lp-fp4-recovery-v1.schema.json', p)


if __name__ == '__main__':
    unittest.main()
