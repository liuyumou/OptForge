"""CPU preparation and independent original-checker admission for SPEC-0038."""
import argparse
from fractions import Fraction as Q
import gzip
import json
import math
import os
from pathlib import Path
import subprocess
from lp_mixed2_fp4_common import ROOT,BASE,BINARY,load,put,ref,require
from lp_delivery2_study import PARENT,bits


def environment(variant=None,profile=False):
    return {k:v for k,v in os.environ.items() if not k.startswith(('GPUP_DELIVERY','GPUP_CHECKER_','GPUP_MIXED2_'))}


def fixture(a,identity):
    m,n=len(a),len(a[0]);bound=lambda v:dict(kind='finite',value=float(v))
    return dict(schema_version=1,model_id=identity,
        variables=[dict(id=3*j+7,domain='continuous',lower=bound(-1),upper=bound(1)) for j in range(n)],
        constraints=[dict(id=5*i+11,lower=bound(0),upper=bound(0),terms=[dict(variable_id=3*j+7,coefficient=float(a[i][j])) for j in range(n) if a[i][j]!=0]) for i in range(m)],
        objective=dict(sense='minimize',offset=3.25,terms=[]))


def prepare():
    import numpy as np
    out=BASE/'models';out.mkdir(exist_ok=False)
    old=load(PARENT/'manifest.json');models=dict(old['models'])
    for n in (1024,2048):
        i=np.arange(n);a=np.eye(n)+(((13*i[:,None]+7*i[None,:])%37)-18)/(73*n)
        x=(13*i%37)/37-.5;y=(7*i%29)/29-.5;c=a.T@y;rhs=a@x
        doc=fixture(a,f'mixed2-fp4-dense-generic-{n}')
        for row,v in zip(doc['constraints'],rhs): row['lower']['value']=row['upper']['value']=float(v)
        doc['objective']['terms']=[dict(variable_id=3*j+7,coefficient=float(c[j])) for j in range(n) if c[j]!=0]
        p=out/f'dense-generic-{n}.json'
        with p.open('x') as f:json.dump(doc,f,separators=(',',':'),allow_nan=False)
        models[f'dense-generic-{n}']=ref(p)
        del doc,a
        print(dict(prepared=n),flush=True)
    codes=[0,1,1.5,2,3,4,6,-1,-1.5,-2,-3,-4,-6]
    cases={
        'normal-code-pairs':[[codes[(i+j)%13]/64 for j in range(32)] for i in range(32)],
        'rectangular-cancellation':[[(-1)**(i+j)*(.1+(i*7+j*13)%19/37) for j in range(33)] for i in range(3)],
        'scale-range':[[math.ldexp((i*7+j*13)%37/37-.5,(i+j)%33-16) for j in range(32)] for i in range(32)],
    }
    tests={}
    for name,a in cases.items():p=out/(name+'.json');put(p,fixture(a,'mixed2-'+name));tests[name]=ref(p)
    put(out/'manifest.json',dict(models=models,tests=tests,parent=ref(PARENT/'manifest.json'),generator=ref(Path(__file__)),settings=old['settings']))


def guard_norms(d):
    p=d['p'];b=p//32;outputs=0
    for key,pack in d['packs'].items():
        k=int(key); sums=[[Q(0)]*(6*p)][0]
        for i in range(p):
            for j in range(p):
                tile=(i//32)*b+j//32;offset=(i%32)*32+j%32
                parts=[]
                for h in range(k):
                    code=(pack['codes'][tile*k*128+h*128+offset//8]>>(4*(offset%8)))&15
                    require(code%8!=1,'subnormal E2M1 codec')
                    v=[0,.5,1,1.5,2,3,4,6][code%8]*(-1 if code&8 else 1)
                    parts.append(Q(v)*Q(2)**pack['exponents'][tile*k+h])
                exact=Q(d['a'][i*p+j]);value=sum(parts);magnitude=sum(map(abs,parts))
                for direction,row in ((0,i),(1,j)):
                    z=3*p*direction+row
                    sums[z]+=abs(exact);sums[z+p]+=abs(exact-value);sums[z+2*p]+=magnitude
        for exact,bound in zip(sums,pack['norms']):require(math.isfinite(bound) and Q(bound)>=exact,'matrix summary fails exact rational bound');outputs+=1
    return outputs


def run(out):
    out=Path(out);out.mkdir(exist_ok=False);manifest=load(BASE/'models/manifest.json')
    put(out/'manifest.json',dict(binary=ref(BINARY),models=ref(BASE/'models/manifest.json')))
    # Exercise the larger independent checker before CUDA, including its byte cap.
    larger=[]
    for family in ('dense-generic-1024','dense-generic-2048'):
        model=ROOT/manifest['models'][family]['path']
        process=subprocess.run([str(BINARY),'check-service',str(model)],input=b'',capture_output=True,check=True,env=environment(),timeout=90)
        ready=json.loads(process.stdout);require(ready['ready'] and ready['model_sha256']==ref(model)['sha256'],'large checker readiness/hash');larger.append(dict(family=family,ready=ready))
    put(out/'large-checkers.json',dict(rows=larger))
    guards=[]
    for name,model in {**manifest['tests'],'irregular-tail-33':manifest['models']['irregular-tail-33']}.items():
        d=json.loads(subprocess.check_output([str(BINARY),'inspect',str(ROOT/model['path']),'unscaled'],env=environment(),timeout=60))
        guards.append(dict(case=name,outputs=guard_norms(d)));put(out/(name+'.inspect.json'),d)
    archive=json.loads(gzip.decompress((ROOT/'docs/benchmarks/data/fp4-accel-result-v1-endpoints.json.gz').read_bytes()))
    rows=[]
    for key,value in archive['endpoints'].items():
        ep=out/(key+'.endpoint.json');put(ep,value['endpoint']);model=ROOT/archive['manifest']['models'][value['family']]['path']
        expected={k:v for k,v in value['certificate'].items() if k!='checker_binary_sha256'}
        for command in ('check','check-serial'):
            dest=out/(key+'-'+command+'.json')
            subprocess.run([str(BINARY),command,str(model),str(ep),value['tier'],str(dest)],env=environment(),capture_output=True,check=True,timeout=60)
            actual=load(dest);require(bits({k:v for k,v in actual.items() if k!='checker_binary_sha256'})==bits(expected),'original certificate mismatch')
            rows.append(dict(key=key,command=command,certificate=ref(dest)))
    put(out/'result.json',dict(status='passed',assessments=len(rows),endpoints=len(archive['endpoints']),guards=guards,rows=rows))
    print(dict(status='passed',assessments=len(rows),guard_outputs=sum(r['outputs'] for r in guards)),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['prepare','check']);p.add_argument('--out');a=p.parse_args();prepare() if a.action=='prepare' else run(a.out)
