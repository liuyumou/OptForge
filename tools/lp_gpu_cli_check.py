"""Small CLI device evidence/fallback acceptance; requires the shared host lease."""
import os
from pathlib import Path
import subprocess
import tempfile
from lp_protocol import ROOT, file_hash, read_json, validate, write_json
from validate_artifacts import validator

def main():
    if os.environ.get('AI_OPTIMIZER_GPU_LEASE')!='inherited':raise SystemExit('inherited host lease required')
    device=os.environ['CUDA_VISIBLE_DEVICES']
    binary=ROOT/'target/release/optimizer'
    with tempfile.TemporaryDirectory() as tmp:
        tmp=Path(tmp);settings=read_json(ROOT/'examples/lp-settings-v1.json');settings['iteration_limit']=201
        write_json(tmp/'settings.json',settings)
        for backend,fallback in [(b,f) for b in ['cuda-lp','cuda-lp-matched','cuda-lp-tuned'] for f in [False,True]]:
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
            if backend=='cuda-lp-tuned':args+=['--lp-execution',str(ROOT/'examples/lp-execution-v1.json')]
            run=subprocess.run(args,env=env,capture_output=True,timeout=30)
            assert run.returncode in (0,1),run.stderr
            endpoint=validate('endpoint',read_json(evidence))
            assert endpoint['requested_backend']==backend
            assert endpoint['schema_version']==(3 if backend=='cuda-lp-tuned' else 2 if backend=='cuda-lp-matched' else 1)
            assert endpoint['record']['backend']==('highs' if fallback else backend)
            assert (endpoint['fallback_reason'] is not None)==fallback
            verify=subprocess.run([str(binary),'lp-study','verify','--model',str(ROOT/'examples/lp-model-v1.json'),'--evidence',str(evidence)],capture_output=True,timeout=15)
            assert verify.returncode==0,verify.stderr
            if backend in ['cuda-lp-matched','cuda-lp-tuned'] and not fallback:
                replayed=tmp/(backend+'-replay.json')
                replay=subprocess.run([str(binary),'lp-study','replay','--model',str(ROOT/'examples/lp-model-v1.json'),
                    '--evidence',str(evidence),'--output',str(replayed),'--device',device],capture_output=True,timeout=30)
                assert replay.returncode in (0,1),replay.stderr
                fresh=validate('endpoint',read_json(replayed))
                assert fresh['record']['candidate']==endpoint['record']['candidate']
                assert fresh['diagnostics']['dual']==endpoint['diagnostics']['dual']
                if backend=='cuda-lp-tuned':
                    assert fresh['execution']['settings']==endpoint['execution']['settings']
                    assert fresh['execution']['code_object_sha256']==endpoint['execution']['code_object_sha256']
                    changed=tmp/'changed-code';changed.mkdir()
                    source=Path(os.environ.get('AI_OPTIMIZER_CUDA_DIR',ROOT/'target/native/cuda'))
                    (changed/'lp_pdhg_tuned.cubin').write_bytes((source/'lp_pdhg_tuned.cubin').read_bytes()+b'changed')
                    reject=subprocess.run([str(binary),'lp-study','replay','--model',str(ROOT/'examples/lp-model-v1.json'),
                        '--evidence',str(evidence),'--output',str(tmp/'rejected.json'),'--device',device],
                        env={**os.environ,'AI_OPTIMIZER_CUDA_DIR':str(changed)},capture_output=True,timeout=15)
                    assert reject.returncode==2,reject.stderr
                    assert b'code object' in reject.stderr,reject.stderr
                    assert not (tmp/'rejected.json').exists()
        # SPEC-0014 acceptance row 32-35: solve-batch, per-solve verification,
        # materialize and verify-batch through the CLI. The committed example
        # batch is two identical repeats of lp-model-v1.json under the shared
        # 201-iteration settings, so both per-solve records must agree bit for
        # bit (requirement 15 applies to one materialized model).
        batch_dir=tmp/'batch'
        run=subprocess.run([str(binary),'solve-batch','--model',str(ROOT/'examples/lp-model-v1.json'),
            '--batch',str(ROOT/'examples/lp-batch-request-v1.json'),'--config',str(ROOT/'examples/solve-config-v1.json'),
            '--lp-settings',str(tmp/'settings.json'),'--lp-execution',str(ROOT/'examples/lp-execution-v1.json'),
            '--device',device,'--lp-evidence',str(batch_dir),'--lp-profile','true'],capture_output=True,timeout=60)
        assert run.returncode in (0,1),run.stderr
        batch=read_json(batch_dir/'batch.json')
        validator('lp-batch-endpoint-v1.schema.json').validate(batch)
        assert batch['requested_backend']=='cuda-lp-tuned' and len(batch['solves'])==2
        assert [solve['index'] for solve in batch['solves']]==[0,1]
        verify=subprocess.run([str(binary),'lp-study','verify-batch','--model',str(ROOT/'examples/lp-model-v1.json'),
            '--batch',str(ROOT/'examples/lp-batch-request-v1.json'),'--evidence',str(batch_dir)],capture_output=True,timeout=30)
        assert verify.returncode==0,verify.stderr
        solves=[]
        for index in range(2):
            # A per-solve record binds the materialized bytes (requirement 16),
            # which for a repeat batch are the base model's canonical bytes —
            # not necessarily the input file's bytes. Verification uses the
            # materialize command's output, exactly as verify-batch does.
            materialized=tmp/('materialized-%d.json'%index)
            shown=subprocess.run([str(binary),'lp-study','materialize','--model',str(ROOT/'examples/lp-model-v1.json'),
                '--batch',str(ROOT/'examples/lp-batch-request-v1.json'),'--index',str(index),'--out',str(materialized)],capture_output=True,text=True,timeout=15)
            assert shown.returncode==0,shown.stderr
            assert shown.stdout.strip()==file_hash(materialized)
            assert batch['solves'][index]['model_sha256']==shown.stdout.strip()
            per=validate('endpoint',read_json(batch_dir/('solve-%03d.json'%index)))
            assert per['requested_backend']=='cuda-lp-tuned' and per['fallback_reason'] is None
            assert batch['solves'][index]['status']==per['assessment']['classification']
            single=subprocess.run([str(binary),'lp-study','verify','--model',str(materialized),
                '--evidence',str(batch_dir/('solve-%03d.json'%index))],capture_output=True,timeout=15)
            assert single.returncode==0,single.stderr
            solves.append(per)
        assert solves[1]['record']['candidate']==solves[0]['record']['candidate']
        assert solves[1]['diagnostics']['dual']==solves[0]['diagnostics']['dual']
        assert solves[1]['control']==solves[0]['control']
    print('CLI GPU endpoint, batch and pinned fallback independently verified')
if __name__=='__main__':main()
