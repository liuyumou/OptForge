import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'tools'))
from lp_billion_copt_nopresolve import Native
from lp_billion_copt_nopresolve_admit import validate_nonoptimal
from lp_billion_copt_nopresolve_continue import bounded_group,GIB

class NoPresolveContracts(unittest.TestCase):
    def native(self,wrong=False):
        api=Native.__new__(Native);api.prob=None;values={};calls=[]
        def call(name,prob,key,value):
            calls.append((name,key,value));values[key.decode()]=value
        api.call=call;api.get=lambda name,integer,parameter:1 if wrong else values[name]
        return api,calls
    def test_presolve_is_integer_and_roundtripped(self):
        api,calls=self.native();api.configure({'Presolve':0,'PDLPTol':1e-12,'FeasTol':1e-9})
        self.assertEqual(calls[0],('SetIntParam',b'Presolve',0));self.assertEqual(calls[1][0],'SetDblParam')
    def test_wrong_native_roundtrip_rejected(self):
        api,_=self.native(True)
        with self.assertRaises(ValueError):api.configure({'Presolve':0})
    def test_timeout_is_retained_as_unresolved_not_infeasibility_proof(self):
        for expect in ['infeasible','unbounded']:
            self.assertFalse(validate_nonoptimal(expect,dict(status=8,optimal=False),None))
    def test_wrong_or_optimal_status_on_known_nonoptimal_model_rejected(self):
        for expect,status in [('infeasible',3),('unbounded',2),('infeasible',1)]:
            with self.assertRaises(ValueError):validate_nonoptimal(expect,dict(status=status,optimal=status==1),None)
    def test_accepted_optimum_on_known_nonoptimal_model_rejected(self):
        with self.assertRaises(ValueError):validate_nonoptimal('infeasible',dict(status=2,optimal=False),dict(accepted=True))
    def model(self):return dict(nonzeros=1_000_000_000,columns=31_250_000,rows=31_250_000)
    def row(self,**updates):
        return dict(dict(id='test',nonzeros=64_000_000,capacity_observed=True,host_peak_bytes=2*GIB,owned_device_peak_bytes=2*GIB,vendor_mem_peak_mb=1000),**updates)
    def test_valid_observed_workspace_fits(self):
        self.assertTrue(bounded_group([self.row()],self.model())['admitted'])
    def test_one_failed_capacity_path_cannot_be_hidden(self):
        self.assertFalse(bounded_group([self.row(),self.row(capacity_observed=False)],self.model())['admitted'])
    def test_vendor_peak_is_compared_in_mb(self):
        x=bounded_group([self.row(vendor_mem_peak_mb=4000)],self.model())
        self.assertFalse(x['admitted']);self.assertEqual(x['forecast_vendor_mem_peak_mb'],62500)
    def test_host_growth_allowance_blocks_peak(self):
        x=bounded_group([self.row(host_peak_bytes=8*GIB)],self.model())
        self.assertFalse(x['admitted']);self.assertGreater(x['empirical_host_peak_with_allowance'],128*GIB)

if __name__=='__main__':unittest.main()
