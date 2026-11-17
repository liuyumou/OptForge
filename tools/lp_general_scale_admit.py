"""Input, host arithmetic and installed COPT baseline admission for scale work."""
import argparse
import json
import subprocess
from pathlib import Path
import numpy as np
from lp_general_common import BASE,ROOT,put,load,ref,require
from lp_general_models import generate,FAMILIES
from lp_general_oracle import settings
from lp_general_device import serial
from lp_general_scale_io import write,from_document
from lp_general_scale_copt import PYTHON

BINARY=ROOT/'research/lp-general-lowbit/target/release/lp-general-lowbit'
def call(command,model,requests):
    p=subprocess.run([str(BINARY),command,str(model)],input=''.join(json.dumps(r)+'\n' for r in requests),text=True,capture_output=True)
    require(p.returncode==0,'CPU admission '+p.stderr)
    return [json.loads(s) for s in p.stdout.splitlines()]

def cpu(identity):
    out=BASE/identity;out.mkdir(exist_ok=False);comparisons=[];probes=[];checks=[]
    from lp_general_scale_imports import validate
    imports=validate(identity);cached=[]
    for i,family in enumerate(FAMILIES):
        doc,w=generate(family,33,831100+i);j=out/(family+'.json');put(j,doc);p=out/(family+'.lpcsr');write(p,from_document(doc))
        requests=[dict(settings={**settings(f),'iteration_limit':8,'check_interval':8}) for f in ['native','fp32','fp4x1','fp4x2']]
        a=call('cpu',j,requests);b=call('cpu',p,requests)
        for k,(x,y) in enumerate(zip(a,b)):
            canonical=lambda r:json.dumps({k:v for k,v in r.items() if k not in ['model_sha256','elapsed_ns','cost_ns']},sort_keys=True,separators=(',',':'))
            require(canonical(x)==canonical(y),'compact numerical input equivalence')
            put(out/f'{family}-{k}.json',y);comparisons.append(dict(family=family,format=requests[k]['settings']['format']))
        proof=call('assess',p,[dict(settings=settings(),primal=w['primal'],dual=w['dual'])])[0]
        require(proof['accepted'],'construction certificate')
        checks.append(serial(j,dict(primal=w['primal'],dual=w['dual'],certificate=proof),1e-9,out,family))
        candidate_requests=[]
        for tol in [1e-7,1e-9]:
            for factor in [0.,1.,-1.,1e-300,1e100]:
                candidate_requests.append(dict(settings={**settings(),'tolerance':tol},primal=w['primal'],dual=[factor*y for y in w['dual']]))
        original=call('assess-proven',p,candidate_requests);optimized=call('assess-fast',p,candidate_requests)
        require(json.dumps(original,sort_keys=True)==json.dumps(optimized,sort_keys=True),'cached original certificate differs')
        cached.append(dict(family=family,requests=len(candidate_requests),exact=True));put(out/(family+'-cached.json'),optimized)
        probe_requests=[]
        rng=np.random.default_rng(831200+i)
        for weight in [1e-6,.1,1.,100.,1e6]:
            probe_requests.append(dict(settings=settings(),primal=rng.uniform(-10,10,w['columns']).tolist(),dual=rng.uniform(-10,10,w['rows']).tolist(),weight=weight))
        for r in call('host-probe',p,probe_requests):
            require(json.dumps(r['original'])==json.dumps(r['optimized']) and r['original_merit']==r['optimized_merit'],'host product/projection arithmetic')
            probes.append(dict(family=family,exact=True))
    # Exercise four-worker host products and both rectangular orientations.
    for family in ['irregular','rectangular']:
        doc,w=generate(family,4097,831999);p=out/(family+'-large.lpcsr');write(p,from_document(doc))
        for r in call('host-probe',p,[dict(settings=settings(),primal=w['primal'],dual=w['dual'],weight=.125)]):
            require(json.dumps(r['original'])==json.dumps(r['optimized']),'parallel original-order products');probes.append(dict(family=family,large=True,exact=True))
    put(out/'result.json',dict(status='passed',binary=ref(BINARY),input_comparisons=comparisons,host_probes=probes,serial=checks,cached=cached,imports=imports))
    print(dict(status='passed',input_comparisons=len(comparisons),host_probes=len(probes)),flush=True)

def copt(identity,gpu):
    out=BASE/identity;out.mkdir(exist_ok=False);rows=[]
    for i,family in enumerate(['irregular','dense_blocks','ill_scaled']):
        doc,w=generate(family,33,832100+i)
        # Include maximization and ranged rows to test objective/dual conventions.
        if i==1:
            doc['objective']['sense']='maximize'
            for t in doc['objective']['terms']:t['coefficient']=-t['coefficient']
        j=out/(family+'.json');put(j,doc);p=out/(family+'.lpcsr');write(p,from_document(doc))
        for ti,tol in enumerate([1e-7,1e-9]):
            dest=out/f'{family}-{ti}.copt.json'
            command=[str(PYTHON),'-B',str(ROOT/'tools/lp_general_scale_copt.py'),'--model',str(p),'--output',str(dest),'--method','copt-gpu-pdlp' if gpu else 'copt-cpu-auto','--tolerance',str(tol),'--seconds','10','--roundtrip']
            child=subprocess.run(command,text=True,capture_output=True);(out/f'{family}-{ti}.stdout').write_text(child.stdout);(out/f'{family}-{ti}.stderr').write_text(child.stderr)
            require(child.returncode==0,'COPT baseline admission '+child.stderr)
            r=load(dest);require(r['has_solution'] and (not gpu or r['gpu_confirmed']),'COPT actual execution')
            cert=call('assess',p,[dict(settings={**settings(),'tolerance':tol},primal=r['primal'],dual=r['dual'])])[0]
            proof=serial(j,dict(primal=r['primal'],dual=r['dual'],certificate=cert),tol,out,f'{family}-{ti}')
            rows.append(dict(response=ref(dest),certificate=cert,serial=proof))
    put(out/'result.json',dict(status='passed',rows=rows,gpu=gpu,binary=ref(BINARY)))
    print(dict(status='passed',cases=len(rows),gpu=gpu),flush=True)

def gpu(identity,sanitizer=None,version=1):
    out=BASE/identity;out.mkdir(exist_ok=False);rows=[]
    image=BASE/f'scale-image-v{version}/tensor.cubin'
    old=BASE/'fast-image-v10/executor'
    require(load(BASE/'scale-cpu-v1/result.json')['status']=='passed','CPU admission first')
    require(ref(image)['sha256']==ref(BASE/'fast-image-v10/tensor.cubin')['sha256'],'unchanged device instructions')
    if version>=4:
        from lp_general_scale_imports import validate
        validate(f'scale-cpu-v{version}')
    cases=[('dense',257),('irregular',4097),('rectangular',4097),('ill_scaled',65),('dense_blocks',129)]
    for family,size in cases:
        doc,_=generate(family,size,832700+size);j=out/(family+'.json');put(j,doc);compact=out/(family+'.lpcsr');write(compact,from_document(doc))
        formats=['native','fp32','fp4x1','fp4x2']
        for fmt in formats:
            for fault in [None,'force_recovery_after','cancel_after'] if not sanitizer else [None]:
                s={**settings(fmt),'iteration_limit':32,'check_interval':16}
                if fault:s[fault]=3
                request=dict(settings=s,tensor=dict(control_interval=8,min_tile_nnz=128),fast=dict(host_reductions=True,host_preparation=version>1,host_certificates=version>=4,auto_schedule=version>=6))
                name=f'{family}-{fmt}-{fault}';command=[str(BINARY),'gpu-fast',str(compact),str(image)]
                if sanitizer:command=['/usr/local/cuda/bin/compute-sanitizer','--tool',sanitizer,'--error-exitcode','99','--log-file',str(out/(name+'.sanitizer')),*command]
                p=subprocess.run(command,input=json.dumps(request)+'\n',text=True,capture_output=True)
                (out/(name+'.stderr')).write_text(p.stderr);require(p.returncode==0,'scale GPU admission '+name)
                r=json.loads(p.stdout);put(out/(name+'.response.json'),r)
                # Auto scheduling is compared to the same explicit admitted
                # schedule; split and combined can change FP32 reduction order.
                control={**request,'fast':dict(combined=r.get('selected_schedule')!='split')}
                q=subprocess.run([str(old),'gpu-fast',str(j),str(image)],input=json.dumps(control)+'\n',text=True,capture_output=True)
                require(q.returncode==0,'historical control failed');before=json.loads(q.stdout)
                def canonical(v):
                    schedule=v.get('selected_schedule')
                    v={k:x for k,x in v.items() if k not in ['model_sha256','elapsed_ns','cost_ns','cached_assessments','selected_schedule','initial_fast_lanes','device_bytes_upper']}
                    v['fast_config']={k:x for k,x in v['fast_config'].items() if k not in ['host_reductions','host_preparation','host_certificates','auto_schedule']}
                    if schedule=='split':v['fast_config']['combined']=False
                    return json.dumps(v,sort_keys=True,separators=(',',':'))
                require(canonical(r)==canonical(before),'exact whole GPU continuation '+name)
                proofs=[serial(j,{**e,'bound_proof':r['bound_proof']},s['tolerance'],out,name+'-'+str(i)) for i,e in enumerate([*r['assessments'],r])]
                if sanitizer:
                    text=(out/(name+'.sanitizer')).read_text();require('ERROR SUMMARY: 0 errors' in text or 'RACECHECK SUMMARY: 0 hazards' in text,'sanitizer summary')
                rows.append(dict(case=name,response=ref(out/(name+'.response.json')),serial=proofs,exact=True))
    put(out/'result.json',dict(status='passed',rows=rows,binary=ref(BINARY),image=ref(image),sanitizer=sanitizer))
    print(dict(status='passed',exact_responses=len(rows),sanitizer=sanitizer),flush=True)

def seal_copt(identity):
    # Offline disposition only: the failed admission's scientific cells are
    # never rerun, and its full reservation remains charged.
    source=BASE/'scale-copt-gpu-v1';out=BASE/identity;out.mkdir(exist_ok=False);rows=[]
    for p in sorted(source.glob('*.copt.json')):
        r=load(p);require(r['gpu_confirmed'] and r['roundtrip_checked'],'COPT device/import admission')
        if r['has_solution']:
            proof=p.with_name(p.name.replace('.copt.json','.serial.json'));require(proof.exists(),'original serial endpoint missing')
            rows.append(dict(response=ref(p),serial=ref(proof),outcome='solution'))
        else:
            require(r['status']==8 and r['primal'] is None and r['dual'] is None,'explicit time limit without endpoint')
            rows.append(dict(response=ref(p),outcome='time_limit_without_solution'))
    require(len(rows)==5,'retained partial admission coverage')
    put(out/'result.json',dict(status='passed',scope='Import, actual GPU execution, dual conventions at both tiers, and no-solution time-limit reporting; not universal convergence.',
        rows=rows,missing=['ill_scaled-1'],original_failed_reservation=ref(BASE/'resources/scale-copt-gpu-v1.settlement.json'),worker=ref(ROOT/'tools/lp_general_scale_copt.py')))

def malformed(identity):
    import struct
    out=BASE/identity;out.mkdir(exist_ok=False)
    b=(BASE/'scale-gpu-v1/irregular.lpcsr').read_bytes()
    cases=[('truncated-'+str(k),b[:k]) for k in [0,7,63,100,len(b)-1]]+[('trailing',b+b'0')]
    for at,value in [(8,(1<<20)+1),(24,(1<<26)+1),(32,2),(48,0),(56,5000)]:
        c=bytearray(b);struct.pack_into('<Q',c,at,value);cases.append(('header-'+str(at),bytes(c)))
    c=bytearray(b);struct.pack_into('<d',c,len(c)-8,float('nan'));cases.append(('coefficient-nan',bytes(c)))
    n,m,z,_,_,idlen,_=struct.unpack('<QQQQdQQ',b[8:64])
    for name,at,dt,value in [('duplicate-ID',64+idlen+4,'I',0),('wrong-infinity',64+idlen+4*(n+m),'d',float('inf')),
        ('bad-offset',64+idlen+20*(n+m),'Q',1),('bad-position',64+idlen+20*(n+m)+8*(m+1),'I',n)]:
        c=bytearray(b);struct.pack_into('<'+dt,c,at,value);cases.append((name,bytes(c)))
    results=[]
    for name,data in cases:
        path=out/(name+'.lpcsr');path.write_bytes(data)
        p=subprocess.run([str(BINARY),'assess',str(path)],input='',capture_output=True,text=True)
        require(p.returncode!=0 and not p.stdout,'native malformed-input refusal '+name)
        results.append(dict(input=ref(path),error=p.stderr.strip()))
    put(out/'result.json',dict(status='passed',binary=ref(BINARY),cases=results))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['cpu','copt','gpu','seal-copt','malformed']);p.add_argument('--id',required=True);p.add_argument('--gpu',action='store_true');p.add_argument('--version',type=int,choices=[1,2,3,4,5,6,7],default=1);p.add_argument('--sanitizer',choices=['memcheck','racecheck','initcheck','synccheck']);a=p.parse_args()
    if a.action=='cpu':cpu(a.id)
    elif a.action=='gpu':gpu(a.id,a.sanitizer,a.version)
    elif a.action=='seal-copt':seal_copt(a.id)
    elif a.action=='malformed':malformed(a.id)
    else:copt(a.id,a.gpu)
