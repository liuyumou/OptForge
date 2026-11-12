"""Fresh CPU process replay of retained serial certificates and pipe lifecycle tests."""
import argparse
import copy
import gzip
import json
import os
from pathlib import Path
import statistics
import subprocess
from lp_delivery2_common import ROOT, BASE, put, ref, load, require

BINARY=ROOT/'research/lp-delivery2/target/release/lp-delivery2'
ARCHIVE=ROOT/'docs/benchmarks/data/fp4-accel-result-v1-endpoints.json.gz'


def numerical_source():
    old=(ROOT/'research/lp-fp4-checker/src/main.rs').read_text()
    new=(ROOT/'research/lp-delivery2/src/main.rs').read_text()
    def body(s):return s[s.index('    fn lane('):s.index('fn main()')]
    require(body(old)==body(new),'numerical orchestration differs')
    return dict(parent=ref(ROOT/'research/lp-fp4-checker/src/main.rs'),candidate=ref(ROOT/'research/lp-delivery2/src/main.rs'),unchanged='lane selection, preparation, solve, command state machine')


def process_cases(model,endpoint):
    cases=[]
    request=dict(endpoint=endpoint,tier='certified-1e-9')
    requests=[]
    for status in ('completed','cancelled','limit','error','refused'):
        value=copy.deepcopy(request);value['endpoint']['transport']=status
        requests.append(value)
    env={**os.environ,'CUDA_VISIBLE_DEVICES':''}
    for baseline in (True,False):
        if baseline:env['GPUP_DELIVERY2_CONTROL']='1'
        else:env.pop('GPUP_DELIVERY2_CONTROL',None)
        p=subprocess.run([str(BINARY),'check-service',str(model)],input=b''.join(json.dumps(v).encode()+b'\n' for v in requests),capture_output=True,timeout=15,env=env)
        require(p.returncode==0,'fresh status requests failed');lines=[json.loads(v) for v in p.stdout.splitlines()]
        require(len(lines)==6 and lines[0]['ready'],'response count')
        require(lines[1]['accepted'] and all(not r['accepted'] for r in lines[2:]),'terminal eligibility changed')
        cases.append(dict(mode=baseline,case='fresh-status-and-EOF',passed=True))
        variants={}
        for field,value in [('model_sha256','wrong'),('primal',[]),('dual',[]),('transport','optimal')]:
            bad=copy.deepcopy(request);bad['endpoint'][field]=value;variants[field]=json.dumps(bad).encode()+b'\n'
        bad=copy.deepcopy(request);bad['tier']='certified-1e-6';variants['tier']=json.dumps(bad).encode()+b'\n'
        variants['duplicate']=b'{"tier":"a","tier":"b","endpoint":null}\n'
        variants['truncated']=json.dumps(request).encode()
        variants['oversize']=b' '*(8*1024*1024)+b'\n'
        for name,payload in variants.items():
            p=subprocess.run([str(BINARY),'check-service',str(model)],input=payload,capture_output=True,timeout=15,env=env)
            require(p.returncode!=0 and len(p.stdout.splitlines())==1,'bad request did not refuse: '+name)
            cases.append(dict(mode=baseline,case=name,passed=True))
        p=subprocess.run([str(BINARY),'check-service',str(model)+'.missing'],capture_output=True,timeout=5,env=env)
        require(p.returncode!=0 and not p.stdout,'bad model became ready')
        cases.append(dict(mode=baseline,case='setup-failure',passed=True))
    return cases


def run(directory,count=5):
    out=Path(directory);out.mkdir(exist_ok=False,parents=True)
    archive=json.loads(gzip.decompress(ARCHIVE.read_bytes()))
    put(out/'manifest.json',dict(binary=ref(BINARY),archive=ref(ARCHIVE),count=count,source=numerical_source(),
        sources=[ref(p) for p in sorted((ROOT/'research/lp-delivery2/src').glob('*.rs'))]))
    rows=[]
    for index,(key,value) in enumerate(archive['endpoints'].items()):
        endpoint=out/(key+'.endpoint.json');put(endpoint,value['endpoint'])
        model=ROOT/archive['manifest']['models'][value['family']]['path']
        require(ref(model)==archive['manifest']['models'][value['family']],'changed model')
        expected={k:v for k,v in value['certificate'].items() if k!='checker_binary_sha256'}
        for baseline in ((True,False) if index%2==0 else (False,True)):
            env={**os.environ,'CUDA_VISIBLE_DEVICES':''}
            if baseline:env['GPUP_DELIVERY2_CONTROL']='1'
            else:env.pop('GPUP_DELIVERY2_CONTROL',None)
            dest=out/(key+('-control' if baseline else '-batched')+'.json')
            subprocess.run([str(BINARY),'transport-profile',str(model),str(endpoint),value['tier'],str(count),str(dest)],check=True,timeout=30,capture_output=True,env=env)
            profile=load(dest)
            require(all({k:v for k,v in r['certificate'].items() if k!='checker_binary_sha256'}==expected for r in profile['rows']),'serial receipt mismatch: '+key)
            require(all(r['certificate']['checker_binary_sha256']==ref(BINARY)['sha256'] for r in profile['rows']),'wrong checker image')
            rows.append(dict(key=key,family=value['family'],tier=value['tier'],baseline=baseline,accepted=expected['accepted'],
                median_ns=statistics.median(r['ns'] for r in profile['rows']),setup_ns=profile['setup_ns'],profile=ref(dest)))
        if (index+1)%20==0:print(dict(endpoints=index+1),flush=True)
    value=next(v for v in archive['endpoints'].values() if v['family']=='coupled-equality' and v['certificate']['accepted'])
    cases=process_cases(ROOT/archive['manifest']['models'][value['family']]['path'],value['endpoint'])
    put(out/'result.json',dict(status='passed',endpoints=len(archive['endpoints']),fresh_assessments=len(rows)*count,rows=rows,process_cases=cases))
    print(dict(endpoints=len(archive['endpoints']),fresh_assessments=len(rows)*count,process_cases=len(cases)),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('directory');p.add_argument('--count',type=int,default=5);a=p.parse_args();run(a.directory,a.count)
