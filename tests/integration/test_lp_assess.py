"""Independent ADR-0039 policy, frozen protocol, identity and budget contracts."""
import copy
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
from jsonschema import ValidationError
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools'))
import lp_assess_admission as oracle
import lp_assess_budget as budget
import benchmark_lp_assess as study
from lp_copt_budget import ComparisonLedger
from lp_protocol import read_json
from validate_artifacts import validator

class AssessmentContracts(unittest.TestCase):
    def test_frozen_roster_and_reservations(self):
        v=budget.protocol();jobs=list(study.jobs(v))
        self.assertEqual(len(jobs),60);self.assertEqual(len({j['id'] for j in jobs}),60)
        self.assertEqual({k:sum(study.effective(v,j)[2]+6 for j in jobs if j['kind']==k) for k in ['timing','profile']},{'timing':1248,'profile':432})
        self.assertEqual(v['combined_cap_seconds'],2300);self.assertEqual(v['prior_events'],16684)
        self.assertEqual(v['cumulative_gpu_ns'],21602574545061)
        self.assertEqual({j['configuration']['arithmetic'] for j in jobs},{'tuned_fp64','accumulation_fp32'})
        self.assertEqual({j['configuration']['policy'] for j in jobs},{'fixed_200','bounded_800'})
    def test_cpu_admission_preserves_all_trajectories(self):
        v=budget.protocol();r=read_json(ROOT/v['cpu_admission']['path'])
        self.assertEqual(r['gpu_seconds'],0);self.assertEqual(r['status'],'passed');self.assertEqual(len(r['rows']),16)
        self.assertTrue(all(x['physical_steps']==4000 for x in r['rows']))
        self.assertLess(r['cpu_seconds'],21600);self.assertLess(r['max_child_rss_bytes'],8<<30)
    def test_independent_zero_motion_transient_and_delayed_success(self):
        cases=oracle.synthetic();self.assertTrue(cases[1]['missed_transient_success']);self.assertEqual(cases[2]['added_updates'],600)
        self.assertTrue(cases[0]['horizon_censored']);self.assertEqual(cases[3]['first_bounded_success'],200)
    def test_final_assessment_is_part_of_discovery(self):
        frames=[dict(point=dict(iteration=i*200),scaled_primal=[0.],scaled_dual=[]) for i in range(1,5)]
        r=oracle.replay(frames,dict(scaled_primal=[0.],scaled_dual=[]),[False,False,False,True])
        self.assertEqual(r['first_bounded_success'],800);self.assertFalse(r['horizon_censored']);self.assertEqual(r['selected'],[200])
        r=oracle.replay(frames,dict(scaled_primal=[0.],scaled_dual=[]),[False]*4,801,True)
        self.assertEqual(r['first_fixed_success'],801);self.assertEqual(r['first_bounded_success'],801)
    def test_public_authority_refuses_before_private_ledger(self):
        v=budget.protocol()
        with patch('lp_refine_budget.ledger_for',side_effect=AssertionError('private ledger accessed')) as parent:
            for key,wrong in [('prior_events',0),('combined_cap_seconds',2301),('cumulative_gpu_ns',28800*10**9),('device','GPU-wrong')]:
                changed=copy.deepcopy(v);changed[key]=wrong
                with self.assertRaises((ValueError,ValidationError)):budget.ledger_for(changed)
            parent.assert_not_called()
    def test_ledger_does_not_refund_a_crashed_attempt(self):
        v=budget.protocol()
        with tempfile.TemporaryDirectory() as d:
            with ComparisonLedger(Path(d),'a'*64,v) as ledger:
                ledger.reserve(v['id']+'-accept-simulation',20,phase='repeatability')
                with self.assertRaises(ValueError):ledger.reserve(v['id']+'-profile-wrong',1,phase='screening')
                with self.assertRaises(ValueError):ledger.reserve(v['id']+'-profile-excess',451,phase='ablations')
            with ComparisonLedger(Path(d),'a'*64,v) as ledger:
                self.assertEqual(ledger.usage('accept'),20*10**9);self.assertFalse(ledger.pending())
                with self.assertRaises(ValueError):ledger.reserve(v['id']+'-accept-simulation',1,phase='repeatability')
    def test_request_binds_arithmetic_policy_profile_and_image(self):
        v=budget.protocol();job=next(j for j in study.jobs(v) if j['kind']=='profile' and j['configuration']['arithmetic']=='accumulation_fp32' and j['configuration']['policy']=='bounded_800')
        identity=dict(source_tree_sha256='a'*64,exec_binary_sha256='b'*64,images={'lp_pdhg_tuned.cubin':'c'*64,'lp_pdhg_precision.cubin':'d'*64})
        with tempfile.TemporaryDirectory() as d:
            d=Path(d);request=study.write_inputs(v,job,d,identity);study.check_request(v,job,d,identity,request)
            payload=read_json(d/(job['id']+'.assess-request.json'));validator('lp-assess-request-v1.schema.json').validate(payload)
            self.assertEqual(payload['code_object_sha256'],'d'*64);self.assertTrue(payload['diagnostic']);self.assertEqual(payload['method']['iteration_limit'],2000)
            for key,wrong in [('policy','fixed_200'),('arithmetic','tuned_fp64'),('diagnostic',False)]:
                bad=copy.deepcopy(payload);bad[key]=wrong;(d/(job['id']+'.assess-request.json')).write_text(__import__('json').dumps(bad))
                with self.assertRaises(ValueError):study.check_request(v,job,d,identity,request)
            for bad in [{**payload,'unknown':True},{k:x for k,x in payload.items() if k!='diagnostic'}]:
                with self.assertRaises(ValidationError):validator('lp-assess-request-v1.schema.json').validate(bad)
    def test_evidence_schema_covers_complete_cpu_witnesses(self):
        v=budget.protocol();r=read_json(ROOT/v['cpu_admission']['path'])
        # Private traces are optional in ordinary CI; a materialized trace must
        # satisfy the same schema used by the frozen online verifier.
        path=ROOT/r['rows'][0]['trace']['path']
        if path.exists():
            e=read_json(path);validator('lp-assess-evidence-v1.schema.json').validate(e)
            for key in ['point','physical_steps','failure']:
                bad=copy.deepcopy(e);del bad['witness']['outcome'][key]
                with self.assertRaises(ValidationError):validator('lp-assess-evidence-v1.schema.json').validate(bad)
    def test_replay_matches_bits_instead_of_float_value_equality(self):
        from lp_assess_accept import replay_matches
        a=dict(witness=dict(request={},outcome=dict(point=[0.0]),traces=[]),assessment={})
        b=copy.deepcopy(a);b['witness']['outcome']['point'][0]=-0.0
        self.assertEqual(a,b)
        self.assertFalse(replay_matches(a,b));self.assertTrue(replay_matches(a,a))
    def test_unverified_partial_profiles_remain_unavailable(self):
        from report_lp_assess import profile_comparisons
        v=budget.protocol()
        with tempfile.TemporaryDirectory() as d:
            d=Path(d)
            for name in v['profile_instances']:
                for c in v['configurations']:
                    (d/(v['id']+'-profile-'+name+'-0-'+c['id']+'.endpoint.json')).write_text('{')
            rows=profile_comparisons(v,d,set())
            self.assertEqual(len(rows),6);self.assertTrue(all(not r['available'] for r in rows))
    def test_acceptance_labels_cannot_launch_unrelated_commands(self):
        for gate in ['regular','project','memcheck','racecheck','initcheck','synccheck']:
            with self.assertRaises(ValueError):budget.validate_command(gate,['true'])
    def test_full_unchanged_image_inventory_is_required(self):
        from benchmark_lp_refine import image_inventory
        names=list(image_inventory(ROOT/'target/native/cuda')) if (ROOT/'target/native/cuda/lp_pdhg_refine.cubin').exists() else ['schedule_eval.cubin','lp_pdhg.cubin','lp_pdhg_atomic.cubin','lp_pdhg_research.cubin','lp_pdhg_tuned.cubin','lp_pdhg_precision.cubin','lp_pdhg_exec.cubin','lp_pdhg_refine.cubin','lp_pdhg_refine.build.json','lp_pdhg_refine.compile.stdout','lp_pdhg_refine.compile.stderr']
        with tempfile.TemporaryDirectory() as d:
            d=Path(d)
            for name in names:(d/name).write_bytes(b'fixture')
            self.assertEqual(set(study.image_inventory(d)),set(names))
            (d/'schedule_eval.cubin').unlink()
            with self.assertRaises(FileNotFoundError):study.image_inventory(d)
if __name__=='__main__':unittest.main()
