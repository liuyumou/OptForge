"""The actual legacy diagnostics omit execution; consume disjoint cost observations."""
import copy
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'tools'))
from lp_resident2_study_v4 import physical_counts

class Resident2PhysicalCounters(unittest.TestCase):
    def fixture(self):
        return dict(error=None,diagnostics=dict(kernel_launches=4),native_costs=dict(unavailable=[],
            counters=dict(host_to_device_bytes=32,device_to_host_bytes=16,device_allocated_bytes=48),
            scopes=[dict(path=['native','kernel_submission'],calls=4),
                    dict(path=['upload','device_synchronization'],calls=2),
                    dict(path=['read','device_synchronization'],calls=1)]))
    def test_disjoint_nested_calls_and_bytes(self):
        c=physical_counts(self.fixture())
        self.assertEqual(c['kernel_launches'],4)
        self.assertEqual(c['synchronizations'],3)
        self.assertEqual(c['upload_bytes'],32)
    def test_partial_duplicate_or_invalid_observations_refuse(self):
        for kind in ['partial','duplicate','boolean','mismatch']:
            r=self.fixture()
            if kind=='partial':r['native_costs']['unavailable']=['partial']
            if kind=='duplicate':r['native_costs']['scopes']*=2
            if kind=='boolean':r['native_costs']['scopes'][0]['calls']=True
            if kind=='mismatch':r['diagnostics']['kernel_launches']=3
            with self.assertRaises(ValueError):physical_counts(r)

if __name__=='__main__':unittest.main()
