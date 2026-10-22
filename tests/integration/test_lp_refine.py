"""ADR-0037 independent algebra, strict interfaces, roster and accounting."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
from jsonschema import ValidationError
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools'))
import lp_refine_oracle as oracle
import lp_refine_budget as budget
import benchmark_lp_refine as study
from lp_copt_budget import ComparisonLedger
from validate_artifacts import validator
class RefineContracts(unittest.TestCase):
    def test_rational_fixture_reproduces(self):
        value=oracle.generate();self.assertEqual(value,json.loads(oracle.FIXTURE.read_text()));self.assertEqual(sum(x['expected']['maps'] for x in value['cases']),1200)
        self.assertEqual({c['model']['objective']['sense'] for c in value['cases']},{'minimize','maximize'})
    def test_frozen_roster_and_reservations(self):
        v=budget.protocol();jobs=list(study.jobs(v));self.assertEqual(len(jobs),108);self.assertEqual(len({j['id'] for j in jobs}),108)
        self.assertEqual({k:sum(study.effective(v,j)[2]+6 for j in jobs if j['kind']==k) for k in ['timing','profile']},{'timing':2256,'profile':432})
        self.assertEqual(v['additional_gpu_seconds'],0);self.assertEqual(v['prior_events'],16454)
        for j in jobs:self.assertEqual(study.effective(v,j)[0]['tolerances'],v['solve']['tolerances'])
    def test_authority_changes_refuse_before_private_ledger(self):
        v=budget.protocol()
        with patch('lp_exec_budget.ledger_for',side_effect=FileNotFoundError) as parent:
            for key,wrong in [('prior_events',0),('cumulative_gpu_ns',28800*10**9),('combined_cap_seconds',3601)]:
                x=copy.deepcopy(v);x[key]=wrong
                with self.assertRaises((ValueError,ValidationError)):budget.ledger_for(x)
            parent.assert_not_called()
    def test_worker_identity_binds_anchor_width_profile_and_limits(self):
        v=budget.protocol();j=next(j for j in study.jobs(v) if j['configuration']['id']=='refine-anchored-fp32' and j['kind']=='profile')
        identity=dict(source_tree_sha256='a'*64,exec_binary_sha256='b'*64,code_object_sha256='c'*64)
        with tempfile.TemporaryDirectory() as d:
            d=Path(d);request=study.write_inputs(v,j,d,identity);study.check_request(v,j,d,identity,request)
            payload=json.loads((d/(j['id']+'.refine-request.json')).read_text());validator('lp-refine-request-v1.schema.json').validate(payload)
            self.assertTrue(payload['anchored']);self.assertEqual(payload['width'],'f32');self.assertEqual(payload['method']['iteration_limit'],200)
            payload['anchored']=False;(d/(j['id']+'.refine-request.json')).write_text(json.dumps(payload))
            with self.assertRaises(ValueError):study.check_request(v,j,d,identity,request)
    def test_ledger_crash_and_phase_limits_are_preserved(self):
        v=budget.protocol()
        with tempfile.TemporaryDirectory() as d:
            with ComparisonLedger(Path(d),'a'*64,v) as ledger:
                ledger.reserve(v['id']+'-accept-simulation',20,phase='repeatability')
                with self.assertRaises(ValueError):ledger.reserve(v['id']+'-profile-invalid',1,phase='screening')
                with self.assertRaises(ValueError):ledger.reserve(v['id']+'-accept-excess',851,phase='repeatability')
            with ComparisonLedger(Path(d),'a'*64,v) as ledger:self.assertEqual(ledger.usage('accept'),20*10**9);self.assertFalse(ledger.pending())
    def test_freeze_includes_unchanged_regular_suite_dependencies(self):
        with tempfile.TemporaryDirectory() as d:
            directory=Path(d)
            required=['schedule_eval.cubin','lp_pdhg.cubin','lp_pdhg_atomic.cubin','lp_pdhg_research.cubin','lp_pdhg_tuned.cubin','lp_pdhg_precision.cubin','lp_pdhg_exec.cubin','lp_pdhg_refine.cubin','lp_pdhg_refine.build.json','lp_pdhg_refine.compile.stdout','lp_pdhg_refine.compile.stderr']
            for name in required:(directory/name).write_bytes(b'fixture')
            self.assertEqual(set(study.image_inventory(directory)),set(required))
            for name in ['schedule_eval.cubin','lp_pdhg_atomic.cubin','lp_pdhg_research.cubin']:
                (directory/name).unlink()
                with self.assertRaises(FileNotFoundError):study.image_inventory(directory)
                (directory/name).write_bytes(b'fixture')
    def test_interrupted_complete_endpoints_keep_their_raw_classification(self):
        from report_lp_refine import check_assessment
        fresh={'classification':'certified_success'}
        check_assessment({'status':'interrupted','assessment':None},fresh)
        with self.assertRaises(ValueError):check_assessment({'status':'completed','assessment':None},fresh)
        check_assessment({'status':'completed','assessment':fresh},fresh)
    def test_report_decodes_compact_controls_before_reading_record(self):
        import report_lp_refine as report
        path=Path('/tmp/refine-endpoint.json');normalized={'record':{'backend':'cuda-lp-tuned'}}
        with patch.object(report,'endpoint_shape',return_value=normalized) as decode,patch.object(report,'read_json',side_effect=AssertionError('raw compact wrapper is not a record')):
            self.assertEqual(report.load_endpoint({'configuration':{'backend':'cuda-lp-tuned'}},path),normalized)
            decode.assert_called_once_with(path,'compact-v1')
        raw={'witness':{'outcome':{}}}
        with patch.object(report,'read_json',return_value=raw):self.assertEqual(report.load_endpoint({'configuration':{'backend':'lp-refine-v1'}},path),raw)
    def test_gate_labels_cannot_admit_unrelated_commands(self):
        for gate in ['regular','oracle','project','memcheck','racecheck','initcheck','synccheck']:
            with self.assertRaises(ValueError):budget.validate_command(gate,['true'])
    def test_request_schema_rejects_unknown_or_missing_fields(self):
        v=budget.protocol();j=next(j for j in study.jobs(v) if j['configuration']['backend']=='lp-refine-v1');identity=dict(source_tree_sha256='a'*64,exec_binary_sha256='b'*64,code_object_sha256='c'*64)
        _,docs=study.prepare_inputs(v,j,Path('/tmp/refine-schema'),identity);payload=docs[j['id']+'.refine-request.json']
        for bad in [{**payload,'unknown':True},{k:x for k,x in payload.items() if k!='anchored'}]:
            with self.assertRaises(ValidationError):validator('lp-refine-request-v1.schema.json').validate(bad)
if __name__=='__main__':unittest.main()
