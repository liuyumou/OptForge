"""The separate allocation and idle-only extension must fail closed."""
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'tools'))
import lp_billion_common as common
import lp_billion_budget as budget
import lp_billion_idle as idle
import lp_billion_availability as availability
import lp_billion_prepare_continue as continuation
from lp_billion_test_support import native_inventory_fixture


class BillionResourceContracts(unittest.TestCase):
    def test_readmission_v10_supersedes_v9_in_numeric_order(self):
        with tempfile.TemporaryDirectory() as temporary, mock.patch.object(budget,'BASE',Path(temporary)):
            root=Path(temporary)/'operational-readmissions';root.mkdir()
            for name in ['v9.json','v10.json','v4.json']:(root/name).write_text('{}')
            self.assertEqual([p.stem for p in budget.operational_plans()],['v4','v9','v10'])

    def test_approved_totals_and_memory_are_exact(self):
        self.assertEqual(sum(common.CPU_CAPS.values()), 570000)
        self.assertEqual(sum(common.GPU_CAPS.values()), 68000)
        self.assertEqual((common.HOST_LIMIT, common.DEVICE_LIMIT, common.DISK_LIMIT),
                         (128 << 30, 80 << 30, 400 << 30))

    def test_foreign_process_refuses_even_when_utilization_is_zero(self):
        with self.assertRaisesRegex(ValueError, 'foreign GPU process'):
            idle.validate_gpu(dict(processes={99: 1}, utilization=0), {42})

    def test_owned_memory_is_aggregated(self):
        with self.assertRaisesRegex(ValueError, 'memory ceiling'):
            idle.validate_gpu(dict(processes={42: 41 << 30, 43: 40 << 30}, used=82 << 30), {42, 43})
        idle.validate_gpu(dict(processes={42: 40 << 30, 43: 40 << 30}, used=81 << 30), {42, 43})

    def test_unlisted_allocation_refuses_even_with_zero_utilization(self):
        with self.assertRaisesRegex(ValueError, 'unattributed GPU memory'):
            idle.validate_gpu(dict(processes={}, utilization=0, used=10 << 30), set())
        with self.assertRaisesRegex(ValueError, 'unattributed GPU memory'):
            idle.validate_gpu(dict(processes={42: 1 << 30}, used=4 << 30), {42})
        idle.validate_gpu(dict(processes={42: 1 << 30}, used=2 << 30), {42})

    def test_availability_requires_sustained_fresh_idle_observations(self):
        samples=[dict(start_ns=i*61*common.NS,end_ns=i*61*common.NS+1,
            used=1<<30,processes={},utilization=0) for i in range(6)]
        now=samples[-1]['end_ns']
        self.assertTrue(availability.stable(samples,now))
        self.assertFalse(availability.stable(samples[:-1],now))
        self.assertFalse(availability.stable(samples,now+91*common.NS))
        self.assertFalse(availability.stable(samples,now-1))
        bad=[dict(s) for s in samples];bad[2]['used']=10<<30
        self.assertFalse(availability.stable(bad,now))
        self.assertFalse(availability.stable(samples[:2]+samples[3:],now))

    def test_continuation_cannot_repeat_an_unsettled_or_failed_reservation(self):
        with tempfile.TemporaryDirectory() as temporary, mock.patch.object(continuation,'BASE',Path(temporary)):
            root=Path(temporary)/'resources';root.mkdir()
            self.assertFalse(continuation.completed('cell'))
            (root/'cell.reservation.json').write_text('{}')
            with self.assertRaisesRegex(ValueError,'unsettled reservation'):
                continuation.completed('cell')
            p=root/'cell.settlement.json'
            p.write_text(json.dumps(dict(status='refused',cleanup_empty=True,overrun=False)))
            with self.assertRaisesRegex(ValueError,'retain failed reservation'):
                continuation.completed('cell')
            p.write_text(json.dumps(dict(status='passed',cleanup_empty=True,overrun=False)))
            self.assertTrue(continuation.completed('cell'))

    def test_failed_telemetry_is_not_idle(self):
        with self.assertRaisesRegex(ValueError, 'NVML telemetry failure'):
            idle.Nvml.check(3)

    def test_idle_requires_empty_process_inventory_and_zero_utilization(self):
        for sample in [dict(processes={1: 1}, utilization=0, free=100 << 30),
                       dict(processes={}, utilization=1, free=100 << 30),
                       dict(processes={}, utilization=0, free=1 << 30, used=1 << 30),
                       dict(processes={}, utilization=0, free=90 << 30, used=10 << 30)]:
            sensor = mock.Mock()
            sensor.sample.return_value = sample
            with mock.patch.object(idle, 'Nvml', return_value=sensor):
                with self.assertRaises(ValueError):
                    idle.quiet(1 << 30)
            sensor.close.assert_called_once()

    def test_three_idle_samples_precede_admission(self):
        sensor = mock.Mock()
        sensor.sample.return_value = dict(processes={}, utilization=0, free=100 << 30, used=1 << 30)
        with mock.patch.object(idle, 'Nvml', return_value=sensor), mock.patch.object(idle.time, 'sleep'):
            self.assertEqual(len(idle.quiet(80 << 30)), 3)
        self.assertEqual(sensor.sample.call_count, 3)

    def test_source_references_refuse_escape_and_mutation(self):
        with tempfile.TemporaryDirectory() as temporary, mock.patch.object(common, 'BASE', Path(temporary)):
            p = Path(temporary)/'source'
            p.write_bytes(b'original')
            item = common.ref(p)
            self.assertEqual(common.resolve(item), p)
            p.write_bytes(b'changed')
            with self.assertRaises(ValueError):
                common.resolve(item)
            with self.assertRaises(ValueError):
                common.resolve(dict(item, path='../outside'))

    def test_settled_charges_replace_reservations_without_editing_them(self):
        with tempfile.TemporaryDirectory() as temporary, mock.patch.object(budget, 'BASE', Path(temporary)):
            root = Path(temporary)/'resources'; root.mkdir()
            r = dict(phase='development', gpu=True, cpu_ns=400*common.NS, gpu_ns=100*common.NS)
            (root/'sample.reservation.json').write_text(json.dumps(r))
            c, g = budget.accounting()
            self.assertEqual((c['development'], g['development']), (400*common.NS, 100*common.NS))
            (root/'sample.settlement.json').write_text(json.dumps(dict(r, cpu_ns=40*common.NS, gpu_ns=10*common.NS)))
            c, g = budget.accounting()
            self.assertEqual((c['development'], g['development']), (40*common.NS, 10*common.NS))
            self.assertEqual(json.loads((root/'sample.reservation.json').read_text()), r)

    def test_complete_disk_scan_counts_hardlinks_once_and_excludes_symlinks(self):
        with tempfile.TemporaryDirectory() as temporary, native_inventory_fixture(), mock.patch.object(common, 'BASE', Path(temporary)):
            root=Path(temporary);(root/'nested').mkdir()
            (root/'first').write_bytes(b'12345');(root/'nested/second').write_bytes(b'123')
            os.link(root/'first',root/'nested/hardlink')
            (root/'symlink').symlink_to(root/'nested/second')
            self.assertEqual(common.disk_bytes(),8)

    def test_later_cleanup_does_not_admit_science_without_fresh_gpu_receipt(self):
        with tempfile.TemporaryDirectory() as temporary, mock.patch.object(common,'BASE',Path(temporary)), mock.patch.object(budget,'BASE',Path(temporary)):
            root=Path(temporary);resources=root/'resources';resources.mkdir()
            settlement=resources/'failed.settlement.json'
            common.put(settlement,dict(status='refused',cleanup_empty=False,overrun=False))
            common.put(resources/'failed.cleanup-disposition.json',dict(status='cleanup_verified',
                settlement=common.ref(settlement),identities=[dict(pid=1,start_ticks=0)],
                admission_job='fresh-gpu',cpu_admission_job='fresh-cpu'))
            with mock.patch('lp_confirmation2_supervisor.same_process',return_value=False):
                budget.cleared(settlement,False,'admission','fresh-cpu')
                with self.assertRaises(FileNotFoundError):
                    budget.cleared(settlement,True,'development','science')
                with self.assertRaises(FileNotFoundError):
                    budget.cleared(settlement,True,'admission','fresh-gpu')
            self.assertFalse(common.load(settlement)['cleanup_empty'])

    def test_cleanup_disposition_refuses_a_still_live_owned_identity(self):
        with tempfile.TemporaryDirectory() as temporary, mock.patch.object(common,'BASE',Path(temporary)):
            root=Path(temporary);settlement=root/'failed.settlement.json'
            common.put(settlement,dict(status='refused',cleanup_empty=False,overrun=False))
            common.put(root/'failed.cleanup-disposition.json',dict(status='cleanup_verified',
                settlement=common.ref(settlement),identities=[dict(pid=1,start_ticks=0)]))
            with mock.patch('lp_confirmation2_supervisor.same_process',return_value=True):
                with self.assertRaisesRegex(ValueError,'still live'):
                    budget.cleared(settlement,False,'cleanup','cleanup')

    def test_cpu_construction_exception_cannot_admit_gpu_or_another_job(self):
        with tempfile.TemporaryDirectory() as temporary, mock.patch.object(common,'BASE',Path(temporary)), mock.patch.object(budget,'BASE',Path(temporary)):
            root=Path(temporary);resources=root/'resources';resources.mkdir()
            settlement=resources/'failed.settlement.json'
            common.put(settlement,dict(status='refused',cleanup_empty=False,overrun=False))
            source=root/'generator';source.write_text('admitted')
            disposition=resources/'failed.cleanup-disposition.json'
            common.put(disposition,dict(status='cleanup_verified',settlement=common.ref(settlement),
                identities=[dict(pid=1,start_ticks=0)],admission_job='gpu',cpu_admission_job='cpu'))
            common.put(root/'operational-readmissions/v7.json',dict(status='prospective',protocol=common.ref(source),
                cleanup_disposition=common.ref(disposition),admission_job='gpu',cpu_admission_job='cpu',
                cpu_only_jobs=['generate'],cpu_only_sources=[common.ref(source)]))
            common.put(resources/'cpu.settlement.json',dict(status='passed',cleanup_empty=True,overrun=False))
            with mock.patch('lp_confirmation2_supervisor.same_process',return_value=False):
                budget.cleared(settlement,False,'development','generate')
                with self.assertRaises(FileNotFoundError):
                    budget.cleared(settlement,True,'development','generate')
                with self.assertRaises(FileNotFoundError):
                    budget.cleared(settlement,False,'development','solve')
                source.write_text('changed')
                with self.assertRaisesRegex(ValueError,'source binding differs'):
                    budget.cleared(settlement,False,'development','generate')


if __name__ == '__main__':
    unittest.main()
