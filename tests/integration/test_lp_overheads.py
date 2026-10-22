"""Independent fixtures for immutable schemas and bounded GPU admission."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'tools'))
from validate_artifacts import SchemaSnapshot, read_json_bytes, validator
from lp_activity import ActivityPause, sample, wait_quiet

GPU = 'GPU-dfb2449a-9eff-e868-3597-2c448c9a8e48'

class SchemaReuseTests(unittest.TestCase):
    def test_snapshot_checks_once_reuses_references_and_requires_explicit_refresh(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            definition = {'$schema':'https://json-schema.org/draft/2020-12/schema',
                '$id':'number.schema.json','type':'integer'}
            outer = {'$schema':definition['$schema'], '$id':'outer.schema.json',
                'type':'object','additionalProperties':False,
                'properties':{'value':{'$ref':'number.schema.json'}},'required':['value']}
            (root/'number.schema.json').write_text(json.dumps(definition))
            (root/'outer.schema.json').write_text(json.dumps(outer))
            from jsonschema import Draft202012Validator
            with patch.object(Draft202012Validator, 'check_schema', wraps=Draft202012Validator.check_schema) as checks:
                snapshot = SchemaSnapshot(root)
                check = snapshot.validator('outer.schema.json')
                for _ in range(10):
                    self.assertIs(check, snapshot.validator('outer.schema.json'))
                    check.validate({'value':1})
                self.assertEqual(checks.call_count, 2)
            for invalid in [{'value':1,'extra':0}, {'value':'1'}, {}]:
                with self.assertRaises(Exception): check.validate(invalid)
            definition['type']='string'
            (root/'number.schema.json').write_text(json.dumps(definition))
            check.validate({'value':1})
            fresh = SchemaSnapshot(root)
            self.assertNotEqual(snapshot.sha256, fresh.sha256)
            with self.assertRaises(Exception): fresh.validator('outer.schema.json').validate({'value':1})
            fresh.validator('outer.schema.json').validate({'value':'1'})

    def test_duplicate_and_nonfinite_schema_bytes_are_rejected(self):
        for raw in [b'{"type":"number","type":"string"}',b'{"minimum":NaN}',b'{"minimum":1e400}']:
            with tempfile.TemporaryDirectory() as tmp:
                (Path(tmp)/'bad.schema.json').write_bytes(raw)
                with self.assertRaises(ValueError):SchemaSnapshot(tmp)
        self.assertIs(validator('lp-ledger-v1.schema.json'), validator('lp-ledger-v1.schema.json'))

class ActivityTests(unittest.TestCase):
    def run_clock(self, samples, seconds=1, cancelled=lambda:False):
        clock=[0]; observed=[]
        def sleep(duration):clock[0]+=round(duration*1e9)
        def probe(device, timeout):
            observed.append(timeout)
            current=samples[min(len(observed)-1,len(samples)-1)]
            if isinstance(current,Exception):raise current
            return current
        return wait_quiet(GPU, seconds, cancelled, probe=probe, clock=lambda:clock[0], sleep=sleep)

    def test_recent_utilization_waits_for_zero_without_attribution(self):
        report=self.run_clock([{'utilization':1,'pids':[]},{'utilization':0,'pids':[]}])
        self.assertEqual(report['reason'],'quiet');self.assertEqual(report['elapsed_ns'],250_000_000)
        self.assertEqual(report['samples'],2)

    def test_process_blocks_even_with_zero_utilization_and_clock_boundary_is_exact(self):
        with self.assertRaises(ActivityPause) as caught:
            self.run_clock([{'utilization':0,'pids':[17]}])
        self.assertEqual(caught.exception.report['elapsed_ns'],1_000_000_000)
        self.assertEqual(caught.exception.report['samples'],4)
        self.assertEqual(caught.exception.report['reason'],'activity_timeout')

    def test_cancel_and_missing_telemetry_pause_without_launch(self):
        with self.assertRaises(ActivityPause) as caught:self.run_clock([],cancelled=lambda:True)
        self.assertEqual(caught.exception.report['samples'],0)
        with self.assertRaises(ActivityPause) as caught:self.run_clock([ValueError('unavailable')])
        self.assertIn('telemetry_unavailable',caught.exception.report['reason'])

    def test_strict_telemetry_and_other_device_process(self):
        from types import SimpleNamespace
        for utilization,apps,valid in [('0','',True),('0','GPU-abcd, 123',True),
                ('N/A','',False),('101','',False),('0','unavailable',False),('0',GPU+', 0',False)]:
            with patch('lp_activity.subprocess.run',side_effect=[SimpleNamespace(stdout=utilization),SimpleNamespace(stdout=apps)]):
                if valid:self.assertEqual(sample(GPU,1)['pids'],[])
                else:
                    with self.assertRaises(ValueError):sample(GPU,1)

    def test_both_telemetry_queries_are_scoped_to_the_selected_device(self):
        from types import SimpleNamespace
        commands=[]
        def query(command,**kwargs):
            commands.append(command)
            if '--id='+GPU not in command:
                return SimpleNamespace(stdout='GPU-abcd, [N/A]')
            return SimpleNamespace(stdout='0' if '--query-gpu=utilization.gpu' in command else '')
        with patch('lp_activity.subprocess.run',side_effect=query):
            self.assertEqual(sample(GPU,1),{'utilization':0,'pids':[]})
        self.assertEqual(len(commands),2)
        self.assertTrue(all('--id='+GPU in c for c in commands))
        with patch('lp_activity.subprocess.run',side_effect=[SimpleNamespace(stdout='0'),SimpleNamespace(stdout=GPU+', [N/A]')]):
            with self.assertRaises(ValueError):sample(GPU,1)

    def test_leased_activity_race_retains_blocked_attempt_without_child(self):
        import lp_supervise
        with tempfile.TemporaryDirectory() as tmp:
            request=dict(schema_version=2,gpu_admission_seconds=3,command=['unused'],directory=tmp,
                prefix='blocked',solve_seconds=10,cleanup_seconds=2,host_rss_bytes=1024,poll_ms=10,output_bytes=1024)
            pause=ActivityPause({'reason':'activity_timeout','elapsed_ns':3_000_000_000})
            with patch.dict('os.environ',{'AI_OPTIMIZER_GPU_LOCK':str(Path(tmp)/'lock')}), \
                 patch('lp_activity.wait_quiet',side_effect=pause), \
                 patch('lp_supervise.subprocess.Popen') as launch:
                result=lp_supervise.supervise(request,GPU)
            launch.assert_not_called()
            self.assertEqual(result['reason'],'activity_blocked')
            self.assertGreater(result['leased_ns'],0)
            self.assertEqual(result['elapsed_ns'],0)
            self.assertTrue((Path(tmp)/'blocked.worker.json').is_file())

if __name__=='__main__':unittest.main()
