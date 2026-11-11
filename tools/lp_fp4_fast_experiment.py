"""Versioned development and admitted FP4 performance experiments (SPEC-0028)."""
import argparse
from fractions import Fraction as Q
import hashlib
import json
from pathlib import Path
import re
import subprocess
import shutil
import time
import numpy as np
from lp_fp4_fast_common import ROOT, BASE, put, load, ref, require
import lp_fp4_fast_prepare as fast
import lp_fp4_gpu_oracle as oracle

BINARY=ROOT/'research/lp-fp4-fast/target/release/lp-fp4-fast'
BACKENDS=('legacy','encode','prune','prepack','columns','shared','registers','quick')


def execute(directory,name,r,image,sanitizer=None):
    before=time.monotonic_ns();binary=isinstance(r['matrix'],np.ndarray)
    inp=directory/(name+('.input.bin' if binary else '.input.json'));out=directory/(name+'.output.json')
    if binary:fast.write_binary(inp,r)
    else:put(inp,r)
    serialization=time.monotonic_ns()-before
    executable=directory/"executor" if (directory/"executor").exists() else BINARY
    cmd=[str(executable),str(inp),str(image),str(out)]
    if sanitizer:cmd=['/usr/local/cuda/bin/compute-sanitizer','--tool',sanitizer,'--error-exitcode','86','--target-processes','all']+cmd
    start=time.monotonic_ns();p=subprocess.run(cmd,capture_output=True,text=True,timeout=120)
    elapsed=time.monotonic_ns()-start
    stdout=directory/(name+'.stdout');stderr=directory/(name+'.stderr')
    stdout.write_text(p.stdout);stderr.write_text(p.stderr)
    row=dict(id=name,input=ref(inp),elapsed_ns=elapsed,serialization_ns=serialization,returncode=p.returncode,stdout=ref(stdout),stderr=ref(stderr))
    if out.exists():row['output']=ref(out)
    put(directory/(name+'.attempt.json'),row)
    require(p.returncode==0,'worker failed: '+name)
    result=load(out)
    if sanitizer:
        pattern=r'RACECHECK SUMMARY: 0 hazards displayed \(0 errors, 0 warnings\)' if sanitizer=='racecheck' else r'ERROR SUMMARY: 0 errors'
        require(re.search(pattern,p.stdout+p.stderr) is not None,'sanitizer failed: '+name)
    return row,result


def differential(directory,image):
    rows=[]
    for f,k in oracle.LANES:
        for updates in (1,8,32):
            expected=None
            for backend in BACKENDS if f!=64 else ('legacy',):
                r=fast.request(1,f,k,backend,n=29,updates=updates,repetitions=2)
                name=f'{f}-{k}-{updates}-{backend}'
                row,out=execute(directory,name,r,image)
                require(out['status']=='completed','state refusal')
                state={x:out[x] for x in ('codes','exponents','state','observed_flags')}
                if expected is None:expected=state
                else:require(state==expected,'legacy state differs: '+name)
                row['bitwise_legacy_match']=True
                row['error']=oracle.observed_error(out['state'],oracle.reference(r,updates))
                row['samples']=out['samples'];rows.append(row)
                print(name,out['samples'][0]['cuda_ms'],flush=True)
    return rows


def primitives(directory,image):
    rows=[]
    for f,k in oracle.LANES:
        for trans in (False,True):
            for pattern in ('dense','tail','codebook','tiny','huge'):
                r=fast.request(1,f,k,'native_cached' if f==64 else 'hardware',n=29 if pattern=='tail' else 32)
                r['mode']='transpose' if trans else 'forward'
                v=[(i%15-7)/8 if i<r['n'] else 0. for i in range(32)]
                if pattern in ('codebook','tiny','huge'):
                    e=-48 if pattern=='tiny' else 48 if pattern=='huge' else 0
                    codes=[i if i!=8 else 0 for i in range(16)]
                    r['matrix']=[float(oracle.decode(codes[(i*13+j*7)%16],4)*Q(2)**e) for i in range(32) for j in range(32)]
                    v=[float(oracle.decode(codes[i%16],4)*Q(2)**e) for i in range(32)]
                    if f!=64:r['matrix_codes'],r['matrix_exponents']=fast.encode_batch(np.array(r['matrix']).reshape(1,1024),f,k)
                r['initial'][32 if trans else 64:64 if trans else 96]=v
                expected=oracle.product_reference(r)
                name=f'{f}-{k}-{r["mode"]}-{pattern}';row,out=execute(directory,name,r,image)
                require(out['status']=='completed','primitive refusal')
                error=max(abs(Q(a)-b) for a,b in zip(out['product'],expected));scale=max(Q(1,1<<96),max(map(abs,expected)))
                limit=scale*Q(1,1<<(38 if f in (4,64) else 19))
                require(error<=limit,'rational product mismatch: '+name)
                row.update(error=float(error),limit=float(limit));rows.append(row)
                print(name,'passed',flush=True)
    return rows


def transactions(directory,image):
    rows=[]
    for f,k in oracle.LANES:
        reference=None
        for variant in ('split','fused','persistent','roundtrip'):
            r=fast.request(1,f,k,'native_cached' if f==64 else 'hardware',n=29)
            r['variant']=variant;name=f'{f}-{k}-{variant}'
            row,out=execute(directory,name,r,image)
            require(out['status']=='completed' and out['physical_updates']==32,'transaction recurrence refusal')
            endpoint=[out[x] for x in ('state','codes','exponents')]
            if variant!='roundtrip':
                if reference is None:reference=endpoint
                else:require(endpoint==reference,'fusion changes state')
            rows.append(row)
        for scenario in ('pre_cancel','cancel','fault'):
            r=fast.request(1,f,k,'native_cached' if f==64 else 'hardware',n=29)
            r['cancel_after']=0 if scenario=='pre_cancel' else 8 if scenario=='cancel' else None
            r['inject_fault']=scenario=='fault'
            name=f'{f}-{k}-{scenario}';row,out=execute(directory,name,r,image)
            require(out['status']==('refused' if scenario=='fault' else 'cancelled') and out['state']==r['initial'],'transaction rollback')
            if scenario!='pre_cancel':require(out['rollback_exact'] and out['physical_updates']>0 and out['logical_updates']==0,'rollback accounting')
            rows.append(row)
    return rows


def sanitizer(directory,image,tool):
    rows=[]
    for f,k in oracle.LANES:
        for variant in ('split','fused','persistent','roundtrip'):
            r=fast.request(2,f,k,'native_cached' if f==64 else 'hardware',n=29,repetitions=2)
            r['variant']=variant
            name=f'{f}-{k}-{variant}';row,out=execute(directory,name,r,image,tool)
            require(out['status']=='completed','sanitizer recurrence refused');rows.append(row)
            print(tool,name,'passed',flush=True)
    return rows


def explore(directory,image):
    rows=[]
    for blocks in (1,64,512,4096):
        for f,k in oracle.LANES:
            for backend in ('legacy','columns') if f!=64 else ('legacy',):
                before=time.monotonic_ns();r=fast.request(blocks,f,k,backend,repetitions=7)
                preparation=time.monotonic_ns()-before
                name=f'{blocks}-{f}-{k}-{backend}';row,out=execute(directory,name,r,image)
                require(out['status']=='completed','profile refusal')
                row.update(blocks=blocks,format=f,components=k,backend=backend,preparation_ns=preparation,samples=out['samples'],counts=out['counts'])
                rows.append(row);print(name,'median ms',float(np.median([s['cuda_ms'] for s in out['samples']])),flush=True)
    return rows


def scaling(directory,image):
    rows=[]
    for blocks in (1,64,512,4096):
        for f,k in oracle.LANES:
            expected=None
            backends=('legacy','columns','shared','registers','quick') if f==4 else ('legacy','columns','registers') if f!=64 else ('legacy',)
            for backend in backends:
                before=time.monotonic_ns();r=fast.request(blocks,f,k,backend,repetitions=7)
                preparation=time.monotonic_ns()-before
                name=f'{blocks}-{f}-{k}-{backend}';row,out=execute(directory,name,r,image)
                require(out['status']=='completed','scaling refusal')
                endpoint=[out[x] for x in ('state','codes','exponents','observed_flags')]
                if expected is None:expected=endpoint
                else:require(endpoint==expected,'scaling state differs: '+name)
                row.update(blocks=blocks,format=f,components=k,backend=backend,preparation_ns=preparation,samples=out['samples'],counts=out['counts'])
                rows.append(row);print(name,'median ms',float(np.median([s['cuda_ms'] for s in out['samples']])),flush=True)
    return rows


def diagnostics(directory,image):
    rows=[]
    for blocks in (1,64,4096):
        for f,k in oracle.LANES:
            backends=('legacy','native_cached') if f==64 else ('quick','timers') if f==4 else ('columns',)
            expected=None
            for backend in backends:
                r=fast.request(blocks,f,k,backend,repetitions=3,arrays=True)
                name=f'{blocks}-{f}-{k}-{backend}';row,out=execute(directory,name,r,image)
                require(out['status']=='completed','diagnostic refusal')
                endpoint=[out[x] for x in ('state','codes','exponents','observed_flags')]
                if expected is None:expected=endpoint
                else:require(endpoint==expected,'instrumentation or native caching changed state')
                row.update(samples=out['samples'],phase_cycles=out['phase_cycles'],counts=out['counts'])
                rows.append(row)
                print(name,'median ms',float(np.median([s['cuda_ms'] for s in out['samples']])),
                      'cycles',np.mean(out['phase_cycles'],axis=0).tolist() if out['phase_cycles'] else [],flush=True)
    return rows


def hardware(directory,image):
    rows=[]
    for blocks in (1,64,512,4096):
        for f,k in oracle.LANES:
            expected=None
            backends=('legacy','native_cached') if f==64 else ('legacy','quick','hardware')
            for backend in backends:
                r=fast.request(blocks,f,k,backend,repetitions=7,arrays=True)
                name=f'{blocks}-{f}-{k}-{backend}';row,out=execute(directory,name,r,image)
                require(out['status']=='completed','hardware path refusal')
                endpoint=[out[x] for x in ('state','codes','exponents','observed_flags')]
                if expected is None:expected=endpoint
                else:require(endpoint==expected,'hardware encoding changed endpoint: '+name)
                row.update(samples=out['samples'],counts=out['counts'])
                rows.append(row);print(name,'median ms',float(np.median([s['cuda_ms'] for s in out['samples']])),flush=True)
    return rows


def stress(directory,image):
    rows=[];rng=np.random.default_rng(120412)
    for f,k in oracle.LANES:
        for updates in (0,1,8,32):
            r=fast.request(17,f,k,'legacy',updates=updates,arrays=True,repetitions=2)
            # Non-dyadic-looking binary64 coefficients keep all FP4 planes active.
            a=rng.uniform(-.06,.06,(17,32,32))+np.eye(32)[None,:,:]*.5
            r['matrix']=a.reshape(-1)
            target=np.array([(j%5-2)/4 for j in range(32)])
            r['cb'].reshape(17,64)[:,32:]=(a*target).sum(axis=2)
            r['initial']=rng.uniform(-.25,.25,17*96)
            if f!=64:r['matrix_codes'],r['matrix_exponents']=fast.encode_batch(a.reshape(17,1024),f,k,arrays=True)
            expected=None
            for backend in ('legacy','native_cached') if f==64 else ('legacy','hardware'):
                r['backend']=backend;name=f'{f}-{k}-{updates}-{backend}'
                row,out=execute(directory,name,r,image)
                require(out['status']=='completed','random dense trajectory refusal')
                endpoint=[out[x] for x in ('state','codes','exponents','observed_flags')]
                if expected is None:expected=endpoint
                else:require(endpoint==expected,'random dense endpoint mismatch: '+name)
                row['error']=oracle.observed_error(out['state'],oracle.reference(r,updates));rows.append(row)
                print(name,'passed',flush=True)
    mid=np.concatenate([fast.FP4_MID,-fast.FP4_MID])
    values=np.concatenate([mid,np.nextafter(mid,-np.inf),np.nextafter(mid,np.inf)])
    values=np.resize(values,96)
    for k in (2,4,8):
        for e in (-48,-1,0,48):
            r=fast.request(1,4,k,'legacy',updates=0,arrays=True)
            r['initial']=np.ldexp(values,e)
            r['initial'].reshape(3,32)[:,31]=np.ldexp(6.,e)
            expected=None
            for backend in ('legacy','hardware'):
                r['backend']=backend;name=f'ties-{k}-{e}-{backend}'
                row,out=execute(directory,name,r,image)
                require(out['status']=='completed','boundary encoding refusal')
                endpoint=[out[x] for x in ('state','codes','exponents')]
                if expected is None:expected=endpoint
                else:require(endpoint==expected,'midpoint mismatch: '+name)
                rows.append(row)
    return rows


def main():
    p=argparse.ArgumentParser();p.add_argument('stage',choices=['differential','primitives','transactions','memcheck','racecheck','initcheck','synccheck','explore','scaling','diagnostics','hardware','stress']);p.add_argument('version');p.add_argument('--build',default='v1');args=p.parse_args()
    image=BASE/('build-'+args.build)/'fast.cubin'
    directory=BASE/(args.stage+'-'+args.version);directory.mkdir(exist_ok=False)
    shutil.copyfile(BINARY,directory/'executor');(directory/'executor').chmod(0o755)
    put(directory/'manifest.json',dict(image=ref(image),binary=ref(directory/'executor'),driver=ref(Path(__file__)),stage=args.stage,exploratory=True))
    rows=sanitizer(directory,image,args.stage) if args.stage in ('memcheck','racecheck','initcheck','synccheck') else globals()[args.stage](directory,image)
    put(directory/'result.json',dict(status='passed',rows=rows,certified=False))
    print(len(rows),'passed',flush=True)

if __name__=='__main__':main()
