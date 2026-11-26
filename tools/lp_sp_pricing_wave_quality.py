"""Source-bound admission for synchronous CUDA and rigorous interval decisions."""
import argparse
import ctypes as C
from contextlib import nullcontext
from fractions import Fraction as Q
import json
from pathlib import Path
import subprocess
import sys

from lp_sp_pricing_budget import ROOT,BASE,binding,put
from lp_sp_pricing_wave_study import CRATE,build
from lp_sp_pricing_gpu_opt_quality import scalar_pdhg

sys.path.insert(0,str(CRATE/'python'))
from sp_pricing.exact import Work,rational
from sp_pricing.geometry import LabelOracle
from sp_pricing.gpu import accept_proposal
from sp_pricing.gpu_lean import LeanBatch
from sp_pricing.native_proof import NativeProof
from sp_pricing.gpu_wave import WaveEngine,PackedBasis,IntervalProof,GPU_LIBRARY,PROOF_LIBRARY


def sources():
    paths=[GPU_LIBRARY,PROOF_LIBRARY,CRATE/'native/batch_wave.cu',CRATE/'native/proof_interval.cpp',
        CRATE/'python/sp_pricing/gpu_wave.py',ROOT/'tools/lp_sp_pricing_wave_quality.py',
        ROOT/'tools/lp_sp_pricing_wave_run.py']
    return [binding(p) for p in paths]


def cpu(identity):
    out=BASE/identity;out.mkdir(exist_ok=False);build(identity+'/build')
    command=['g++','-std=c++17','-O1','-g','-ffp-contract=off','-fno-fast-math','-frounding-math',
        '-fsanitize=address,undefined','-fno-omit-frame-pointer',str(CRATE/'native/proof_interval.cpp'),
        str(CRATE/'native/proof.cpp'),str(CRATE/'native/proof_interval_test.cpp'),
        '/usr/lib/x86_64-linux-gnu/libgmp.so.10.4.1','-o',str(out/'interval-sanitized')]
    subprocess.run(command,check=True)
    with (out/'sanitizer.log').open('x') as stream:subprocess.run([str(out/'interval-sanitized')],stdout=stream,stderr=subprocess.STDOUT,check=True)
    subprocess.run([sys.executable,'-B','-m','unittest','discover','-s','tests/integration','-p','test_lp_sp_pricing*.py'],check=True)
    put(out/'result.json',dict(status='passed',sources=sources(),native_sanitizer_cases=128,
        sanitizers=['ASan','UBSan'],log=binding(out/'sanitizer.log'),binary=binding(out/'interval-sanitized')))


def quality(path,smoke=False):
    cases=[]
    for r in ([4,32] if smoke else [1,17,32,257]):
        b=[[Q(int(j==2*i+(i%2))) for j in range(2*r)] for i in range(r)]
        cases.append((str(r),b,Q(4),Q(1,1024*r)))
    if not smoke:
        original=json.loads((BASE/'gpu-ladder-v2/coupled-8-73011/result.json').read_text())
        for i,e in enumerate(original['events']):
            if 'calibration' not in e:continue
            c=e['calibration'];cases.append((f'real-{i}',[[rational(v) for v in row] for row in c['basis']],rational(c['H']),rational(c['epsilon'])))
    rows=[];proposals=0;scalar_checks=0
    with WaveEngine() as engine:
        for name,b,h,eps in cases:
            for sparse in (False,True):
                o=LabelOracle(b,h,eps,Work(max_operations=1000000000,seconds=600));packed=PackedBasis(o)
                widths=[3] if smoke else sorted({1,3,64,2*o.n})
                baseline=nullcontext(None) if smoke else LeanBatch(CRATE/'target/release/libsp_batch_optimized.so',b,sparse)
                with baseline as legacy,NativeProof(o) as exact:
                    for width in widths:
                        slots=[i%(2*o.n) for i in range(width)];active=[1]*width
                        engine.load(o,slots,packed,sparse);engine.advance(17,active);engine.advance(47,active)
                        continued_x=list(engine.x[:width*o.r]);continued_u=list(engine.u[:width*2*o.n])
                        engine.load(o,slots,packed,sparse);engine.advance(64,active)
                        x=list(engine.x[:width*o.r]);u=list(engine.u[:width*2*o.n])
                        if x!=continued_x or u!=continued_u:raise AssertionError('continued waves differ from uninterrupted waves')
                        maximum=0
                        # The baseline has capacity 64. Independent objectives
                        # allow an exact state comparison across several batches.
                        for start in ([] if smoke else range(0,width,64)):
                            actual=slots[start:start+64];padded=actual+[actual[-1]]*(64-len(actual))
                            legacy.begin(padded,h,eps);legacy.advance(64)
                            for q in range(len(actual)):
                                for observed,expected in zip(x[(start+q)*o.r:(start+q+1)*o.r],legacy.x[q*o.r:(q+1)*o.r]):
                                    maximum=max(maximum,abs(observed-expected)/(1+abs(expected)))
                                for observed,expected in zip(u[(start+q)*2*o.n:(start+q+1)*2*o.n],legacy.u[q*2*o.n:(q+1)*2*o.n]):
                                    maximum=max(maximum,abs(observed-expected)/(1+abs(expected)))
                        if maximum>1e-12:raise AssertionError('wave/legacy numerical state disagreement')
                        reference={}
                        for q,slot in enumerate(slots):
                            raw_x=x[q*o.r:(q+1)*o.r];raw_u=u[q*2*o.n:(q+1)*2*o.n]
                            proof=exact.labels(slot//2,raw_x,raw_u)
                            reference.update(proof['established']);proposals+=1
                            if q in {0,width-1}:
                                independent=accept_proposal(o,slot//2,raw_x,raw_u)
                                if proof['established']!=independent['established']:raise AssertionError('independent exact oracle differs')
                        with IntervalProof(o,packed) as interval:
                            labels,stats=interval.batch(slots,active,engine.x,engine.u,{})
                        if any(reference.get(i)!=sign for i,sign in labels.items()):
                            raise AssertionError('interval/GMP wave decisions differ')
                        if not name.startswith('real-') and labels!=reference:
                            raise AssertionError('structured wave lost a known label')
                        if o.r<=32 and width in (1,3):
                            expected_x,expected_u=scalar_pdhg(b,slots[0],h,eps,64)
                            scalar_checks+=1
                            if any(abs(a-v)>1e-10*(1+abs(v)) for a,v in zip(x[:o.r]+u[:2*o.n],expected_x+expected_u)):
                                raise AssertionError('scalar equations differ')
                        flags=[int(i%2==0) for i in range(width)];engine.advance(8,flags)
                        for q,flag in enumerate(flags):
                            if not flag and (x[q*o.r:(q+1)*o.r]!=list(engine.x[q*o.r:(q+1)*o.r]) or
                                u[q*2*o.n:(q+1)*2*o.n]!=list(engine.u[q*2*o.n:(q+1)*2*o.n])):
                                raise AssertionError('inactive state advanced')
                        last_x=list(engine.x[:width*o.r]);last_u=list(engine.u[:width*2*o.n]);engine.advance(8,[0]*width)
                        if last_x!=list(engine.x[:width*o.r]) or last_u!=list(engine.u[:width*2*o.n]):raise AssertionError('empty wave changed state')
                        rows.append(dict(case=name,sparse=sparse,width=width,normalized_difference=maximum,
                            exact_labels=len(labels),uncovered_reference_labels=len(reference)-len(labels),
                            interval=stats,continued=True,inactive=True))
    put(path,dict(status='passed',configurations=len(rows),exact_proposals=proposals,
        independent_scalar_cases=scalar_checks,rows=rows,sources=sources()))
    print(json.dumps(dict(status='passed',configurations=len(rows),exact_proposals=proposals)),flush=True)


def admit(identity,cpu_identity):
    out=BASE/identity;out.mkdir(exist_ok=False)
    cpu_result=BASE/cpu_identity/'result.json';cpu_data=json.loads(cpu_result.read_text())
    if cpu_data['status']!='passed' or cpu_data['sources']!=sources():raise RuntimeError('CPU admission changed')
    quality(out/'quality.json');evidence=[binding(cpu_result),binding(out/'quality.json')]
    for name in ['memcheck','racecheck','initcheck','synccheck']:
        command=['/usr/local/cuda/bin/compute-sanitizer','--tool',name,'--target-processes','all','--error-exitcode','91',
                 sys.executable,'-B',__file__,'quality',str(out/(name+'.json')),'--smoke']
        with (out/(name+'.log')).open('x') as stream:subprocess.run(command,stdout=stream,stderr=subprocess.STDOUT,check=True)
        evidence.extend([binding(out/(name+'.json')),binding(out/(name+'.log'))])
    model=dict(A=[[1,1],[-1,0],[0,-1]],b=[2,0,0],c=[1,1]);put(out/'model.json',model)
    with (out/'cold.log').open('x') as stream:
        subprocess.run([sys.executable,'-B',str(ROOT/'tools/lp_sp_pricing_wave_run.py'),str(out/'model.json'),
            str(out/'response.json')],stdout=stream,stderr=subprocess.STDOUT,check=True)
    from lp_sp_pricing_verify import verify
    if not verify(model,json.loads((out/'response.json').read_text()))['accepted']:
        raise RuntimeError('cold asynchronous original-LP smoke failed')
    evidence.extend(binding(out/name) for name in ['model.json','response.json','cold.log'])
    put(out/'admission.json',dict(status='passed',sources=sources(),evidence=evidence))


def validate(path):
    d=json.loads(Path(path).read_text())
    if d['status']!='passed' or d['sources']!=sources():raise RuntimeError('wave source admission changed')
    for item in d['evidence']:
        if binding(item['path'])!=item:raise RuntimeError('wave evidence changed')


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['cpu','quality','admit']);p.add_argument('target')
    p.add_argument('--cpu');p.add_argument('--smoke',action='store_true');a=p.parse_args()
    if a.action=='cpu':cpu(a.target)
    elif a.action=='quality':quality(Path(a.target),a.smoke)
    else:admit(a.target,a.cpu)
