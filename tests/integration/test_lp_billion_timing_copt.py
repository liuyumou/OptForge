"""Billion-scale timing coverage and exact native-adapter input boundaries."""
import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
import numpy as np

sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'tools'))
from lp_billion_timing import PHASES, process_ledger, validate_profile
from lp_billion_copt import read_array, finite, INF
from lp_billion_results import canonical


class TimingContracts(unittest.TestCase):
    def response(self):
        costs=dict.fromkeys(PHASES,2)
        return dict(input_ns=10,elapsed_ns=45,certificate={'accepted':False},solver_profile=dict(
            schema_version=1,clock='monotonic_host_wall',total_ns=40,exclusive_ns=costs,
            phase_entries=dict.fromkeys(PHASES,1),timer_overhead_included=True,kernel_active_time=False))
    def test_full_process_coverage_includes_residuals(self):
        r=process_ledger(self.response(),dict(process_ns=70,response_transport_ns=3,fresh_process_ns=73),7)
        self.assertEqual(r['total_ns'],80)
        self.assertEqual(sum(r['exclusive_ns'].values()),80)
        self.assertEqual(r['exclusive_ns']['process_startup_serialization_cleanup'],15)
    def test_rejects_missing_phase_wrong_sum_and_negative(self):
        for mutation in ['missing','sum','negative','bool']:
            r=self.response();p=r['solver_profile']
            if mutation=='missing':p['exclusive_ns'].pop(PHASES[0])
            elif mutation=='sum':p['total_ns']+=1
            elif mutation=='negative':p['exclusive_ns'][PHASES[0]]=-1
            else:p['exclusive_ns'][PHASES[0]]=True
            with self.assertRaises(ValueError):validate_profile(r)
    def test_rejects_overlapping_input_and_solver_intervals(self):
        with self.assertRaisesRegex(ValueError,'smaller'):
            process_ledger(self.response(),dict(process_ns=50,response_transport_ns=3,fresh_process_ns=53))
    def test_rejects_transport_accounting_gap(self):
        with self.assertRaisesRegex(ValueError,'transport'):
            process_ledger(self.response(),dict(process_ns=70,response_transport_ns=3,fresh_process_ns=74))
    def test_device_admission_checks_named_preparation_fields(self):
        from lp_billion_admit import validate_timings
        r=self.response()
        r['preparation_detail_ns']=dict(engine=1,operator=2,packing=3,control_initialization=4)
        r['cost_ns']=dict(host_preparation=10)
        validate_timings(r,True)
        missing=copy.deepcopy(r);missing.pop('solver_profile')
        with self.assertRaisesRegex(ValueError,'requested solver profile'):validate_timings(missing,True)
        r['cost_ns']['host_preparation']=11
        with self.assertRaisesRegex(ValueError,'preparation timing coverage'):validate_timings(r)
    def test_canonical_ignores_only_timing_not_certificate(self):
        a=self.response();b=copy.deepcopy(a);b['solver_profile']['total_ns']+=1
        self.assertEqual(canonical(a),canonical(b))
        b['certificate']['accepted']=True
        self.assertNotEqual(canonical(a),canonical(b))


class CoptArrayContracts(unittest.TestCase):
    def test_bounded_multichunk_read_preserves_bits(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);(root/'objects').mkdir();chunks=[]
            expected=np.array([0.,-0.,1.,-4.],dtype='<f8')
            for part in [expected[:2],expected[2:]]:
                b=part.tobytes();sha=hashlib.sha256(b).hexdigest()
                (root/'objects'/(sha+'.bin')).write_bytes(b);chunks.append(dict(sha256=sha,bytes=len(b)))
            spec=dict(dtype='f64le',count=4,chunks=chunks)
            self.assertTrue(np.array_equal(read_array(root,spec,'f64le',4).view('u8'),expected.view('u8')))
            (root/'objects'/(chunks[0]['sha256']+'.bin')).write_bytes(b'x'*16)
            with self.assertRaisesRegex(ValueError,'digest'):read_array(root,spec,'f64le',4)
    def test_rejects_incomplete_storage_before_allocating(self):
        with self.assertRaisesRegex(ValueError,'byte count'):
            read_array('/unused',dict(dtype='f64le',count=10**9,chunks=[]),'f64le',10**9)
    def test_finite_sentinel_and_nan_are_rejected(self):
        for v in [INF,-INF,float('nan'),float('inf')]:
            with self.assertRaises(ValueError):finite(np.array([v]),'test')
        finite(np.array([float('inf'),float('-inf'),1.]),'bounds',True)
    def test_native_parameter_type_comes_from_api_not_python_value(self):
        from lp_billion_copt import Native
        api=Native.__new__(Native);calls=[]
        api.call=lambda *args:calls.append(args)
        api.prob=None
        api.get=lambda name,integer,parameter:12000
        api.configure({'MemLimit':12000})
        self.assertEqual(calls[0][0],'SetDblParam')
    def test_native_gpu_path_stays_closed_before_admission(self):
        from lp_billion_copt import solve
        with self.assertRaisesRegex(ValueError,'ownership and peak-memory'):
            solve('/unused','/unused',gpu=True)


if __name__=='__main__':unittest.main()
