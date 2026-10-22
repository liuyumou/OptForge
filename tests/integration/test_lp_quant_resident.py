"""Contract boundaries for the separate resident study and evidence reader."""
import copy,sys,unittest
from pathlib import Path
from fractions import Fraction as F
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'tools'))
from lp_protocol import ROOT,read_json
from lp_quant_resident_budget import CONFIG,protocol
from benchmark_lp_quant_resident import jobs,effective,micro_jobs
from validate_artifacts import SchemaSnapshot

class ResidentContracts(unittest.TestCase):
 def test_allocation_and_roster_fit_unchanged_authority(self):
  v=protocol();parent=read_json(ROOT/'benchmarks/configs/lp-quant-v1.json');roster=list(jobs(v))
  self.assertEqual(len(roster),117);self.assertEqual(len(micro_jobs(v)),3)
  self.assertEqual(sum(effective(v,j)[2]+6 for j in roster if j['kind']=='timing'),2268)
  self.assertEqual(sum(effective(v,j)[2]+6 for j in roster if j['kind']=='profile')+108,432)
  self.assertEqual(v['phase_gpu_seconds'],parent['phase_gpu_seconds']);self.assertEqual(v['cumulative_gpu_ns'],parent['cumulative_gpu_ns'])
  self.assertEqual(v['additional_gpu_seconds'],0);self.assertEqual(v['allocated_gpu_seconds'],3600)

 def test_frozen_protocol_rejects_contract_and_budget_changes(self):
  v=read_json(CONFIG);validator=SchemaSnapshot().validator('lp-quant-resident-study-v1.schema.json');validator.validate(v)
  for k,x in [('additional_gpu_seconds',1),('allocated_gpu_seconds',3601),('prior_events',17035),('planned_attempts',121),('profile_work',1999),('order_seed',17),('device','GPU-other')]:
   bad=copy.deepcopy(v);bad[k]=x
   with self.assertRaises(Exception):validator.validate(bad)
  bad=copy.deepcopy(v);bad['configurations'][0]['settings']['primal_budget']=1e-6
  with self.assertRaises(Exception):validator.validate(bad)

 def test_cpu_refusals_remain_in_denominator(self):
  v=protocol();a=read_json(ROOT/v['cpu_admission']['path']);eligible={(r['model'],r['configuration']):r['eligible'] for r in a['rows']}
  self.assertEqual(len(eligible),72);self.assertEqual(sum(r['useful_low'] for r in a['rows']),0)
  timing=[j for j in jobs(v) if j['kind']=='timing'];self.assertEqual(len(timing),108)
  self.assertEqual(sum(eligible[(j['instance']['id'],j['configuration']['id'])] for j in timing),36)
  self.assertEqual(sum(eligible[(j['instance']['id'],j['configuration']['id'])] for j in jobs(v) if j['kind']=='profile'),3)

 def test_profiles_require_exact_verified_gpu_horizon(self):
  from report_lp_quant_resident import profile_complete
  e=dict(executor='gpu',request=dict(diagnostic=True,horizon=2000),outcome=dict(horizon=2000,first_certified_iteration=1400,core=dict(stop='work_horizon',iterations=2000,physical=2067,failure=None),counts=dict(uncertain=0)))
  self.assertTrue(profile_complete(e,2000));self.assertFalse(profile_complete(e,2000,False))
  for field,value in [('executor','cpu'),('request',dict(diagnostic=False,horizon=2000))]:
   bad=copy.deepcopy(e);bad[field]=value;self.assertFalse(profile_complete(bad,2000))
  for field,value in [('stop','time_limit'),('stop','certified'),('iterations',1999),('failure',dict(reason='device_failure'))]:
   bad=copy.deepcopy(e);bad['outcome']['core'][field]=value;self.assertFalse(profile_complete(bad,2000))
  bad=copy.deepcopy(e);bad['outcome']['counts']['uncertain']=32;self.assertFalse(profile_complete(bad,2000))

 def test_fallback_never_counts_as_resident_success(self):
  from report_lp_quant_resident import successful_solve
  self.assertFalse(successful_solve(dict(record=dict(backend='highs',termination='optimal')),'cuda-lp-tuned'))
  e=dict(executor='gpu',outcome=dict(core=dict(stop='certified',failure=None)));self.assertTrue(successful_solve(e,'lp-quant-resident-v1'))
  e['outcome']['core']['stop']='time_limit';self.assertFalse(successful_solve(e,'lp-quant-resident-v1'))

 def test_successor_arithmetic_encloses_exact_boundaries(self):
  from lp_quant_resident_oracle import add,mul,div
  for a,b in [(F(1),F(1,2**53)),(F(1,2**1074),F(3,2**1074)),(F(2)**100,F(2)**-100),(F(1,2**1022),F(1,2**1022))]:
   self.assertGreaterEqual(add(a,b),a+b);self.assertGreaterEqual(mul(a,b),a*b);self.assertGreaterEqual(div(a,b),a/b)

 def test_resident_schema_rejects_unknowns_and_oversized_counters(self):
  e=read_json(ROOT/'tests/fixtures/lp-quant-resident-evidence-v1.json');validator=SchemaSnapshot().validator('lp-quant-resident-evidence-v1.schema.json');validator.validate(e)
  for key,value in [('extra',1),('launches',2**64)]:
   bad=copy.deepcopy(e);bad[key]=value
   with self.assertRaises(Exception):validator.validate(bad)
  bad=copy.deepcopy(e);bad['outcome']['counts']['guard_products']=2**64
  with self.assertRaises(Exception):validator.validate(bad)

 def test_delivery_rejects_oversized_and_inconsistent_physical_work(self):
  from lp_quant_resident_delivery import metadata
  e=read_json(ROOT/'tests/fixtures/lp-quant-resident-evidence-v1.json');metadata(e)
  for field,value in [('launches',2**64-1),('launches',e['launches']+1),('upload_bytes',2**64-1),('readback_bytes',2**64-1),('host_product_scans',1),('product_vector_transfers',1)]:
   bad=copy.deepcopy(e);bad[field]=value
   with self.assertRaises(ValueError):metadata(bad)

 def test_delivery_rejects_invalid_source_archive_members(self):
  import io,tarfile,tempfile
  from lp_quant_resident_delivery import archive_digest
  with tempfile.TemporaryDirectory() as d:
   for name,kind in [('../escape',tarfile.REGTYPE),('link',tarfile.SYMTYPE)]:
    p=Path(d)/'source.tar'
    with tarfile.open(p,'w') as a:
     m=tarfile.TarInfo(name);m.type=kind;m.size=0;a.addfile(m,io.BytesIO())
    with self.assertRaises(ValueError):archive_digest(p)

if __name__=='__main__':unittest.main()
