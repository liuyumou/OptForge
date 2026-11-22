"""Fairness and failure-preservation boundaries for the prospective comparison."""
import copy
import sys
import unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'tools'))
from lp_billion_copt_fair_policy import forecast, pair, timely
from lp_billion_copt_fair_allocation import CPU, GPU, OLD_CPU, OLD_GPU, worksheet


class FairComparison(unittest.TestCase):
    def test_degenerate_recovery_refuses_attempted_or_changed_cells(self):
        import tempfile
        import lp_billion_copt_fair_degenerate_tail as d
        cells = [dict(id=identity, status='pending', family='degenerate', wall_seconds=1800,
                      seconds=2700, lane=lane, audit_seconds=audit)
                 for identity, lane, audit in zip(d.REMAINING, ['copt-gpu-pdlp', 'fp4x2'], [900, 4600])]
        with tempfile.TemporaryDirectory() as directory, patch.object(d, 'BASE', Path(directory)):
            (Path(directory) / 'resources').mkdir()
            self.assertEqual(d.untouched(dict(cells=cells)), cells)
            altered = copy.deepcopy(cells); altered[1]['wall_seconds'] = 2100
            with self.assertRaises(ValueError): d.untouched(dict(cells=altered))
            (Path(directory) / 'resources' / (cells[0]['id'] + '.reservation.json')).touch()
            with self.assertRaises(ValueError): d.untouched(dict(cells=cells))

    def test_smaller_vendor_reservation_preserves_solver_settings_and_forecast_margin(self):
        import lp_billion_copt_fair_headroom as h
        cell=dict(status='pending',family='ill_scaled',lane='copt-gpu-pdlp',wall_seconds=1800,seconds=2700,
                  memory_mb=48000,variant='scaling-off',model={'sha256':'original'},
                  memory=dict(admitted=True,host_gib=128,host_bytes=128<<30,empirical_host_peak_with_allowance=110<<30))
        before=copy.deepcopy(cell)
        with patch.object(h,'ref',return_value={'protocol':True}): revised=h.smaller(cell)
        self.assertEqual(cell,before);self.assertEqual(revised['memory']['host_gib'],120)
        self.assertEqual({k:v for k,v in revised.items() if k!='memory'},{k:v for k,v in before.items() if k!='memory'})
        cell['memory']['empirical_host_peak_with_allowance']=113<<30
        with self.assertRaises(ValueError):h.smaller(cell)

    def test_early_endpoint_cleanup_protects_shared_model_chunks_and_small_objects(self):
        from lp_billion_copt_fair_headroom import removable
        def array(sha,size):return dict(dtype='f64le',count=size//8,chunks=[dict(sha256=sha,bytes=size)])
        model=array('a'*64,16<<20);endpoint=array('b'*64,16<<20);small=array('c'*64,1<<20)
        documents=[dict(endpoint=dict(primal=model,dual=endpoint),small=small)]
        self.assertEqual(removable(documents,[dict(arrays={'original':model})]),{'b'*64:16<<20})

    def test_native_tail_changes_only_supported_prospective_wall_allowance(self):
        from lp_billion_copt_fair_native_tail import corrected
        cell=dict(status='pending',family='ill_scaled',lane='fp4x2',seconds=2700,wall_seconds=2100.,
                  common_solver_wall_seconds=2100,audit_seconds=4600,audit_host_gib=64,memory={'host_gib':76},
                  request={'settings':dict(wall_ms=2100000,tolerance=1e-9,iteration_limit=10000,check_interval=500),
                           'tensor':{'control_interval':100},'fast':{'gpu_control':True}})
        saved=copy.deepcopy(cell);expected=copy.deepcopy(cell)
        expected.update(wall_seconds=1800.,common_solver_wall_seconds=1800)
        expected['request']['settings']['wall_ms']=1800000
        self.assertEqual(corrected(cell),expected);self.assertEqual(cell,saved)
        for changed in [dict(cell,family='coupled_blocks'),dict(cell,status='missing_response'),dict(cell,seconds=1800)]:
            with self.assertRaises(ValueError):corrected(changed)

    def test_native_tail_vendor_has_equal_allowance_and_retains_audit_margin(self):
        from lp_billion_copt_fair_native_tail import corrected
        cell=dict(status='pending',family='degenerate',lane='copt-gpu-pdlp',seconds=2700,wall_seconds=2100.,
                  audit_seconds=900,variant='scaling-off',memory_mb=48000)
        value=corrected(cell)
        self.assertEqual(value['wall_seconds'],1800)
        self.assertEqual(value['seconds']-value['wall_seconds'],900)
        self.assertEqual(value['audit_seconds'],900);self.assertEqual(value['variant'],cell['variant'])

    def test_prospective_allowance_preserves_numerical_and_memory_settings(self):
        from lp_billion_copt_fair_budgeted import resized
        original = dict(status='pending', lane='fp4x2', family='ill_scaled', seconds=1800, wall_seconds=1200,
                        memory={'host_gib': 76, 'device_gib': 70}, model={'sha256': 'original'},
                        request=dict(settings=dict(iteration_limit=10000, tolerance=1e-9, wall_ms=1200000,
                                                   check_interval=500), tensor={'control_interval': 100}))
        before = copy.deepcopy(original); revised = resized(original)
        self.assertEqual(original, before)
        expected = copy.deepcopy(before['request']); expected['settings']['wall_ms'] = 2100000
        self.assertEqual(revised['request'], expected)
        self.assertEqual(revised['memory'], before['memory']); self.assertEqual(revised['model'], before['model'])
        self.assertEqual(revised['audit_seconds'], 4600)
        original['request']['settings']['tolerance'] = 1e-6
        with self.assertRaises(ValueError): resized(original)

    def test_remaining_worksheet_includes_all_audits_and_normal_overhead(self):
        from lp_billion_copt_fair_budgeted import worksheet
        cells = [dict(seconds=2700, wall_seconds=2100, audit_seconds=v) for v in [900]*4 + [2800,4600,4600]]
        plan = worksheet(cells)
        self.assertEqual(plan['cpu'], dict(admission=2400, development=82800, reporting=70000, cleanup=720))
        self.assertEqual(plan['gpu'], dict(admission=180, development=18900))
        self.assertEqual(sum(plan['reporting_components_cpu'].values()), 70000)
        self.assertEqual(plan['audit_cpu_seconds'], 62400)
        with self.assertRaises(ValueError): worksheet(cells[:-1])

    def test_certified_pair_with_different_allowances_has_no_ratio(self):
        from lp_billion_copt_fair_budgeted import budgeted_pair
        project = dict(family='tall', status='certified', complete_ns=100, timely_strict_certificate=True,
                       requested_solver_wall_ns=1200*10**9, outer_reservation_seconds=1800)
        vendor = dict(project, status=1, complete_ns=200, requested_solver_wall_ns=2100*10**9, outer_reservation_seconds=2700)
        self.assertIsNone(budgeted_pair(project, vendor)['copt_over_project_complete_ratio'])
        vendor.update(requested_solver_wall_ns=1200*10**9, outer_reservation_seconds=1800)
        self.assertEqual(budgeted_pair(project, vendor)['copt_over_project_complete_ratio'], 2)

    def test_read_only_seal_cannot_regrade_proofs_or_restore_lost_timing(self):
        from lp_billion_copt_fair_recovery_v2 import validate_seal
        from lp_billion_full_audit import requests
        response = dict(settings={'tolerance': 1e-9}, endpoint={'primal': 'final'}, certificate={'accepted': True},
                        status='certified', certified=True,
                        assessments=[dict(endpoint={'primal': 'earlier'}, certificate={'accepted': False})])
        queries, mapping, _ = requests(response)
        first = [dict(accepted=True, model_sha256='original', tolerance=1e-9)]
        second = [dict(accepted=False, model_sha256='original', tolerance=1e-9)]
        stored = dict(results=first + second, proof_mapping=mapping, checks=2, covered_endpoints=2,
                      final_check_ns=None, final_proof_timing_available=False, timing_eligible=False,
                      strict_endpoint_accepted=True, certified=True)
        request = dict(requests=queries, mapping=mapping)
        self.assertTrue(validate_seal(response, request, first, second, stored, 'original'))
        changed = copy.deepcopy(stored); changed['final_proof_timing_available'] = True
        with self.assertRaisesRegex(ValueError, 'timing'): validate_seal(response, request, first, second, changed, 'original')
        changed = copy.deepcopy(stored); changed['results'][1]['accepted'] = True
        with self.assertRaises(ValueError): validate_seal(response, request, first, changed['results'][1:], changed, 'original')

    def test_recovered_proof_requires_exact_original_requests(self):
        from lp_billion_copt_fair_recovery import prior_proofs
        from lp_billion_full_audit import requests
        response = dict(settings={'tolerance': 1e-9}, endpoint={'primal': 'final', 'dual': 'final-dual'},
                        certificate={'accepted': True}, assessments=[dict(endpoint={'primal': 'earlier', 'dual': 'earlier-dual'}, certificate={'accepted': False})])
        queries, mapping, _ = requests(response)
        retained = dict(requests=queries, mapping=mapping)
        proof = dict(accepted=True, model_sha256='original', tolerance=1e-9)
        self.assertEqual(prior_proofs(response, retained, [proof], 'original')[1], [0, 1])
        changed = copy.deepcopy(retained); changed['requests'][1]['endpoint']['dual'] = 'different'
        with self.assertRaisesRegex(ValueError, 'request binding'): prior_proofs(response, changed, [proof], 'original')

    def test_recovered_proof_cannot_drop_or_regrade_completed_evidence(self):
        from lp_billion_copt_fair_recovery import prior_proofs
        from lp_billion_full_audit import requests
        response = dict(settings={'tolerance': 1e-9}, endpoint={'primal': 'final'}, certificate={'accepted': True},
                        assessments=[dict(endpoint={'primal': 'earlier'}, certificate={'accepted': False})])
        queries, mapping, _ = requests(response); retained = dict(requests=queries, mapping=mapping)
        proof = dict(accepted=True, model_sha256='original', tolerance=1e-9)
        for changed in [dict(proof, accepted=False), dict(proof, model_sha256='other'), dict(proof, tolerance=1e-6)]:
            with self.assertRaises(ValueError): prior_proofs(response, retained, [changed], 'original')
        with self.assertRaises(ValueError): prior_proofs(response, retained, [], 'original')

    def test_capacity_disposition_keeps_policy_binding_and_forecast_separate(self):
        from lp_billion_copt_fair_capacity import metadata
        bound = dict(source={'runner': True}, capacity={'policy': True}, checker={'checker': True})
        report = dict(capacity={'wide': {'admitted': False}}, **metadata(bound))
        self.assertEqual(report['capacity'], {'wide': {'admitted': False}})
        self.assertEqual(report['capacity_policy'], {'policy': True})
        self.assertEqual(report['original_runner'], {'runner': True})
        self.assertEqual(bound['capacity'], {'policy': True})

    def test_full_authorization_chain_and_exact_caps_remain_required(self):
        import lp_billion_readmission as r
        import lp_billion_copt_fair_allocation as allocation
        from test_lp_billion_gpu_control import AssessmentAllocationContracts
        old, assessment, revised, packing = AssessmentAllocationContracts().fixture()
        extension = dict(status='explicitly_authorized', user_answer=allocation.ANSWER,
                         previous_approval={'path': 'approved-assessment-extension-v1.json'},
                         original_approval={'path': 'approved-recovery-v1.json'},
                         old_cpu_caps=OLD_CPU, old_gpu_caps=OLD_GPU, cpu_caps=CPU, gpu_caps=GPU,
                         proposal={}, protocol={})
        args = (old, extension, assessment, revised, packing)
        with patch.object(r, 'ref', side_effect=lambda p: {'path': p.name}), patch.object(r, 'resolve'), \
             patch.object(allocation, 'ref', side_effect=lambda p: {'path': p.name}), patch.object(allocation, 'resolve'):
            accepted = r.fair_approval(*args)
            self.assertEqual(accepted['settlement'], old['settlement'])
            self.assertEqual(accepted['cpu_caps'], CPU)
            for index in range(1, 5):
                changed = copy.deepcopy(args); changed[index]['user_answer'] = ''
                with self.assertRaises(ValueError): r.fair_approval(*changed)
            for key in ['cpu_caps', 'old_cpu_caps', 'previous_approval']:
                changed = copy.deepcopy(args); changed[1][key] = {}
                with self.assertRaises(ValueError): r.fair_approval(*changed)

    def test_late_or_unsuccessful_certificate_cannot_win(self):
        row = dict(family='tall', lane='copt-gpu-pdlp', timing_eligible=True, certified=True)
        response = dict(solver_wall_ns=599_000_000_000, returned_before_deadline=True)
        self.assertTrue(timely(row, response, 600))
        response['solver_wall_ns'] = 600_000_000_001
        self.assertFalse(timely(row, response, 600))
        response.update(solver_wall_ns=1, returned_before_deadline=False)
        self.assertFalse(timely(row, response, 600))
        row.update(lane='fp4x2', timing_eligible=False)
        self.assertFalse(timely(row, dict(elapsed_ns=1), 600))

    def test_failed_capacity_path_is_not_dropped(self):
        model = dict(family='irregular', nonzeros=1_000_000_000, rows=10, columns=10)
        small = dict(id='small', family='irregular', nonzeros=64_000_000,
                     capacity_observed=True, response={'present': True}, host_peak_bytes=1 << 30,
                     owned_device_peak_bytes=1 << 30, vendor_mem_peak_mb=0)
        large = dict(small, id='large', nonzeros=512_000_000, capacity_observed=False, response=None)
        self.assertTrue(forecast(model, [small], 48000)['admitted'])
        refused = forecast(model, [small, large], 48000)
        self.assertFalse(refused['admitted'])
        self.assertEqual(refused['source_cells'], ['small', 'large'])
        overflow = dict(small, host_peak_bytes=20 << 30)
        self.assertFalse(forecast(model, [overflow], 48000)['admitted'])

    def test_ratio_requires_both_timely_strict_solutions(self):
        project = dict(family='tall', status='certified', complete_ns=100, timely_strict_certificate=True)
        vendor = dict(family='tall', status=1, complete_ns=200, timely_strict_certificate=True)
        self.assertEqual(pair(project, vendor)['copt_over_project_complete_ratio'], 2)
        vendor['timely_strict_certificate'] = False
        self.assertIsNone(pair(project, vendor)['copt_over_project_complete_ratio'])

    def test_proposal_does_not_change_current_allocation(self):
        from lp_billion_common import CPU_CAPS, GPU_CAPS
        # Both the still-current and explicitly approved future state are allowed;
        # merely importing the proposal must never mutate either dictionary.
        before = copy.deepcopy((CPU_CAPS, GPU_CAPS))
        plan = worksheet()
        self.assertEqual((CPU_CAPS, GPU_CAPS), before)
        self.assertIn(before, [(OLD_CPU, OLD_GPU), (CPU, GPU)])
        self.assertEqual(sum(plan['cpu'].values()), 237880)
        self.assertEqual(sum(plan['gpu'].values()), 27270)


if __name__ == '__main__':
    unittest.main()
