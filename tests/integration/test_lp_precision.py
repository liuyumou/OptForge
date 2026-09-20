"""GPUP-5 strict contracts, frozen scope and independent external authority."""
import copy,json,subprocess,sys,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'tools'))
from benchmark_lp_precision import protocol,CONFIG,require_prior_history
from benchmark_lp import schedule
from lp_protocol import read_json,write_json,file_hash
from validate_artifacts import validator
from lp_copt import parameters,gpu_started,validate_import_coefficients
class PrecisionTests(unittest.TestCase):
    def test_copt_preserves_supported_input_coefficients(self):
        manifest=read_json(ROOT/'benchmarks/manifests/lp-development-v1.json')
        for instance in manifest['instances']:
            validate_import_coefficients(read_json(ROOT/instance['model']['path']))
        model=read_json(ROOT/'examples/lp-model-v1.json')
        for coefficient in [1e-10,-1e-10,1e-11,-1e-11,float('inf'),float('nan')]:
            model['constraints'][0]['terms'][0]['coefficient']=coefficient
            with self.assertRaises(ValueError):validate_import_coefficients(model)

    def test_copt_gpu_confirmation_requires_execution_not_discovery(self):
        self.assertFalse(gpu_started('Hardware has 1 supported GPU device'))
        self.assertTrue(gpu_started('Starting PDLP solver using GPU 0'))
        self.assertTrue(gpu_started('Starting PDLP solver on GPU 0'))
        self.assertFalse(gpu_started('Starting PDLP solver using GPU 1'))
    def test_frozen_grid_and_exact_carry_forward(self):
        value,base,manifests=protocol(materialized=False);jobs=list(schedule(value,manifests))
        self.assertEqual(len(jobs),480);self.assertEqual(value['prior_gpu_ns'],902574545061)
        self.assertEqual(value['cumulative_gpu_ns'],4502574545061)
        self.assertEqual(value['solve'],base['solve']);self.assertEqual(len(value['configurations']),12)
        for config in value['configurations']:
            if 'precision' in config:validator('lp-precision-v1.schema.json').validate(config['precision'])
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'ledger';path.write_text('{}\n')
            with self.assertRaises(ValueError):require_prior_history(path)
    def test_precision_schema_requires_every_field_and_supported_combinations(self):
        s=read_json(ROOT/'examples/lp-storage-fp32-v1.json');v=validator('lp-precision-v1.schema.json')
        for key in s:
            wrong=dict(s);del wrong[key]
            with self.assertRaises(Exception):v.validate(wrong)
        for wrong in [{**s,'extra':1},{**s,'products':'f32'},{**s,'schema_version':2},{**s,'rounding':'stochastic'},{**s,'working_state':'f32'}]:
            with self.assertRaises(Exception):v.validate(wrong)
    def test_cli_refuses_precision_on_other_backends_before_device_open(self):
        binary=ROOT/'target/debug/optimizer'
        for backend in ['highs','host-lp','cuda-lp','cuda-lp-matched']:
            result=subprocess.run([str(binary),'solve','--model',str(ROOT/'examples/lp-model-v1.json'),'--config',str(ROOT/'examples/solve-config-v1.json'),'--backend',backend,'--lp-precision',str(ROOT/'examples/lp-storage-fp32-v1.json')],capture_output=True,text=True)
            self.assertNotEqual(result.returncode,0);self.assertIn('requires cuda-lp-tuned',result.stderr)
    def test_external_original_model_and_dual_signs(self):
        binary=ROOT/'target/debug/optimizer';original=read_json(ROOT/'examples/lp-model-v1.json');options=read_json(ROOT/'examples/solve-config-v1.json')
        with tempfile.TemporaryDirectory() as tmp:
            d=Path(tmp)
            for maximize in [False,True]:
                model=copy.deepcopy(original);model['constraints'][0]['lower']={'kind':'finite','value':0.5};model['objective']['offset']=7.0
                if maximize:
                    model['objective']['sense']='maximize'
                    for t in model['objective']['terms']:t['coefficient']=-t['coefficient']
                path=d/'model.json';write_json(path,model)
                witness=dict(schema_version=1,model_sha256=file_hash(path),requested_backend='copt-cpu-pdlp',executed_backend='copt-cpu-pdlp',options=options,copt_version='8.0.6',parameters=parameters(options,False),library_sha256='a'*64,binding_sha256='b'*64,gpu_confirmed=False,row_ids=[0],variable_ids=[0,1],primal=[0.5,1.0],dual=[-1.0],status='optimal',iterations=10,limitations=['fixture'])
                wp=d/'witness.json';out=d/f'endpoint-{maximize}.json';write_json(wp,witness)
                result=subprocess.run([str(binary),'lp-study','external-certify','--model',str(path),'--evidence',str(wp),'--output',str(out)],capture_output=True,text=True)
                self.assertEqual(result.returncode,0,result.stderr);endpoint=read_json(out);self.assertEqual(endpoint['assessment']['classification'],'certified_success')
                validator('lp-external-endpoint-v1.schema.json').validate(endpoint)
                endpoint['witness']['primal'][0]=0.75;write_json(out,endpoint)
                rejected=subprocess.run([str(binary),'lp-study','external-verify','--model',str(path),'--evidence',str(out)],capture_output=True,text=True)
                self.assertNotEqual(rejected.returncode,0)
                witness['executed_backend']='copt-gpu-pdlp';write_json(wp,witness)
                rejected=subprocess.run([str(binary),'lp-study','external-certify','--model',str(path),'--evidence',str(wp),'--output',str(d/'forged.json')],capture_output=True,text=True)
                self.assertNotEqual(rejected.returncode,0)
