"""CPU-only timing and comparison contracts; no installed vendor dependencies."""
import copy
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'tools'))
from lp_resident2_study import compare, eligible, phase_totals, roster

class Resident2Contract(unittest.TestCase):
    def test_disjoint_clocks_include_residual(self):
        w=dict(solves=1,conversion_ns=1,preparation_ns=2,import_ns=3,
               rows=[dict(native_ns=4,export_ns=5,output_ns=6)])
        phases=phase_totals(w,[7],30)
        self.assertEqual(sum(phases.values()),30)
        self.assertEqual(phases['unattributed'],2)
        with self.assertRaises(ValueError):phase_totals(w,[7],27)
        with self.assertRaises(ValueError):phase_totals(w,[],30)
        w['conversion_ns']=-1
        with self.assertRaises(ValueError):phase_totals(w,[7],30)

    def test_only_same_transport_certified_completed_pairs(self):
        c=dict(model={'sha256':'a'},lifecycle='cold',repetition=0,solves=1,status='completed',
               elapsed_ns=20,results=[dict(accepted=True,stop='accepted',iterations=200)])
        r=copy.deepcopy(c);r['elapsed_ns']=10
        self.assertEqual(compare(c,r),2)
        for key,value in [('accepted',False),('stop','time_limit'),('iterations',None)]:
            bad=copy.deepcopy(r);bad['results'][0][key]=value
            self.assertIsNone(compare(c,bad))
        r['lifecycle']='prepared'
        with self.assertRaises(ValueError):compare(c,r)
        self.assertFalse(eligible(dict(status='completed',elapsed_ns=1,results=[])))

    def test_complete_balanced_roster_and_bounded_jobs(self):
        jobs=roster([dict(id=str(i),model=dict(path=str(i),sha256=str(i))) for i in range(8)])
        self.assertEqual(len(jobs),64)
        self.assertEqual(len({j['id'] for j in jobs}),64)
        self.assertEqual(sum(j['solves'] for j in jobs),96)
        for i in range(0,len(jobs),2):
            self.assertEqual({j['mode'] for j in jobs[i:i+2]},{'control','resident'})
            self.assertEqual(jobs[i]['model'],jobs[i+1]['model'])
        self.assertEqual({j['native_seconds'] for j in jobs},{8})

if __name__=='__main__':unittest.main()
