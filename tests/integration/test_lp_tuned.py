"""GPUP-4 strict execution, numerical fixtures, compatibility and study limits."""
import copy,json,subprocess,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools'))
from benchmark_lp_tuned import protocol,CONFIG,CORRECTION,require_executable,require_prior_history
from benchmark_lp import schedule,run_trial,provenance
from lp_protocol import Ledger,NS,read_json,write_json,file_hash,validate
from validate_artifacts import validator
from lp_warp_oracle import build,FIXTURE
from report_lp_tuned import analyze,complete_evidence

class TunedTests(unittest.TestCase):
    def test_frozen_protocol_and_exact_allowance(self):
        value,base,manifests=protocol(materialized=False);jobs=list(schedule(value,manifests))
        self.assertEqual(len(jobs),320);self.assertEqual(sum(j[2]['backend']!='host-lp' for j in jobs),280)
        self.assertEqual(len({j[0] for j in jobs}),320)
        self.assertEqual(value['prior_gpu_ns'],445988045904)
        self.assertEqual(value['cumulative_gpu_ns'],1345988045904)
        for key in ['prior_gpu_ns','additional_gpu_seconds','cumulative_gpu_ns','order_seed']:
            wrong=copy.deepcopy(value);wrong[key]+=1
            with self.assertRaises(Exception):validate('campaign',wrong)
        with tempfile.TemporaryDirectory() as tmp:
            directory=Path(tmp)
            with Ledger(directory,value['budget_authority']['sha256']) as ledger:
                reservation=ledger.reserve('prior',446);ledger.settle(reservation,value['prior_gpu_ns'])
                prefix=ledger.path.read_bytes()
            with Ledger(directory,value['budget_authority']['sha256'],cumulative_ns=value['cumulative_gpu_ns']) as ledger:
                r=ledger.reserve('new',899);ledger.settle(r,899*NS)
                with self.assertRaisesRegex(ValueError,'exhausted'):ledger.reserve('over',2)
                self.assertTrue(ledger.path.read_bytes().startswith(prefix))
                ledger.reserve('crash',1)
            with Ledger(directory,value['budget_authority']['sha256'],cumulative_ns=value['cumulative_gpu_ns']) as ledger:
                self.assertFalse(ledger.pending());self.assertEqual(ledger.totals(),value['cumulative_gpu_ns'])
                with self.assertRaisesRegex(ValueError,'exhausted'):ledger.reserve('one-more',0.000000001)

    def test_correction_preserves_protocol_and_preflights_executable_permission(self):
        original,_,_=protocol(materialized=False)
        corrected,_,_=protocol(CORRECTION,materialized=False)
        self.assertEqual({**corrected,'id':original['id']},original)
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'archived-executable';path.write_bytes(b'archived bytes')
            path.chmod(0o644)
            with self.assertRaisesRegex(ValueError,'not executable'):require_executable(path)
            path.chmod(0o755);require_executable(path)
            self.assertEqual(path.read_bytes(),b'archived bytes')
            path.write_bytes(b'previous history\nnew events\n')
            import hashlib
            with patch('benchmark_lp_tuned.PRIOR_EVENTS',1), patch('benchmark_lp_tuned.PRIOR_LEDGER_SHA256',hashlib.sha256(b'previous history\n').hexdigest()):
                require_prior_history(path)
                path.write_bytes(b'altered history\nnew events\n')
                with self.assertRaisesRegex(ValueError,'history differs'):require_prior_history(path)


    def test_settings_are_explicit_and_numerical_fixtures_independent(self):
        settings=read_json(ROOT/'examples/lp-execution-v1.json');validator('lp-execution-v1.schema.json').validate(settings)
        for key in settings:
            missing=dict(settings);del missing[key]
            with self.assertRaises(Exception):validator('lp-execution-v1.schema.json').validate(missing)
        invalid=[{**settings,'schema_version':2},{**settings,'extra':1},{**settings,'allocation':'per_check'},list(settings.values()),{**settings,'reduction':'atomic'}]
        for value in invalid:
            with self.assertRaises(Exception):validator('lp-execution-v1.schema.json').validate(value)
        self.assertEqual(read_json(FIXTURE),build())

    def test_legacy_schema_bytes_unchanged(self):
        for pattern in ['lp-*-v1.schema.json','lp-*-v2.schema.json','solve-record-v2.schema.json']:
            for path in (ROOT/'schemas').glob(pattern):
                # Schemas introduced after that commit are additions, not legacy changes.
                if path.name in ('lp-execution-v1.schema.json','lp-precision-v1.schema.json','lp-external-witness-v1.schema.json','lp-external-endpoint-v1.schema.json','lp-manifest-v2.schema.json'):continue
                archived=subprocess.check_output(['git','show','722e0b0:schemas/'+path.name],cwd=ROOT)
                self.assertEqual(path.read_bytes(),archived,path.name)

    def test_tuned_admission_uses_gpu_wrapper_and_separate_code_identity(self):
        value,base,manifests=protocol(materialized=False)
        job=next(j for j in schedule(value,manifests) if j[2]['id']=='tuned-fused-warp32')
        with tempfile.TemporaryDirectory() as tmp:
            directory=Path(tmp);write_json(directory/'solve.json',value['solve']);write_json(directory/'lp-settings.json',value['lp_settings'])
            code=ROOT/'target/native/cuda'
            class Worker:
                returncode=1
                def wait(self,**kwargs):return 1
            base=provenance(ROOT/'target/debug/optimizer',value['device'])
            with Ledger(directory/'budget',value['budget_authority']['sha256']) as ledger, \
                    patch('benchmark_lp.quiet_device',return_value={'elapsed_ns':0,'reason':'quiet'}), \
                    patch('benchmark_lp.telemetry',return_value='mock telemetry'), \
                    patch('benchmark_lp.subprocess.Popen',return_value=Worker()) as launch:
                with self.assertRaisesRegex(ValueError,'uncertain/overrun'):
                    run_trial(value,*job,ROOT/'target/debug/optimizer',directory,ledger,base,file_hash(CONFIG),code_directory=code)
                trial=read_json(directory/(job[0]+'.trial.json'))
                args=launch.call_args.args[0]
                self.assertEqual(args[:3],['bash',str(ROOT/'tools/gpu_job.sh'),value['device']])
                self.assertEqual(ledger.totals(),16*NS)
                request=read_json(directory/(job[0]+'.request.json'))
                self.assertEqual(request['command'][:2],['/usr/bin/env','AI_OPTIMIZER_CUDA_DIR='+str(code)])
                self.assertIn('--lp-execution',request['command']);self.assertEqual(request['gpu_admission_seconds'],3)
                self.assertEqual(trial['schema_version'],3)

    def test_tuned_cli_rejects_invalid_settings_before_device_open(self):
        binary=ROOT/'target/debug/optimizer'
        if not binary.is_file():self.skipTest('CLI build required')
        args=[str(binary),'solve','--model',str(ROOT/'examples/lp-model-v1.json'),'--config',str(ROOT/'examples/solve-config-v1.json'),'--backend','cuda-lp-tuned','--device','GPU-not-a-device','--lp-settings',str(ROOT/'examples/lp-settings-v1.json')]
        run=subprocess.run(args,capture_output=True,text=True,timeout=10)
        self.assertNotEqual(run.returncode,0);self.assertIn('requires --lp-execution',run.stderr)
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'bad.json';write_json(path,{**read_json(ROOT/'examples/lp-execution-v1.json'),'allocation':'per_check'})
            run=subprocess.run(args+['--lp-execution',str(path)],capture_output=True,text=True,timeout=10)
            self.assertNotEqual(run.returncode,0);self.assertIn('upload/allocation',run.stderr)

    def test_failures_remain_in_coverage(self):
        value,_,_=protocol(materialized=False)
        trial={'instance_id':'fixture','config_id':'tuned-fused-warp32','mode':'timing','repetition':0,'status':'timeout','endpoint_class':'timeout','elapsed_ns':10*NS,'requested_backend':'cuda-lp-tuned','executed_backend':'cuda-lp-tuned'}
        rows,_=analyze([trial],value,[{'id':'fixture'}]);row=next(r for r in rows if r['configuration']=='tuned-fused-warp32')
        self.assertEqual((row['certified'],row['attempted'],row['censored_timeouts']),(0,1,1))
        self.assertIsNone(row['certified_median_ns']);self.assertFalse(complete_evidence([trial],320))
        with self.assertRaises(ValueError):analyze([trial,trial],value,[{'id':'fixture'}])
if __name__=='__main__':unittest.main()
