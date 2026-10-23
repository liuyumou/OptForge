"""Independent format semantics and strict frozen-protocol/schema regressions."""
import copy,sys,unittest
from fractions import Fraction as F
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'tools'))
from lp_quant_oracle import decode
from lp_quant_budget import CONFIG
from lp_protocol import read_json
from validate_artifacts import SchemaSnapshot
class QuantContracts(unittest.TestCase):
 def test_format_limits_and_reserved_codes(self):
  self.assertEqual(decode('e4m3',0x7e),F(448));self.assertIsNone(decode('e4m3',0x7f));self.assertEqual(decode('e5m2',0x7b),F(57344));self.assertIsNone(decode('e5m2',0x7c));self.assertEqual(decode('fp16',1),F(1,1<<24));self.assertEqual(decode('e4m3',1),F(1,1<<9));self.assertEqual(decode('e5m2',1),F(1,1<<16))
 def test_frozen_protocol_rejects_budget_seed_and_policy_mutations(self):
  v=read_json(CONFIG);validator=SchemaSnapshot().validator('lp-quant-study-v1.schema.json');validator.validate(v)
  for field,value in [('combined_cap_seconds',3601),('prior_events',0),('order_seed',17002),('additional_gpu_seconds',0),('device','GPU-other')]:
   bad=copy.deepcopy(v);bad[field]=value
   with self.assertRaises(Exception):validator.validate(bad)
 def test_settings_schema_rejects_future_quantization_and_unknowns(self):
  schema=SchemaSnapshot().validator('lp-quant-request-v1.schema.json').schema['properties']['settings']
  from jsonschema import Draft202012Validator
  validator=Draft202012Validator(schema);settings=read_json(CONFIG)['configurations'][0]['settings'];validator.validate(settings)
  for k,value in [('tile_size',16),('rounding','stochastic'),('primal_budget',1e-6),('format','fp4'),('extra',0)]:
   bad=dict(settings);bad[k]=value
   with self.assertRaises(Exception):validator.validate(bad)
 def test_resource_monitor_finds_thread_spawned_children(self):
  import concurrent.futures,os,subprocess
  from lp_quant_resources import process_tree
  before,_=process_tree(os.getpid())
  with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
   child=pool.submit(subprocess.Popen,[sys.executable,'-c','import sys; data=bytearray(16<<20); print("ready",flush=True); sys.stdin.read()'],stdin=subprocess.PIPE,stdout=subprocess.PIPE,text=True).result()
   try:
    self.assertEqual(child.stdout.readline().strip(),'ready')
    after,_=process_tree(os.getpid());self.assertGreater(after,before+(8<<20))
   finally:child.communicate('');self.assertEqual(child.returncode,0)
 def test_report_excludes_fallback_and_incomplete_profile_horizons(self):
  from report_lp_quant import successful_solve,profile_complete
  e=dict(record=dict(backend='highs',termination='optimal'),diagnostics=dict(profile=True,iterations=1400),control=dict(physical_iterations=1400,logical_iterations=1400))
  self.assertFalse(successful_solve(e,'cuda-lp-tuned'))
  e['record']['backend']='cuda-lp-tuned';self.assertTrue(successful_solve(e,'cuda-lp-tuned'));self.assertFalse(profile_complete(e,2000))
  e['diagnostics']['iterations']=2000;e['control']=dict(physical_iterations=2000,logical_iterations=2000);self.assertTrue(profile_complete(e,2000))
  q=dict(executor='gpu',outcome=dict(stop='iteration_limit',physical=1999,failure=None));self.assertFalse(profile_complete(q,2000));q['outcome']['physical']=2000;self.assertTrue(profile_complete(q,2000));q['outcome']['stop']='time_limit';self.assertFalse(profile_complete(q,2000))
if __name__=='__main__':unittest.main()
