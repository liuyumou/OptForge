"""Image-bound tensor arithmetic, rational guard and lifecycle admission."""
import argparse
from fractions import Fraction as Q
import json
import math
import os
from pathlib import Path
import struct
import subprocess
from lp_mixed2_fp4_common import ROOT,BASE,BINARY,load,put,ref,require
from lp_mixed2_fp4_cpu import environment
from lp_mixed2_fp4_transport import Service
from lp_delivery2_study import bits


def exact_product(d,raw,tr):
    p=d['p'];x=raw[(p if tr else 2*p):(2*p if tr else 3*p)];result=[]
    for i in range(p):result.append(sum((Q(d['a'][j*p+i if tr else i*p+j])*Q(x[j]) for j in range(p)),Q(0)))
    return result


def native_product(d,raw,tr):
    p=d['p'];x=raw[(p if tr else 2*p):(2*p if tr else 3*p)];result=[]
    for i in range(p):
        partial=[]
        for w in range(8):
            v=0.
            for j in range(w,p,8):v+=d['a'][j*p+i if tr else i*p+j]*x[j]
            partial.append(v)
        v=0.
        for x0 in partial:v+=x0
        result.append(v)
    return result


def check_product(d,raw,tr,result,native=False,exact=False):
    truth=exact_product(d,raw,tr);require(len(result['product'])==d['p']==len(result['bound']),'product dimensions')
    for v,b,q in zip(result['product'],result['bound'],truth):
        require(math.isfinite(v) and math.isfinite(b) and b>=0,'invalid product enclosure')
        if not native:require(abs(Q(v)-q)<=Q(b),'original product escapes local enclosure')
        if exact:require(Q(v)==q,'integer component MMA is inexact')
    if native:require(bits(result['product'])==bits(native_product(d,raw,tr)),'native product arithmetic order')
    return len(truth)


def run(out,image,cpu,sanitizer=None):
    out=Path(out);image=Path(image);cpu=Path(cpu);out.mkdir(exist_ok=False)
    require(load(cpu/'result.json')['status']=='passed','CPU contract admission')
    require(load(cpu/'manifest.json')['binary']==ref(BINARY),'CPU admitted binary differs')
    require(load(BASE/'resources/native-v1.settlement.json')['status']=='passed','full native acceptance')
    os.environ['AI_OPTIMIZER_ADMISSION_TRACE']='1'
    if sanitizer:os.environ['AI_OPTIMIZER_SANITIZER']=sanitizer
    models=load(BASE/'models/manifest.json');rows=[];outputs=0
    put(out/'manifest.json',dict(binary=ref(BINARY),image=ref(image),cpu=ref(cpu/'result.json'),sanitizer=sanitizer,target_processes="application-only",
        inventory=subprocess.check_output(['nvidia-smi','--query-gpu=uuid,name,driver_version,memory.total,compute_mode','--format=csv'],text=True),
        compiler=subprocess.check_output(['/usr/local/cuda/bin/nvcc','--version'],text=True)))
    cases=['normal-code-pairs','rectangular-cancellation','scale-range','irregular-tail-33']
    for name in cases:
        d=load(cpu/(name+'.inspect.json'));model=(models['tests']|models['models'])[name];p=d['p']
        s=Service(image,ROOT/model['path'],out/(name+'.log'),equilibrate=False)
        try:
            for lane in ('native','fp4x2','fp4x4'):
                raw=d['initial'].copy();raw[0]=-0.;raw[3*p]=-0.
                values=[0,1,1.5,2,3,4,6,-1,-1.5,-2,-3,-4,-6]
                for j in range(p):
                    for plane in (1,2):raw[plane*p+j]=values[(j+(plane-1)*5)%13]/8 if name=='normal-code-pairs' else math.ldexp(((j*13+plane*7)%37)/37-.5,(j%9)-4)
                # Padding is deliberately nonzero: arithmetic consumes padded zero coefficients safely.
                s.call('debug_reset',lane=lane,raw=raw,max_updates=1000)
                before=s.call('debug_export'); require(bits(before['raw'])==bits(raw),'reset changed FP64 state')
                for tr in (False,True):
                    r=s.call('debug_transpose' if tr else 'debug_forward')
                    outputs+=check_product(d,raw,tr,r,lane=='native',name=='normal-code-pairs')
                    rows.append(dict(case='direct-product',family=name,lane=lane,transpose=tr,raw=raw,result=r))
                    for guarded in (True,False):
                        op=('debug_bench_' if guarded else 'debug_unguarded_')+('transpose' if tr else 'forward')
                        batch=s.call(op,count=3)
                        require(bits(batch['product'])==bits(r['product']),'diagnostic batch changed product')
                        require(batch['guarded']==guarded and batch['count']==3,'diagnostic scope')
                        if guarded:require(bits(batch['bound'])==bits(r['bound']),'batched guard differs')
                        else:require(all(v==0 for v in batch['bound']),'unguarded diagnostic mislabeled')
                step=s.call('debug_step',count=3,limit=1e20);require(step['physical']==3 and not any(step['step']['flags']),'paired work')
                current=s.call('debug_export')
                for tr in (False,True):
                    r=s.call('debug_centered_transpose' if tr else 'debug_centered_forward')
                    outputs+=check_product(d,current['raw'],tr,r,lane=='native')
                    rows.append(dict(case='centered-product',family=name,lane=lane,transpose=tr,raw=current['raw'],result=r))
                s.call('debug_save');saved=s.call('debug_saved');s.call('debug_step',count=5,limit=1e20);s.call('debug_restore');restored=s.call('debug_export')
                require(bits(saved['raw'])==bits(restored['raw']) and restored['logical']==saved['logical'] and restored['generation']==1,'checkpoint restoration')
                s.call('debug_finish');rows.append(dict(case='checkpoint',family=name,lane=lane,exact=True))
        finally:s.close()
        put(out/(name+'.arithmetic.json'),dict(rows=[r for r in rows if r.get('family')==name]))
    # Cover all >512 grid/norm indices and the largest admitted allocations.
    for name in ('dense-generic-1024','dense-generic-2048'):
        s=Service(image,ROOT/models['models'][name]['path'],out/(name+'.log'))
        try:
            for lane in ('native','fp4x2','fp4x4'):
                s.call('debug_reset',lane=lane,max_updates=100);initial=s.call('debug_export')
                step=s.call('debug_step',count=2,limit=1e20);require(step['physical']==2 and not any(step['step']['flags']),'large-grid step')
                s.call('debug_restore');restored=s.call('debug_export');require(bits(initial['raw'])==bits(restored['raw']),'large-grid restore')
                s.call('debug_finish');rows.append(dict(case='large-grid',family=name,lane=lane,step=step))
        finally:s.close()
    families=('coupled-equality','dense-generic-128','irregular-tail-33') if sanitizer else tuple(models['models'])
    for name in families:
        s=Service(image,ROOT/models['models'][name]['path'],out/('solve-'+name+'.log'))
        try:
            for lane in ('native','fp4x2','fp4x4'):
                r,elapsed=s.solve_to_file(out/(name+'-'+lane+'.json'),lane=lane,tier='certified-1e-9',**models['settings'])
                require(r['certified']==(name!='infinite-bound-refusal'),'unexpected final certificate: '+name+' '+lane)
                require(r['physical']==sum(r['attempted'].values()) and elapsed>=r['solve_ns'],'complete work accounting')
                if lane=='native':
                    prior=BASE/'device-v2'/(name+'-native.json')
                    old=load(prior)
                    def strip(v):
                        if isinstance(v,dict):return {k:strip(x) for k,x in v.items() if k!='checker_binary_sha256'}
                        if isinstance(v,list):return list(map(strip,v))
                        return v
                    for key in ('endpoint','certificate','audits','checkpoint','terminal','physical','logical','attempted','status'):
                        require(bits(strip(r[key]))==bits(strip(old[key])),'native differential: '+name+' '+key)
                rows.append(dict(case='solve',family=name,lane=lane,certified=r['certified'],complete_ns=elapsed,result=ref(out/(name+'-'+lane+'.json'))))
        finally:s.close()
    model=ROOT/models['models']['dense-generic-128']['path']
    for case,fields in [('cancel',dict(cancel_after=7)),('deadline',dict(wall_ms=0)),('guard',dict(fault='local_budget')),('conversion',dict(fault='conversion_failure'))]:
        s=Service(image,model,out/(case+'.log'))
        try:
            r,elapsed=s.solve_to_file(out/(case+'.json'),lane='fp4x2',tier='certified-1e-9',**fields)
            if case in ('cancel','deadline'):
                require(r['status']==('cancelled' if case=='cancel' else 'deadline') and not r['certified'],'interruption authority')
                require(bits(r['terminal']['raw'])==bits(r['checkpoint']['device']['raw']),'interruption restore')
            else:
                require(r['certified'] and any(x['kind']=='recovery' for x in r['events']),'recovery certificate')
                if case=='conversion':require(any(x['kind']=='conversion_failure' for x in r['events']) and r['final_lane']==32,'permanent native fallback')
            rows.append(dict(case=case,result=ref(out/(case+'.json'))))
        finally:s.close()
    # New explicit fixed schedule changes checkpoints, never certificate authority.
    for name in ('dense-generic-128','coupled-equality'):
        s=Service(image,ROOT/models['models'][name]['path'],out/('fixed-'+name+'.log'))
        try:
            for lane in ('native','fp4x2','fp4x4'):
                for window in (8,16,32):
                    path=out/(f'fixed-{name}-{lane}-{window}.json')
                    r,_=s.solve_to_file(path,lane=lane,tier='certified-1e-9',fixed_audit=True,window_max=window,**models['settings'])
                    require(r['certified'] and r['fixed_audit'] and r['physical']==sum(r['attempted'].values()),'fixed schedule certificate/work')
                    rows.append(dict(case='fixed-schedule',family=name,lane=lane,window=window,result=ref(path)))
        finally:s.close()
    if sanitizer:
        logs=list(out.glob('*.sanitizer'));require(logs,'missing sanitizer logs')
        for p in logs:
            text=p.read_text();require('ERROR SUMMARY: 0 errors' in text or (sanitizer=='racecheck' and 'RACECHECK SUMMARY: 0 hazards' in text),'sanitizer errors: '+str(p))
    put(out/'result.json',dict(status='passed',cases=len(rows),rational_outputs=outputs,rows=rows,sanitizer=sanitizer))
    print(dict(status='passed',cases=len(rows),rational_outputs=outputs,sanitizer=sanitizer),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('out');p.add_argument('--image',required=True);p.add_argument('--cpu',required=True);p.add_argument('--sanitizer',choices=['memcheck','racecheck','initcheck','synccheck']);a=p.parse_args();run(a.out,a.image,a.cpu,a.sanitizer)
