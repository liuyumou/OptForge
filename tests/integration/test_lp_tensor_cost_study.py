"""CPU-only guards for ADR-0044's frozen roster and forecast boundaries."""
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'tools'))
from lp_tensor_cost_common import protocol
from benchmark_lp_tensor_cost import jobs,effective,prepare_inputs
from lp_tensor_cost_accept import acceptance_jobs
from lp_tensor_cost_screen import integer,profile_complete,forecast,RULE
from validate_artifacts import validator

class CostStudyTests(unittest.TestCase):
 def test_exact_roster_and_phase_caps(self):
  value=protocol();validator('lp-tensor-cost-study-v1.schema.json').validate(value)
  rows=list(jobs(value))
  self.assertEqual(len(rows),76);self.assertEqual(len({r['id'] for r in rows}),76)
  self.assertEqual([r['kind'] for r in rows[:16]],['profile']*16)
  self.assertEqual(sum(effective(value,r)[2]+6 for r in rows if r['kind']=='profile'),320)
  self.assertEqual(sum(effective(value,r)[2]+6 for r in rows if r['kind']=='timing'),990)
  self.assertEqual(sum(seconds+6 for _,seconds in acceptance_jobs()),496)
  self.assertEqual(sum('ablation' in r for r in rows),4)
  for row in rows:
   if row['kind']=='profile' and row['configuration']['backend']=='lp-tensor-cost-v1':
    self.assertEqual(effective(value,row)[1]['iteration_limit'],50000)

 def test_tuned_profiles_use_own_cli_and_deadline(self):
  v=protocol();identity={}
  for j in jobs(v):
   if j['kind']!='profile' or j['configuration']['id']!='tuned-fp64':continue
   worker,docs=prepare_inputs(v,j,Path('/tmp/cost-frozen'),identity)
   self.assertIn('/tmp/cost-frozen/optimizer',worker['command'])
   self.assertNotIn('/tmp/cost-frozen/lp_precision_tensor_cost',worker['command'])
   self.assertIn('--cost-profile',worker['command'])
   self.assertEqual(docs[j['id']+'.solve.json']['time_limit_ms'],worker['solve_seconds']*1000)
   self.assertEqual(docs[j['id']+'.method.json']['iteration_limit'],2000)

 def test_counter_types_are_strict(self):
  for bad in [True,-1,1.0,'1',None]:
   with self.assertRaises(ValueError):integer(bad)
  self.assertEqual(integer(0),0)

 def test_incomplete_profiles_never_qualify(self):
  e=dict(executor='gpu',outcome=dict(core=dict(iterations=2000,stop='work_horizon',failure=None),counts=dict(uncertain=0)))
  job=dict(configuration=dict(backend='lp-tensor-cost-v1'))
  trial=dict(status='completed');worker=dict(reason='completed',returncode=0)
  self.assertTrue(profile_complete(e,job,trial,worker))
  self.assertFalse(profile_complete(e,job,dict(status='interrupted'),worker))
  e['outcome']['core']['iterations']=1999
  self.assertFalse(profile_complete(e,job,trial,worker))

 def test_forecast_keeps_predeclared_threshold(self):
  self.assertEqual(RULE['threshold'],0.9);self.assertEqual(RULE['required_profiles'],16)
  self.assertEqual(RULE['negative_residual'],'refuse')
  self.assertEqual(protocol()['analysis'],dict(comparisons=6,confidence=.95,resamples=10000,seed=17002))

 def test_forecast_uses_prefix_and_maximum_tail_once(self):
  v=protocol();d=Path('/tmp/cost-frozen')
  custom=dict(executor='gpu',outcome=dict(core=dict(iterations=2000,stop='work_horizon',failure=None),first_certified_iteration=200,counts=dict(uncertain=0,useful_windows=1,mma_instructions=1,accepted_nonzero_t=1,accepted_nonzero_f=1)),phases_ns=dict(execute_total=200,delivery_original_assessment=10,**{'boundary/200/execute_total':100}))
  tuned=dict(record=dict(backend='cuda-lp-tuned',termination='optimal'),assessment=dict(gap_closed=True))
  def load(path):
   name=path.name
   if name=='forecast-rule.json':return RULE
   if name.endswith('.trial.json'):return dict(status='completed')
   if name.endswith('.worker.json'):return dict(reason='completed',returncode=0,elapsed_ns=300)
   if name.endswith('.raw-cost.json'):return dict(elapsed_ns=250)
   return custom
  with patch('pathlib.Path.exists',return_value=True),patch('lp_tensor_cost_screen.read_json',side_effect=load),patch('lp_tensor_cost_screen.file_hash',return_value='frozen'),patch('benchmark_lp_tensor_cost.verify_endpoint'),patch('benchmark_lp_adaptive_cost.endpoint_shape',return_value=tuned):
   result=forecast(v,d,{},persist=False)
  self.assertTrue(result['passed']);self.assertEqual(result['maximum_producer_tail_ns'],100)
  self.assertEqual({r['forecast_ns'] for r in result['forecasts']},{210})
