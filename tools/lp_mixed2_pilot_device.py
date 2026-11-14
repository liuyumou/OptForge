"""New-image arithmetic, lifecycle and sanitizer admission for MIXED2 pilot."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import time
from lp_mixed2_pilot_common import ROOT,BASE,BINARY,IMAGE,load,put,ref,require
from lp_mixed2_pilot_cpu import environment
from lp_mixed2_pilot_transport import Service
from lp_mixed2_pilot_validate import exact_solve,profile,check_guard,rhs
from lp_delivery2_study import PARENT,bits


def prior(family):
    m=load(PARENT/'manifest.json')
    cell=next(c for c in m['cells'] if c['family']==family and c['lane']=='nativefast' and c['tier']=='certified-1e-9' and c['lifecycle']=='prepared')
    return ref(PARENT/(cell['id']+'.json'))


def product(inp,out,stem):
    path=out/(stem+'.input.json');dest=out/(stem+'.result.json');put(path,inp)
    prefix=[]
    if os.environ.get('AI_OPTIMIZER_SANITIZER'):
        prefix=['/usr/local/cuda/bin/compute-sanitizer','--tool',os.environ['AI_OPTIMIZER_SANITIZER'],'--error-exitcode','86','--log-file',str(out/(stem+'.sanitizer'))]
    started=time.monotonic_ns()
    r=subprocess.run(prefix+[str(BINARY),'product-pilot',str(IMAGE),str(path),str(dest)],capture_output=True,timeout=25,env=environment('control'))
    (out/(stem+'.stderr')).write_bytes(r.stderr);r.check_returncode()
    return dict(complete_ns=time.monotonic_ns()-started,input=ref(path),result=ref(dest),value=load(dest))


def matrix_input(model,transpose):
    d=json.loads(subprocess.check_output([str(BINARY),'inspect',str(model),'unscaled'],env=environment('control'),timeout=30))
    n,m,p=d['n'],d['m'],d['p']
    return dict(rows=m,cols=n,a=[d['a'][r*p+c] for r in range(m) for c in range(n)],x=rhs(m if transpose else n),transpose=transpose)


def run(out,sanitizer=None):
    out=Path(out);out.mkdir(parents=True,exist_ok=False)
    require(load(BASE/'cpu-v1/result.json')['status']=='passed','CPU admission')
    require(load(BASE/'resources/cpu-native-v1.settlement.json')['status']=='passed','full native gate')
    require(load(BASE/'cpu-v1/manifest.json')['binary']==ref(BINARY),'CPU admitted executable changed')
    if sanitizer:os.environ['AI_OPTIMIZER_SANITIZER']=sanitizer
    m=load(PARENT/'manifest.json');binary=ref(BINARY);image=ref(IMAGE);rows=[]
    inventory=subprocess.check_output(['nvidia-smi','--query-gpu=uuid,name,driver_version,memory.total,compute_mode','--format=csv'],text=True,timeout=10)
    compiler=subprocess.check_output(['/usr/local/cuda/bin/nvcc','--version'],text=True,timeout=10)
    put(out/'manifest.json',dict(binary=binary,image=image,sanitizer=sanitizer,parent=ref(PARENT/'manifest.json'),inventory=inventory,compiler=compiler))
    families=('dense-generic-512','irregular-tail-33') if sanitizer else tuple(m['models'])
    for family in families:
        for variant in ('control','profile'):
            s=Service(IMAGE,ROOT/m['models'][family]['path'],out/f'{family}-{variant}.log',variant=variant)
            try:
                r,elapsed=s.solve_to_file(out/f'{family}-{variant}.json',lane='nativefast',tier='certified-1e-9',**m['settings'])
                old=prior(family);exact_solve(r,load(ROOT/old['path']),binary,image)
                rows.append(dict(case='original-solve',family=family,variant=variant,certified=r['certified'],complete_ns=elapsed,original=old,result=ref(out/f'{family}-{variant}.json')))
            finally:s.close()
            if variant=='profile':profile([json.loads(x) for x in (out/f'{family}-{variant}.log').read_text().splitlines()])
    for family in ('dense-generic-512','irregular-tail-33'):
        for variant in ('control','profile'):
            s=Service(IMAGE,ROOT/m['models'][family]['path'],out/f'checkpoint-{family}-{variant}.log',variant=variant)
            try:
                s.call('debug_reset',lane='gridnative',max_updates=1000);initial=s.call('debug_export')
                r=s.call('debug_step',count=8,limit=1.);require(r['physical']==8,'work accounting')
                s.call('debug_save');saved=s.call('debug_saved');s.call('debug_step',count=32,limit=1.)
                s.call('debug_restore');restored=s.call('debug_export')
                keys=('raw','codes','exponents','pairs','logical')
                require(bits({k:saved[k] for k in keys})==bits({k:restored[k] for k in keys}),'restore bits')
                s.call('debug_finish');s.call('debug_reset',lane='gridnative');fresh=s.call('debug_export')
                require(bits({k:initial[k] for k in keys})==bits({k:fresh[k] for k in keys}),'reset bits')
                s.call('debug_finish');rows.append(dict(case='checkpoint-reset',family=family,variant=variant,exact=True))
            finally:s.close()
    for variant in ('control','profile'):
        s=Service(IMAGE,ROOT/m['models']['dense-generic-128']['path'],out/f'cancel-{variant}.log',variant=variant)
        try:
            r=s.call('solve',lane='gridnative',tier='certified-1e-9',cancel_after=7)
            require(r['status']=='cancelled' and not r['certified'] and r['physical']==7,'cancellation authority')
            require(bits(r['terminal']['raw'])==bits(r['checkpoint']['device']['raw']),'cancel restore')
            rows.append(dict(case='cancel',variant=variant,result=r))
        finally:s.close()
    cases=[dict(rows=1,cols=2,a=[-0.,.1],x=[1.,-2.],transpose=False),
        dict(rows=2,cols=2,a=[2.**-149,0.,-2.**-149,2.**-126],x=[2.**-1000,-2.**-1000],transpose=False),
        dict(rows=3,cols=2,a=[1.,-1.,.1,.3,1e20,-1e20],x=[1.+2.**-52,1.],transpose=False)]
    for family in ('irregular-tail-33','dense-generic-512'):
        cases.append(matrix_input(ROOT/m['models'][family]['path'],False))
    products=[]
    for index,case in enumerate(cases):
        for tr in (False,True):
            inp={**case,'transpose':tr,'x':rhs(case['rows']) if tr else case['x'],'count':3}
            outputs={mode:product({**inp,'mode':mode},out,f'product-{index}-{int(tr)}-{mode}') for mode in ('fp64','fp32','guard')}
            check=check_guard(inp,outputs['fp32']['value']['values'],outputs['guard']['value']['values'])
            products.append(dict(case=index,transpose=tr,check=check,outputs=outputs))
    for case in ('image','model'):
        try:
            s=Service(IMAGE if case!='image' else out/'absent.cubin',ROOT/m['models']['dense-generic-128']['path'] if case!='model' else out/'absent.json',out/f'bad-{case}.log',variant='profile')
        except RuntimeError:rows.append(dict(case='setup-refusal-'+case,passed=True))
        else:s.close();raise ValueError('bad setup admitted')
    if sanitizer:
        logs=list(out.glob('*.sanitizer'));require(logs,'missing sanitizer logs')
        for p in logs:
            content=p.read_text()
            early_model=(p.name=='bad-model.log.sanitizer' and content.strip()=='========= COMPUTE-SANITIZER\n========= Error: Target application terminated before first instrumented API call')
            require(early_model or 'ERROR SUMMARY: 0 errors' in content or (sanitizer=='racecheck' and 'RACECHECK SUMMARY: 0 hazards' in content),'sanitizer errors or missing summary: '+str(p))
    put(out/'result.json',dict(status='passed',rows=rows,products=products,sanitizer=sanitizer,manifest=ref(out/'manifest.json')))
    print(dict(status='passed',cases=len(rows),product_cases=len(products),sanitizer=sanitizer),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('directory');p.add_argument('--sanitizer',choices=['memcheck','racecheck','initcheck','synccheck']);a=p.parse_args();run(a.directory,a.sanitizer)
