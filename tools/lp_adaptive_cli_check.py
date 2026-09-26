"""Leased v5 CLI, independent verification, replay and explicit availability fallback."""
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from lp_protocol import ROOT,read_json,write_json
from validate_artifacts import validator


def call(args,env=None):
    result=subprocess.run([str(ROOT/'target/release/optimizer'),*map(str,args)],capture_output=True,text=True,env=env,timeout=20)
    if result.returncode not in (0,1,2):raise ValueError(result.stderr)
    return result


def main():
    if os.environ.get('AI_OPTIMIZER_GPU_LEASE')!='inherited':raise ValueError('shared host lease required')
    directory=Path(tempfile.mkdtemp(prefix='cli-',dir=ROOT/'artifacts/gpup6-acceptance'))
    model=ROOT/'examples/lp-model-v1.json';device=os.environ['CUDA_VISIBLE_DEVICES']
    v=read_json(ROOT/'benchmarks/configs/lp-adaptive-v1.json');method=dict(v['lp_settings'],iteration_limit=64,check_interval=16)
    options=dict(v['solve'],iteration_limit=64);write_json(directory/'method.json',method);write_json(directory/'solve.json',options)
    configurations=[c for c in v['configurations'] if c['id'] in ['adaptive-fp64-a1','adaptive-direct-working_fp32-a32-strict-sticky','adaptive-gradual-working_fp32-a32-strict-demote','adaptive-direct-storage_fp32-a8-strict-demote']]
    for c in configurations:
        policy=directory/(c['id']+'.policy.json');write_json(policy,c['adaptive'])
        endpoint=directory/(c['id']+'.json');replay=directory/(c['id']+'.replay.json')
        args=['solve','--model',model,'--config',directory/'solve.json','--backend','cuda-lp-tuned','--device',device,'--lp-settings',directory/'method.json','--lp-execution',ROOT/'examples/lp-precision-execution-v1.json','--lp-adaptive',policy,'--lp-evidence',endpoint]
        result=call(args)
        if not endpoint.exists():raise ValueError(result.stderr)
        original=read_json(endpoint);validator('lp-endpoint-v5.schema.json').validate(original)
        if original['record']['backend']!='cuda-lp-tuned':raise ValueError('unexpected fallback')
        verified=call(['lp-study','verify','--model',model,'--evidence',endpoint]);assert verified.returncode==0,verified.stderr
        repeated=call(['lp-study','replay','--model',model,'--evidence',endpoint,'--output',replay,'--device',device]);assert replay.exists(),repeated.stderr
        restored=read_json(replay)
        for key in ['assessment','adaptive','control','execution']:assert original[key]==restored[key],(c['id'],key)
        for key in ['candidate','best_bound','gap','termination','lp_settings','lp_execution','lp_adaptive']:assert original['record'].get(key)==restored['record'].get(key),(c['id'],key)
    with tempfile.TemporaryDirectory() as tmp:
        tmp=Path(tmp);shutil.copy2(ROOT/'target/native/cuda/schedule_eval.cubin',tmp/'schedule_eval.cubin')
        env=dict(os.environ,AI_OPTIMIZER_CUDA_DIR=str(tmp));args[-1]=directory/'fallback.json';result=call(args,env)
        assert args[-1].exists(),result.stderr
        fallback=read_json(args[-1]);validator('lp-endpoint-v5.schema.json').validate(fallback)
        assert fallback['record']['backend']=='highs' and fallback['record']['schema_version']==2
        assert fallback['fallback_reason'] and fallback['adaptive']['proposed_steps']==0
        assert fallback['adaptive']['settings']==read_json(policy)
        verified=call(['lp-study','verify','--model',model,'--evidence',args[-1]]);assert verified.returncode==0,verified.stderr
    args[-1]=directory/'invalid.json'
    refused=call([*args,'--lp-precision',ROOT/'examples/lp-storage-fp32-v1.json'])
    assert refused.returncode==2 and 'mutually exclusive' in refused.stderr and not args[-1].exists()
    print('Four adaptive CLI/replay pairs, independent v5 verification, pinned fallback and conflicting-option refusal passed')
if __name__=='__main__':main()
