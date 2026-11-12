"""CPU contract/checker admission for coupled FP4 integration; no device context."""
from copy import deepcopy
from fractions import Fraction as F
import json,subprocess,sys,tempfile,unittest
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'tools'))
import lp_fp4_integrate_model as m
import lp_fp4_recovery_contract as policy
from lp_fp4_integrate_common import put,load,ref
from lp_fp4_integrate_run import BINARY

class Models(unittest.TestCase):
 def test_coupled_tail_and_original_sign_offset(self):
  for family in m.FAMILIES:
   doc,d=m.model(family);n=len(d['c']);self.assertEqual(doc['objective']['offset'],3.25)
   self.assertGreater(np.max(np.abs(d['a'][:32,32:]))+np.max(np.abs(d['a'][32:,:32])),0)
   self.assertEqual(len(doc['variables']),n)
   if family=='dense-rich-65':self.assertEqual(doc['objective']['sense'],'maximize')
 def test_preparation_both_orientations_share_original_tiles(self):
  _,d=m.model('irregular-tail-33')
  for f,k in m.LANES:
   r=m.prepare(d,f,k);self.assertEqual(len(r['initial']),320)
   self.assertEqual(r['initial_iteration'],0);self.assertEqual(r['max_updates'],600)
   self.assertLessEqual((2**-r['shift'])**2*np.linalg.norm(d['a'],1)*np.linalg.norm(d['a'],np.inf),.75)
   self.assertTrue(all(-48<=e<=48 for e in r['exponents']))
 def test_original_a_observation_matches_rational_oracle(self):
  _,d=m.model('coupled-equality');raw=m.initial(d);n=len(d['c']);p=(n+31)//32*32
  bound=lambda a:[None if not np.isfinite(x) else float(x) for x in a]
  exact=policy.residual_observation(d['a'].tolist(),d['c'].tolist(),bound(d['rl']),bound(d['ru']),bound(d['lo']),bound(d['hi']),raw[:n],raw[p:p+n])
  got=m.observation(d,raw)
  for k in exact:self.assertAlmostEqual(got[k],float(exact[k]),places=14)
 def test_initial_state_is_nonzero_and_not_solved(self):
  for family in m.FAMILIES:
   _,d=m.model(family);raw=m.initial(d);self.assertGreater(m.observation(d,raw)['rho'],1e-4)
   p=len(raw)//5;self.assertEqual(raw[:p],raw[3*p:4*p]);self.assertEqual(raw[p:2*p],raw[4*p:])
 def test_reference_keeps_anchors_and_handles_all_bounds(self):
  for family in m.FAMILIES:
   _,d=m.model(family);r=m.prepare(d,64,1);raw=m.reference(d,r['initial'],3,r['shift']);p=len(raw)//5
   self.assertEqual(raw[3*p:],r['initial'][3*p:]);self.assertTrue(np.isfinite(raw).all())
   self.assertNotEqual(raw[:p],r['initial'][:p])
 def test_no_unknown_lanes(self):
  _,d=m.model('coupled-equality')
  with self.assertRaises(ValueError):m.prepare(d,4,3)
  with self.assertRaises(ValueError):m.model('unknown')

class Checker(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  if not BINARY.exists():raise unittest.SkipTest('isolated integration binary not built')
 def check(self,doc,x,y,tier='certified-1e-9',transport='completed'):
  # Keep fixtures under the repository because evidence refs forbid outside roots.
  with tempfile.TemporaryDirectory(dir=ROOT/'target') as t:
   p=Path(t);put(p/'model.json',doc);put(p/'endpoint.json',dict(model_sha256=ref(p/'model.json')['sha256'],primal=list(map(float,x)),dual=list(map(float,y)),transport=transport))
   subprocess.run([str(BINARY),'check',str(p/'model.json'),str(p/'endpoint.json'),tier,str(p/'certificate.json')],check=True,capture_output=True,timeout=10)
   return load(p/'certificate.json')
 def test_constructed_nonzero_endpoints_certify_both_tiers(self):
  for family in m.FAMILIES:
   if family=='infinite-bound-refusal':continue
   doc,d=m.model(family)
   for tier in ('certified-1e-7','certified-1e-9'):
    with self.subTest(family=family,tier=tier):self.assertTrue(self.check(doc,d['target_x'],d['target_y'],tier)['accepted'])
 def test_infinite_bound_refusal_is_unchanged(self):
  doc,d=m.model('infinite-bound-refusal');r=self.check(doc,d['target_x'],d['target_y'])
  self.assertFalse(r['accepted']);self.assertIsNone(r['bound']);self.assertIn('infinite bound',r['refusal'])
 def test_initial_nonoptimal_and_cancelled_do_not_certify(self):
  doc,d=m.model('coupled-equality');r=m.initial(d);p=len(r)//5
  self.assertFalse(self.check(doc,r[:p],r[p:2*p])['accepted'])
  self.assertFalse(self.check(doc,d['target_x'],d['target_y'],transport='cancelled')['accepted'])
 def test_looser_tier_is_not_strict_pass(self):
  bound=lambda v:dict(kind='finite',value=v)
  doc=dict(schema_version=1,model_id='tier-separation',variables=[dict(id=7,domain='continuous',lower=bound(0),upper=bound(1))],constraints=[],objective=dict(sense='minimize',offset=0.,terms=[dict(variable_id=7,coefficient=1.)]))
  self.assertTrue(self.check(doc,[5e-8],[],'certified-1e-7')['accepted'])
  self.assertFalse(self.check(doc,[5e-8],[],'certified-1e-9')['accepted'])

class PolicyIdentityTests(unittest.TestCase):
 def test_fast_policy_is_exact_schema_admitted_policy(self):
  from lp_fp4_integrate_policy import admitted_policy
  import lp_fp4_recovery_contract as policy
  self.assertEqual(admitted_policy(),policy.policy())
 def test_modified_policy_refused(self):
  from lp_fp4_integrate_policy import admitted_policy
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'policy.json';p.write_text('{}')
   with self.assertRaises(ValueError):admitted_policy(p)

if __name__=='__main__':unittest.main()
