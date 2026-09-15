"""Small CLI device evidence/fallback acceptance; requires the shared host lease."""
import os
from pathlib import Path
import subprocess
import tempfile
from lp_protocol import ROOT, read_json, validate, write_json

def main():
    if os.environ.get('AI_OPTIMIZER_GPU_LEASE')!='inherited':raise SystemExit('inherited host lease required')
    device=os.environ['CUDA_VISIBLE_DEVICES']
    binary=ROOT/'target/release/optimizer'
    with tempfile.TemporaryDirectory() as tmp:
        tmp=Path(tmp);settings=read_json(ROOT/'examples/lp-settings-v1.json');settings['iteration_limit']=201
        write_json(tmp/'settings.json',settings)
        for backend,fallback in [(b,f) for b in ['cuda-lp','cuda-lp-matched'] for f in [False,True]]:
            evidence=tmp/'endpoint.json'
            env=dict(os.environ)
            if fallback:
                # Opening a DeviceSession first needs the existing scheduling
                # object. Isolate LP availability failure after that succeeds.
                missing=tmp/'unprovisioned';missing.mkdir(exist_ok=True)
                source=Path(os.environ.get('AI_OPTIMIZER_CUDA_DIR',ROOT/'target/native/cuda'))
                if not (missing/'schedule_eval.cubin').exists():(missing/'schedule_eval.cubin').symlink_to((source/'schedule_eval.cubin').resolve())
                env['AI_OPTIMIZER_CUDA_DIR']=str(missing)
            args=[str(binary),'solve','--model',str(ROOT/'examples/lp-model-v1.json'),
                '--config',str(ROOT/'examples/solve-config-v1.json'),'--backend',backend,'--device',device,
                '--lp-settings',str(tmp/'settings.json'),'--lp-evidence',str(evidence),'--lp-profile','true']
            run=subprocess.run(args,env=env,capture_output=True,timeout=30)
            assert run.returncode in (0,1),run.stderr
            endpoint=validate('endpoint',read_json(evidence))
            assert endpoint['requested_backend']==backend
            assert endpoint['schema_version']==(2 if backend=='cuda-lp-matched' else 1)
            assert endpoint['record']['backend']==('highs' if fallback else backend)
            assert (endpoint['fallback_reason'] is not None)==fallback
            verify=subprocess.run([str(binary),'lp-study','verify','--model',str(ROOT/'examples/lp-model-v1.json'),'--evidence',str(evidence)],capture_output=True,timeout=15)
            assert verify.returncode==0,verify.stderr
            if backend=='cuda-lp-matched' and not fallback:
                replayed=tmp/'matched-replay.json'
                replay=subprocess.run([str(binary),'lp-study','replay','--model',str(ROOT/'examples/lp-model-v1.json'),
                    '--evidence',str(evidence),'--output',str(replayed),'--device',device],capture_output=True,timeout=30)
                assert replay.returncode in (0,1),replay.stderr
                fresh=validate('endpoint',read_json(replayed))
                assert fresh['record']['candidate']==endpoint['record']['candidate']
                assert fresh['diagnostics']['dual']==endpoint['diagnostics']['dual']
    print('CLI GPU endpoint and pinned fallback independently verified')
if __name__=='__main__':main()
