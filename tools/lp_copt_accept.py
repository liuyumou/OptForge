"""Leased ADR-0026 profile equivalence and real COPT method/certification acceptance."""
import copy
import os
from pathlib import Path
import struct
import subprocess
import tempfile
from lp_copt_budget import protocol
from lp_protocol import ROOT,read_json,write_json,file_hash
from lp_cost import validate_profile
from lp_copt_comparison import METHODS

def equal_bits(a,b):
    if isinstance(a,float) or isinstance(b,float):return isinstance(a,(int,float)) and isinstance(b,(int,float)) and struct.pack('>d',a)==struct.pack('>d',b)
    if isinstance(a,dict):return isinstance(b,dict) and a.keys()==b.keys() and all(equal_bits(a[k],b[k]) for k in a)
    if isinstance(a,list):return isinstance(b,list) and len(a)==len(b) and all(equal_bits(x,y) for x,y in zip(a,b))
    return a==b

def call(args,env=None):
    r=subprocess.run([str(a) for a in args],env=env,capture_output=True,text=True,timeout=35)
    if r.returncode not in (0,1):raise ValueError('acceptance command failed: '+r.stderr[-1800:])
    return r

def main():
    if os.environ.get('AI_OPTIMIZER_GPU_LEASE')!='inherited':raise ValueError('shared host lease required')
    v=protocol();binary=ROOT/'target/release/optimizer';directory=Path(tempfile.mkdtemp(prefix='cli-',dir=ROOT/v['acceptance_output']))
    options=dict(v['solve'],iteration_limit=200,time_limit_ms=30000);method=dict(v['lp_settings'],iteration_limit=200)
    write_json(directory/'solve.json',options);write_json(directory/'method.json',method)
    model=ROOT/'artifacts/lp-inputs-v1/gpup-development-irregular-256.json';results=[]
    for c in [c for c in v['configurations'] if c['id'] in v['short_configurations']]:
        records=[];evidence=[]
        for profile in [False,True]:
            out=directory/(c['id']+('-on' if profile else '-off')+'.json')
            args=[binary,*(['lp-study','solve'] if profile else ['solve']),'--model',model,'--config',directory/'solve.json','--backend',c['backend'],
                  '--device',v['device'],'--lp-settings',directory/'method.json','--lp-evidence',out,'--lp-profile',str(profile).lower()]
            for key in ['execution','precision','adaptive']:
                if key in c:
                    path=directory/(c['id']+'.'+key+'.json');write_json(path,c[key]);args+=['--lp-'+key,path]
            if profile:args+=['--model-byte-limit','134217728','--cost-profile',out.with_suffix('.cost.json')]
            call(args);e=read_json(out)
            if e['record']['backend']!=c['backend']:raise ValueError('unexpected availability fallback')
            call([binary,'lp-study','verify','--model',model,'--evidence',out])
            record=copy.deepcopy(e['record']);del record['elapsed_ms'];records.append(record);evidence.append(e)
            if profile:
                raw=read_json(out.with_suffix('.cost.json'));validate_profile(raw)
                for counter,field in [('device_allocated_bytes','allocated_bytes'),('host_to_device_bytes','upload_bytes'),('device_to_host_bytes','readback_bytes')]:
                    if raw['counters'].get(counter)!=e['execution'][field]:raise ValueError('profile byte counter differs from execution evidence')
        if not equal_bits(records[0],records[1]):raise ValueError('profile changed numerical record: '+c['id'])
        for key in ['control','precision','adaptive']:
            if not equal_bits(evidence[0].get(key),evidence[1].get(key)):raise ValueError('profile changed work/policy state')
        for key in ['dual','iterations','assessment_iteration','restarts']:
            if not equal_bits(evidence[0]['diagnostics'][key],evidence[1]['diagnostics'][key]):raise ValueError('profile changed numerical diagnostics: '+key)
        results.append(dict(config=c['id'],bitwise_equivalent=True))
    write_json(directory/'copt-solve.json',dict(v['solve'],time_limit_ms=30000))
    for maximize in [False,True]:
        data=read_json(model)
        if maximize:
            data['objective']['sense']='maximize';data['objective']['offset']=7.0
            for term in data['objective']['terms']:term['coefficient']=-term['coefficient']
        path=directory/('max-model.json' if maximize else 'min-model.json');write_json(path,data)
        for mode in METHODS:
            out=directory/(mode+('-max' if maximize else '-min')+'.json')
            env={**os.environ,'COPT_HOME':v['copt_installation'],'COPT_LICENSE_DIR':v['copt_installation'],'LD_LIBRARY_PATH':'/usr/local/cuda/lib64'+(':'+os.environ['LD_LIBRARY_PATH'] if os.environ.get('LD_LIBRARY_PATH') else '')}
            if mode!='copt-gpu-pdlp':env['CUDA_VISIBLE_DEVICES']=''
            args=[ROOT/v['copt_python'],'-B',ROOT/'tools/lp_copt_comparison.py','--model',path,'--config',directory/'copt-solve.json','--binary',binary,
                  '--output',out,'--method',mode,'--device',v['device'],'--cost-profile',out.with_suffix('.cost.json')]
            call(args,env);e=read_json(out)
            if e['witness']['executed_backend']!=mode or e['assessment']['classification']!='certified_success':raise ValueError('COPT acceptance was not certified: '+mode+' '+str(e['assessment']))
            call([binary,'lp-study','external-verify','--model',path,'--evidence',out]);validate_profile(read_json(out.with_suffix('.cost.json')))
            results.append(dict(config=mode,maximize=maximize,certified=True,endpoint_sha256=file_hash(out)))
    write_json(directory/'receipt.json',dict(results=results,source_binary_sha256=file_hash(binary)))
    print('six project profiles bitwise equivalent; six COPT min/max method endpoints certified; '+str(directory))
if __name__=='__main__':main()
