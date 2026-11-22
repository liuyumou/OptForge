"""Distinct deadline endpoints and repaired certificates cannot lose strict checks."""
import copy,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'tools'))
from lp_billion_full_audit import requests,validate
class FullAuditContracts(unittest.TestCase):
    def response(self):
        return dict(settings={'tolerance':1e-9},endpoint={'primal':'final400','dual':'dual400'},
                    certificate={'accepted':False},assessments=[dict(endpoint={'primal':'attempt500','dual':'dual500'},certificate={'accepted':False})])
    def test_deadline_restoration_keeps_distinct_intermediate(self):
        q,m,e=requests(self.response());self.assertEqual(len(q),2);self.assertEqual(m,[0,1])
    def test_identical_endpoint_reuses_proof_but_covers_both_claims(self):
        r=self.response();r['assessments'][0]['endpoint']=copy.deepcopy(r['endpoint'])
        q,m,e=requests(r);self.assertEqual(len(q),1);self.assertEqual(m,[0,0])
        proofs=[dict(model_sha256='model',tolerance=1e-9,accepted=False)]
        self.assertFalse(validate(proofs,m,e,'model',True))
        e[1]['certificate']['accepted']=True
        with self.assertRaisesRegex(ValueError,'differs accepted'):validate(proofs,m,e,'model',True)
    def test_repaired_dual_witness_binding_cannot_change(self):
        r=self.response();r['certificate']['certificate_dual_array']={'sha256':'original'}
        q,m,e=requests(r)
        proofs=[dict(model_sha256='model',tolerance=1e-9,accepted=False,certificate_dual_array={'sha256':'different'}),dict(model_sha256='model',tolerance=1e-9,accepted=False)]
        with self.assertRaisesRegex(ValueError,'differs certificate_dual_array'):validate(proofs,m,e,'model',True)
    def test_certificate_must_bind_original_model_and_tolerance(self):
        q,m,e=requests(self.response())
        for model,t in [('different',1e-9),('model',1e-6)]:
            proofs=[dict(model_sha256=model,tolerance=t,accepted=False)]*2
            with self.assertRaisesRegex(ValueError,'identity'):validate(proofs,m,e,'model',True)
    def test_copt_endpoint_is_independently_judged(self):
        q,m,e=requests(dict(has_solution=True,endpoint={'primal':'x','dual':'y'}),False)
        self.assertFalse(validate([dict(model_sha256='model',tolerance=1e-9,accepted=False)],m,e,'model',False))
if __name__=='__main__':unittest.main()
