"""Whole-roster resource and unsupported-lane coverage before any billion attempt."""
import sys,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'tools'))
import lp_billion_full_run as full
class FullRunContracts(unittest.TestCase):
    def fixture(self):
        models={f:dict(rows=4,columns=4,nonzeros=20,canonical_tiles=0,covered_nnz=0,model={'sha256':f}) for f in full.FAMILIES}
        capacity={f:{lane:dict(admitted=True,host_gib=128,device_gib=80 if lane=='copt-gpu-pdlp' else 0) for lane in full.LANES[3:]} for f in full.FAMILIES}
        return models,capacity,{k:0 for k in full.CPU_CAPS},{k:0 for k in full.GPU_CAPS},0
    def plans(self,args):
        with patch.object(full,'ref',side_effect=lambda p:{'path':str(p)}):return full.candidates(*args)
    def test_every_ceiling_keeps_full_thirty_cell_roster_and_cadences(self):
        for p in self.plans(self.fixture()):
            self.assertEqual(len(p['cells']),30);self.assertEqual(len({(c['family'],c['lane']) for c in p['cells']}),30)
            for c in p['cells']:
                if c['lane'] in full.LANES[:3]:
                    self.assertEqual(c['request']['settings']['tolerance'],1e-9)
                    self.assertEqual(c['request']['settings']['check_interval'],500)
                    self.assertEqual(c['request']['tensor']['control_interval'],100)
    def test_unsupported_vendor_lane_remains_visible(self):
        args=self.fixture();args[1]['degenerate']['copt-gpu-pdlp']['admitted']=False
        for p in self.plans(args):
            matches=[c for c in p['cells'] if (c['family'],c['lane'])==('degenerate','copt-gpu-pdlp')]
            self.assertEqual(len(matches),1);self.assertEqual(matches[0]['status'],'unsupported_capacity')
    def test_whole_audits_and_storage_can_refuse_an_otherwise_fitting_solve(self):
        args=self.fixture();args[2]['reporting']=full.CPU_CAPS['reporting']*full.NS
        self.assertTrue(all('whole strict audit CPU plus final reporting' in p['rejected_by'] for p in self.plans(args)))
        args=self.fixture();args=list(args);args[4]=full.DISK_LIMIT
        self.assertTrue(all('whole storage including repaired witnesses' in p['rejected_by'] for p in self.plans(args)))
    def test_extra_assessments_increase_audit_and_witness_reservations(self):
        plans=self.plans(self.fixture());a,b=plans[0],plans[1]
        self.assertGreater(b['audit_cpu_seconds'],a['audit_cpu_seconds']);self.assertGreater(b['storage_bytes'],a['storage_bytes'])
if __name__=='__main__':unittest.main()
