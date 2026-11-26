"""Admission for the lean FP64/GMP path, including continued and inactive states."""
import argparse
from fractions import Fraction as Q
import json
from pathlib import Path
import subprocess
import sys
import time
from lp_sp_pricing_budget import ROOT,BASE,binding,put

CRATE=ROOT/'research/lp-sp-pricing'
sys.path.insert(0,str(CRATE/'python'))
from sp_pricing.exact import Work,rational
from sp_pricing.geometry import LabelOracle
from sp_pricing.gpu import GpuBatch,accept_proposal
from sp_pricing.gpu_lean import LeanBatch
from sp_pricing.native_proof import NativeProof

LIBRARY=CRATE/'target/release/libsp_batch_optimized.so'
OLD=BASE/'gpu-optimization-baseline-v1/research/lp-sp-pricing/target/release/liblp_sp_pricing.so'


def scalar_pdhg(b,slot,h,eps,steps):
    """Independent scalar equations for the candidate's diagonal metric."""
    b=[[float(v) for v in row] for row in b];r,s=len(b),len(b[0]);h,eps=float(h),float(eps)
    tau=[.9/sum(map(abs,row)) if any(row) else 1. for row in b]
    sums=[sum(abs(b[i][j]) for i in range(r)) for j in range(s)]
    sigma=[.9/v if v else 1. for v in sums]
    x=[0.]*r;u=[0.]*s
    for _ in range(steps):
        nxt=[max(-h,min(h,x[i]+tau[i]*(b[i][slot]-sum(b[i][j]*u[j] for j in range(s))))) for i in range(r)]
        bar=[2*v-old for v,old in zip(nxt,x)];x=nxt
        for j in range(s):
            v=u[j]+sigma[j]*sum(b[i][j]*bar[i] for i in range(r))
            u[j]=v-2*sigma[j] if v>2*sigma[j] else v+eps*sigma[j] if v<-eps*sigma[j] else 0.
    return x,u


def sources():
    paths=[LIBRARY,CRATE/'target/cpu/libsp_proof.so',CRATE/'native/batch_optimized.cu',
        CRATE/'native/proof.cpp',CRATE/'native/gmp_abi.h',CRATE/'python/sp_pricing/gpu.py',
        CRATE/'python/sp_pricing/gpu_lean.py',CRATE/'python/sp_pricing/native_proof.py',
        ROOT/'tools/lp_sp_pricing_run.py']
    return [binding(p) for p in paths]


def validate(receipt):
    d=json.loads(Path(receipt).read_text())
    if d['status']!='passed' or d['sources']!=sources():raise RuntimeError('lean admission does not bind current source')
    for item in d['evidence']:
        if binding(item['path'])!=item:raise RuntimeError('lean admission evidence changed')


def cpu(identity):
    out=BASE/identity;out.mkdir(exist_ok=False)
    command=['g++','-std=c++17','-O1','-g','-fsanitize=address,undefined','-fno-omit-frame-pointer',
        str(CRATE/'native/proof.cpp'),str(CRATE/'native/proof_test.cpp'),
        '/usr/lib/x86_64-linux-gnu/libgmp.so.10.4.1','-o',str(out/'proof-sanitized')]
    subprocess.run(command,check=True)
    with (out/'sanitizer.log').open('x') as log:
        subprocess.run([str(out/'proof-sanitized')],check=True,stdout=log,stderr=subprocess.STDOUT)
    subprocess.run([sys.executable,'-B','-m','unittest','discover','-s','tests/integration','-p','test_lp_sp_pricing*.py'],check=True)
    put(out/'result.json',dict(status='passed',sanitizers=['ASan','UBSan'],native_cases=96,
        log=binding(out/'sanitizer.log'),binary=binding(out/'proof-sanitized'),sources=sources()))


def quality(path,smoke=False):
    r_values=[4,32] if smoke else [1,4,17,40,257]
    cases=[]
    for r in r_values:
        b=[[Q(int(j==2*i+(i%2))) for j in range(2*r)] for i in range(r)]
        cases.append((str(r),b,Q(4),Q(1,1024*r)))
    if not smoke:
        result=json.loads((BASE/'gpu-ladder-v2/coupled-8-73011/result.json').read_text())
        for i,event in enumerate(result['events']):
            if 'calibration' not in event:continue
            c=event['calibration'];cases.append((f'real-{i}',[[rational(v) for v in row] for row in c['basis']],rational(c['H']),rational(c['epsilon'])))
    rows=[];proofs=0
    for name,b,h,eps in cases:
        oracle=LabelOracle(b,h,eps,Work(max_operations=500000000,seconds=600))
        for sparse in (False,True):
            with LeanBatch(LIBRARY,b,sparse) as engine,NativeProof(oracle) as checker:
                for width in (([8] if name=='4' else [1]) if smoke else [1,8,32,64]):
                    slots=[i%(2*oracle.n) for i in range(width)]
                    engine.begin(slots,h,eps)
                    engine.advance(17);continued=engine.advance(47)
                    whole=engine.propose(slots,h,eps,64,'fp64',slot_targets=True)
                    if any(whole[k]!=continued[k] for k in ['x','dual']):raise AssertionError('continued state differs from uninterrupted steps')
                    if not smoke and oracle.r<=17:
                        errors=[]
                        for q,slot in enumerate(slots[:4]):
                            reference=scalar_pdhg(b,slot,h,eps,64)
                            for key,values in zip(['x','dual'],reference):
                                errors.extend(abs(x-y)/max(1,abs(y)) for x,y in zip(whole[key][q],values))
                        maximum=max(errors)
                        if maximum>1e-10:raise AssertionError('persistent iteration differs from admitted reference')
                    else:maximum=None
                    for index,slot in enumerate(slots):
                        p=checker.check(slot//2,whole['x'][index],whole['dual'][index],full_dual=True)
                        independent=accept_proposal(oracle,slot//2,whole['x'][index],whole['dual'][index])
                        for key in ['x','witness','dual_upper','established']:
                            if p[key]!=independent[key]:raise AssertionError('native exact proof differs: '+key)
                        compact=checker.labels(slot//2,whole['x'][index],whole['dual'][index])
                        if compact['established']!=independent['established']:raise AssertionError('compact exact decisions differ')
                        if name in ['1','4','17','32','40','257'] and slot%2==(slot//2)%2 and not compact['accepted']:
                            raise AssertionError(f'no exact label for known diagonal target: {name}/{sparse}/{width}/{slot}; separation={oracle.broadcast_negative}')
                        proofs+=1
                    flags=[int(i%2==0) for i in range(width)]
                    engine.active(flags);frozen=engine.advance(11)
                    for i,flag in enumerate(flags):
                        if not flag and any(frozen[k][i]!=whole[k][i] for k in ['x','dual']):raise AssertionError('inactive query changed')
                    engine.active([0]*width);inactive=engine.advance(1)
                    if any(inactive[k]!=frozen[k] for k in ['x','dual']):raise AssertionError('all-inactive state changed')
                    rows.append(dict(case=name,sparse=sparse,width=width,continued=True,inactive_checked=True,
                                     normalized_difference=maximum,device_iteration_ms=whole['device_iteration_ms']))
                for slots in [[-1],[2*oracle.n]]:
                    try:engine.begin(slots,h,eps)
                    except RuntimeError:pass
                    else:raise AssertionError('invalid slot accepted')
    put(path,dict(status='passed',configurations=len(rows),exact_differential_proposals=proofs,rows=rows,
                  native=binding(LIBRARY),precision='fp64_only',baseline='independent_scalar_diagonal_pdhg',smoke=smoke))
    print(json.dumps(dict(status='passed',configurations=len(rows),exact_differential_proposals=proofs)),flush=True)


def admit(identity):
    out=BASE/identity;out.mkdir(exist_ok=False)
    quality(out/'quality.json')
    evidence=[binding(out/'quality.json')]
    for tool in ['memcheck','racecheck','initcheck','synccheck']:
        command=['/usr/local/cuda/bin/compute-sanitizer','--tool',tool,'--error-exitcode','91','--target-processes','all',
            sys.executable,'-B',__file__,'quality',str(out/(tool+'.json')),'--smoke']
        with (out/(tool+'.log')).open('x') as log:subprocess.run(command,stdout=log,stderr=subprocess.STDOUT,check=True)
        evidence += [binding(out/(tool+suffix)) for suffix in ['.json','.log']]
    cpu_receipt=BASE/identity.replace('-admit-','-cpu-admit-')/'result.json'
    cpu_data=json.loads(cpu_receipt.read_text())
    cpu_sources={item['path']:item for item in cpu_data['sources']}
    for item in sources():
        if item['path'].endswith(('proof.cpp','native_proof.py','libsp_proof.so','gmp_abi.h')) and cpu_sources.get(item['path'])!=item:
            raise RuntimeError('CPU proof admission does not match')
    evidence.append(binding(cpu_receipt))
    put(out/'admission.json',dict(status='passed',sources=sources(),evidence=evidence))
    print(json.dumps(dict(status='passed',sanitizers=4)),flush=True)


def resume(identity,previous):
    """Retain the failed reservation; complete only its unfinished sanitizers."""
    old=BASE/previous;out=BASE/identity;out.mkdir(exist_ok=False)
    receipt=BASE/'resources'/(previous+'.settlement.json')
    settled=json.loads(receipt.read_text())
    if settled['status']!='refused' or not settled['cleanup_empty'] or settled['overrun']:
        raise RuntimeError('previous admission has no usable cleanup disposition')
    reserved=json.loads((BASE/'resources'/(previous+'.reservation.json')).read_text())
    original={item['path']:item for item in reserved['sources']}
    cpu_receipt=BASE/previous.replace('-admit-','-cpu-admit-')/'result.json'
    cpu_data=json.loads(cpu_receipt.read_text());cpu_sources={i['path']:i for i in cpu_data['sources']}
    for item in sources():
        retained=original.get(item['path'],cpu_sources.get(item['path']))
        if retained is None or any(item[k]!=retained[k] for k in ['bytes','sha256']):
            raise RuntimeError('interrupted admission source changed')
    quality_data=json.loads((old/'quality.json').read_text())
    memory_data=json.loads((old/'memcheck.json').read_text())
    if quality_data['status']!='passed' or memory_data['status']!='passed' or binding(LIBRARY)!=quality_data['native']:
        raise RuntimeError('retained native quality proof missing')
    if 'ERROR SUMMARY: 0 errors' not in (old/'memcheck.log').read_text():raise RuntimeError('retained memcheck incomplete')
    evidence=[binding(old/name) for name in ['quality.json','memcheck.json','memcheck.log']]+[binding(cpu_receipt),binding(receipt)]
    put(out/'plan.json',dict(status='source_bound_unfinished_sanitizers_only',sources=sources(),retained=evidence,
        tools=['racecheck','initcheck','synccheck'],host_reservation_gib=32,
        sanitizer_scope='smaller smoke: persistent r4/width8 and graph r32/width1; both formats, continuation and inactive states; original larger interrupted workload retained',
        previous_trigger='coordinator_lost; preceding cause unavailable; full failed charge retained'))
    for tool in ['racecheck','initcheck','synccheck']:
        command=['/usr/local/cuda/bin/compute-sanitizer','--tool',tool,'--error-exitcode','91','--target-processes','all',
            sys.executable,'-B',__file__,'quality',str(out/(tool+'.json')),'--smoke']
        with (out/(tool+'.log')).open('x') as log:subprocess.run(command,stdout=log,stderr=subprocess.STDOUT,check=True)
        evidence += [binding(out/(tool+suffix)) for suffix in ['.json','.log']]
    put(out/'admission.json',dict(status='passed',sources=sources(),evidence=evidence,retained_failure=binding(receipt)))
    print(json.dumps(dict(status='passed',retained_sanitizers=1,new_sanitizers=3)),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['cpu','quality','admit','resume']);p.add_argument('target');p.add_argument('--smoke',action='store_true')
    p.add_argument('--previous')
    a=p.parse_args()
    if a.action=='cpu':cpu(a.target)
    elif a.action=='quality':quality(Path(a.target),a.smoke)
    elif a.action=='admit':admit(a.target)
    else:resume(a.target,a.previous)
