"""Strict ADR-0042 numerical/resource/evidence/report boundaries, source-only."""
import copy,sys,unittest,tempfile,os
from unittest.mock import patch
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'tools'))
from lp_protocol import ROOT,read_json
from lp_tensor_residual_common import CONFIG,protocol
from benchmark_lp_tensor_residual import jobs,effective,micro_jobs
from validate_artifacts import SchemaSnapshot
from report_lp_tensor_residual import gain,profile_eligible,report_output,useful_tensor,worker_bounds

class TensorContracts(unittest.TestCase):
 def test_frozen_roster_and_allocations(self):
  v=protocol();roster=list(jobs(v));self.assertEqual(len(roster),72);self.assertEqual(len(micro_jobs(v)),3)
  self.assertEqual(sum(effective(v,j)[2]+6 for j in roster if j['kind']=='timing'),1440)
  self.assertEqual(sum(effective(v,j)[2]+6 for j in roster if j['kind']=='profile')+105,525)
  self.assertEqual(v['allocated_gpu_seconds'],2665);self.assertEqual(v['additional_gpu_seconds'],0)
 def test_tuned_controls_obey_continuation_deadlines(self):
  from benchmark_lp_tensor_residual import control_job,prepare_inputs
  import benchmark_lp_tensor_residual as study
  v=protocol()
  for j in jobs(v):
   if j['configuration']['id']!='tuned-fp64' or j['kind']!='timing':continue
   inherited=control_job(v,j)
   self.assertEqual(inherited['instance']['time_limit_seconds'],8 if j['instance']['id'].endswith('-1024') else 28)
   with patch.object(study,'control_inputs',return_value='bound') as builder:
    self.assertEqual(prepare_inputs(v,j,ROOT,{}),'bound')
    self.assertEqual(builder.call_args.args[1],inherited)

 def test_phase_authority_inherits_accepted_amendments(self):
  v=protocol();parent=read_json(ROOT/'benchmarks/configs/lp-quant-resident-v1.json');base=read_json(ROOT/'benchmarks/configs/lp-campaign-v1.json')
  self.assertEqual(v['phase_gpu_seconds'],parent['phase_gpu_seconds']);self.assertNotEqual(v['phase_gpu_seconds'],base['phase_gpu_seconds']);self.assertEqual(v['cumulative_gpu_ns'],parent['cumulative_gpu_ns']);self.assertEqual(v['total_gpu_seconds'],base['total_gpu_seconds'])
 def test_native_promotion_and_malformed_worker_counters_cannot_supply_a_gain(self):
  e=dict(executor='gpu',outcome=dict(core=dict(stop='certified',failure=None),counts=dict(useful_windows=0,mma_instructions=0,accepted_nonzero_t=0,accepted_nonzero_f=0)))
  self.assertFalse(useful_tensor(e));e['outcome']['counts'].update(useful_windows=1,mma_instructions=16,accepted_nonzero_t=1,accepted_nonzero_f=1);self.assertTrue(useful_tensor(e))
  w=dict(elapsed_ns=10,leased_ns=11,peak_rss_bytes=0,queue_ns=0,activity=dict(device='GPU-test'));worker_bounds(w,12,'GPU-test')
  for k,x in [('elapsed_ns',True),('leased_ns',13),('peak_rss_bytes',-1)]:
   bad=copy.deepcopy(w);bad[k]=x
   with self.assertRaises(ValueError):worker_bounds(bad,12,'GPU-test')
 def test_fragment_loaders_cover_all_required_addresses_once(self):
  from lp_tensor_residual_layout_oracle import verify
  self.assertEqual(verify()["status"],"passed")
 def test_contract_changes_refuse(self):
  v=read_json(CONFIG);validator=SchemaSnapshot().validator('lp-tensor-residual-study-v1.schema.json')
  for k,x in [('allocated_gpu_seconds',2666),('prior_events',17199),('timing_repetitions',4),('profile_work',1999),('device','GPU-other')]:
   bad=copy.deepcopy(v);bad[k]=x
   with self.assertRaises(Exception):validator.validate(bad)
 def test_bootstrap_requires_complete_paired_coverage_and_adjusts_six_comparisons(self):
  self.assertIsNone(gain([(2.,1.)]*4));self.assertIsNone(gain([(2.,1.)]*5,False))
  self.assertFalse(gain([(1.,1.)]*5)['gain']);self.assertTrue(gain([(2.,1.)]*5)['gain']);self.assertEqual(gain([(2.,1.)]*5)['multiplicity'],6)
 def test_interrupted_profile_is_ineligible(self):
  e=dict(executor='gpu',request=dict(diagnostic=True,horizon=2000),outcome=dict(core=dict(iterations=2000,stop='work_horizon',failure=None),counts=dict(uncertain=0)));t=dict(status='completed');w=dict(reason='completed',returncode=0)
  self.assertTrue(profile_eligible(e,2000,True,t,w));self.assertFalse(profile_eligible(e,2000,False,t,w));self.assertFalse(profile_eligible(e,2000,True,dict(status='interrupted'),w));self.assertFalse(profile_eligible(e,2000,True,t,dict(reason='time_limit',returncode=0)))
 def test_historical_reports_and_aliases_are_protected(self):
  for path in ['docs/benchmarks/lp-quant-resident-gpup7r.md','docs/benchmarks/data/quant-resident/report.json','artifacts/gpup-quant-v1/report.json']:
   with self.assertRaises(ValueError):report_output(ROOT/path)
  with tempfile.TemporaryDirectory() as d, patch('report_lp_tensor_residual.BASE',Path(d)):
   p=Path(d)/'report.json';p.write_text('original')
   with self.assertRaises(ValueError):report_output(p)
   alias=Path(d)/'alias.json';alias.symlink_to(p)
   with self.assertRaises(ValueError):report_output(alias)
 def test_portable_evidence_schema_rejects_unknown_or_oversized_counters(self):
  e=read_json(ROOT/'tests/fixtures/lp-tensor-residual-evidence-v1.json');v=SchemaSnapshot().validator('lp-tensor-residual-evidence-v1.schema.json');v.validate(e)
  for key,value in [('mma_instructions',-1),('padded_products',2**64),('unexpected',0)]:
   bad=copy.deepcopy(e);bad['outcome']['counts'][key]=value
   with self.assertRaises(Exception):v.validate(bad)
if __name__=='__main__':unittest.main()
