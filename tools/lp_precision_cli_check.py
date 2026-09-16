"""Leased GPUP-5 CLI evidence/replay and explicit HiGHS fallback acceptance."""
import os,shutil,subprocess,tempfile
from pathlib import Path
from lp_protocol import ROOT,read_json,write_json
from validate_artifacts import validator

def call(args,env=None):
    r=subprocess.run([str(ROOT/'target/release/optimizer'),*map(str,args)],capture_output=True,text=True,env=env,timeout=15)
    if r.returncode not in (0,1,2):raise ValueError(r.stderr)
    return r

def main():
    if os.environ.get('AI_OPTIMIZER_GPU_LEASE')!='inherited':raise ValueError('shared host lease required')
    directory=Path(tempfile.mkdtemp(prefix='cli-',dir=ROOT/'artifacts/gpup5-acceptance'))
    model=ROOT/'examples/lp-model-v1.json';config=ROOT/'examples/solve-config-v1.json';device=os.environ['CUDA_VISIBLE_DEVICES']
    value=read_json(ROOT/'benchmarks/configs/lp-precision-v4.json');lp=value['lp_settings'].copy();lp['iteration_limit']=1000;write_json(directory/'method.json',lp)
    for c in value['configurations']:
        if 'precision' not in c:continue
        precision=directory/(c['id']+'.settings.json');write_json(precision,c['precision']);endpoint=directory/(c['id']+'.json');replay=directory/(c['id']+'.replay.json')
        args=['solve','--model',model,'--config',config,'--backend','cuda-lp-tuned','--device',device,'--lp-settings',directory/'method.json','--lp-execution',ROOT/'examples/lp-precision-execution-v1.json','--lp-precision',precision,'--lp-evidence',endpoint]
        result=call(args)
        if not endpoint.exists():raise ValueError(result.stderr)
        original=read_json(endpoint);validator('lp-endpoint-v4.schema.json').validate(original)
        if original['record']['backend']!='cuda-lp-tuned':raise ValueError('unexpected fallback')
        verified=call(['lp-study','verify','--model',model,'--evidence',endpoint]);assert verified.returncode==0,verified.stderr
        repeated=call(['lp-study','replay','--model',model,'--evidence',endpoint,'--output',replay,'--device',device]);assert replay.exists(),repeated.stderr
        restored=read_json(replay)
        for key in ['assessment','precision','control','execution']:assert original[key]==restored[key],(c['id'],key)
        for key in ['candidate','best_bound','gap','termination','lp_settings','lp_execution','lp_precision']:assert original['record'].get(key)==restored['record'].get(key),(c['id'],key)
    # Missing precision object is an availability failure, with complete request metadata.
    with tempfile.TemporaryDirectory() as tmp:
        tmp=Path(tmp);shutil.copy2(ROOT/'target/native/cuda/schedule_eval.cubin',tmp/'schedule_eval.cubin')
        env=dict(os.environ,AI_OPTIMIZER_CUDA_DIR=str(tmp));endpoint=directory/'missing-code-fallback.json'
        args[-1]=endpoint;result=call(args,env)
        assert endpoint.exists(),result.stderr
        fallback=read_json(endpoint);validator('lp-endpoint-v4.schema.json').validate(fallback)
        assert fallback['record']['backend']=='highs';assert fallback['record']['schema_version']==2
        assert fallback['fallback_reason'];assert fallback['precision']['proposed_steps']==0
        assert fallback['precision']['settings']==read_json(precision)
        verified=call(['lp-study','verify','--model',model,'--evidence',endpoint]);assert verified.returncode==0,verified.stderr
    print('Six precision CLI/replay pairs and pinned HiGHS fallback passed')
if __name__=='__main__':main()
