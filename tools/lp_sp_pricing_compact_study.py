"""Build and source-bound admission for the opt-in compact storage path."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
import shutil
from fractions import Fraction as Q
from types import SimpleNamespace
import numpy as np
from lp_sp_pricing_budget import ROOT,BASE,binding,put

CRATE=ROOT/'research/lp-sp-pricing'
sys.path.insert(0,str(CRATE/'python'))


def sources():
    paths=list((CRATE/'python/sp_pricing').glob('compact_*.py'))+list((CRATE/'native').glob('compact_*.*'))
    paths += [CRATE/'target/release/libsp_compact.so',CRATE/'target/cpu/libsp_compact_proof.so',
              ROOT/'tests/integration/test_lp_sp_pricing_compact.py',Path(__file__).resolve()]
    return [binding(p) for p in sorted(paths)]


def build(identity):
    out=BASE/identity;out.mkdir(exist_ok=False)
    cpu=CRATE/'target/cpu/libsp_compact_proof.so';gpu=CRATE/'target/release/libsp_compact.so'
    for library in (cpu,gpu):
        if library.exists():shutil.copyfile(library,out/('preceding-'+library.name))
    commands=[['g++','-std=c++17','-O3','-fPIC','-shared','-ffp-contract=off','-fno-fast-math','-frounding-math',
        str(CRATE/'native/compact_proof.cpp'),'-o',str(cpu)],
        ['/usr/local/cuda/bin/nvcc','-std=c++17','-O3','--fmad=false','-Xcompiler','-fPIC','-shared',
        '-gencode','arch=compute_120,code=sm_120','--cudart','shared','-Xlinker','-rpath=/usr/local/cuda/lib64',
        str(CRATE/'native/compact_tiles.cu'),'-o',str(gpu)]]
    for cmd in commands:subprocess.run(cmd,check=True)
    for library in (cpu,gpu):shutil.copyfile(library,out/library.name)
    put(out/'build.json',dict(commands=commands,sources=sources(),retained=[binding(out/p.name) for p in (cpu,gpu)]))


def cpu(identity):
    build(identity)
    binary=BASE/identity/'proof-sanitized'
    subprocess.run(['g++','-std=c++17','-O1','-g','-ffp-contract=off','-fno-fast-math','-frounding-math',
        '-fsanitize=address,undefined','-fno-omit-frame-pointer',str(CRATE/'native/compact_proof.cpp'),
        str(CRATE/'native/compact_proof_test.cpp'),'-o',str(binary)],check=True)
    with (BASE/identity/'sanitizer.log').open('x') as stream:
        subprocess.run([str(binary)],stdout=stream,stderr=subprocess.STDOUT,check=True)
    subprocess.run([sys.executable,'-B','-m','unittest','discover','-s','tests/integration',
        '-p','test_lp_sp_pricing_compact.py','-v'],cwd=ROOT,check=True)
    put(BASE/identity/'result.json',dict(status='passed',sources=sources(),tests=11,
        sanitizer_cases=64,sanitizers=['ASan','UBSan'],sanitizer_log=binding(BASE/identity/'sanitizer.log')))


def quality(path,smoke=False):
    from sp_pricing.compact_basis import Rows,TileSource
    from sp_pricing.compact_geometry import CompactOracle
    from sp_pricing.compact_gpu import TileEngine,TileProof,exact_labels,proposals
    from sp_pricing.gpu_wave import WaveEngine,PackedBasis
    from sp_pricing.exact import Work
    from lp_sp_pricing_gpu_opt_quality import scalar_pdhg
    records=[];proofs=0
    rng=np.random.default_rng(121971)
    for r in (7,33):
        s=2*r;b=[[Q(int(v),16) for v in row] for row in rng.integers(-4,5,size=(r,s))]
        o=CompactOracle(Rows.dense(b),4,Q(1,65536),Work(seconds=180,max_operations=1000000000))
        old=SimpleNamespace(b=b,r=r,n=r,h=o.h,epsilon=o.epsilon)
        for sparse in (False,True):
            for cached in (False,True):
                for width in ([3] if smoke else [1,3,16]):
                    steps=3 if smoke else 17;slots=[i%s for i in range(width)]
                    source=TileSource(o.matrix,8,16,cache_bytes=16384)
                    with TileEngine(source,width,4<<20 if cached else 0,sparse) as engine,TileProof(o,source) as checker:
                        x,u,profile=engine.propose(slots,o.h,o.epsilon,steps)
                        labels,stats=checker.batch(slots,x,u)
                        reference={}
                        for q,slot in enumerate(slots):
                            if slot//2 in reference:continue
                            reference.update(exact_labels(o,slot//2,x[q],u[q]));proofs+=1
                        if any(reference.get(i)!=v for i,v in labels.items()):raise RuntimeError('tiled exact decisions differ')
                        if not smoke:
                            with WaveEngine() as previous:
                                previous.load(old,slots,PackedBasis(old),sparse);previous.advance(steps,[1]*width)
                                xp=np.ctypeslib.as_array(previous.x,shape=(width*r,)).reshape(x.shape)
                                up=np.ctypeslib.as_array(previous.u,shape=(width*s,)).reshape(u.shape)
                                error=max(float(np.max(np.abs(x-xp)/(1+np.abs(xp)))),float(np.max(np.abs(u-up)/(1+np.abs(up)))))
                            if error>1e-12:raise RuntimeError('whole-state tiled differential failed')
                            sx,su=scalar_pdhg(b,slots[0],o.h,o.epsilon,steps)
                            if max(abs(a-b)/(1+abs(b)) for a,b in zip([*x[0],*u[0]],[*sx,*su]))>1e-10:
                                raise RuntimeError('independent scalar equations differ')
                        else:error=None
                        records.append(dict(r=r,s=s,sparse=sparse,cached=cached,width=width,
                            normalized_error=error,labels=len(labels),proof=stats,profile=profile))
    if not smoke:
        b=Rows([{2*i+1:Q(1)} for i in range(40)],80)
        results=[]
        for pipeline in (False,True):
            o=CompactOracle(b,4,Q(1,65536),Work(seconds=60,max_operations=100000000),isotropic_error=0)
            labels,metadata=proposals(o,width=8,steps=16,pipeline=pipeline,device_cache_bytes=1<<20)
            if labels!={i:1 for i in range(40)} or o._a is not None:raise RuntimeError('bounded pipeline did not resolve diagonal case')
            results.append(metadata)
    else:results=[]
    put(path,dict(status='passed',configurations=len(records),exact_proposals=proofs,rows=records,
        pipeline=results,sources=sources()))
    print(json.dumps(dict(status='passed',configurations=len(records),exact_proposals=proofs)),flush=True)


def admit(identity,cpu_identity):
    cpu_path=BASE/cpu_identity/'result.json';cpu_data=json.loads(cpu_path.read_text())
    if cpu_data['status']!='passed' or cpu_data['sources']!=sources():raise RuntimeError('CPU admission changed')
    if json.loads((BASE/'resources'/f'{cpu_identity}.settlement.json').read_text())['status']!='passed':raise RuntimeError('CPU reservation failed')
    out=BASE/identity;out.mkdir(exist_ok=False);quality(out/'quality.json')
    evidence=[binding(cpu_path),binding(out/'quality.json')]
    for name in ['memcheck','racecheck','initcheck','synccheck']:
        with (out/(name+'.log')).open('x') as stream:
            subprocess.run(['/usr/local/cuda/bin/compute-sanitizer','--tool',name,'--target-processes','all',
                '--error-exitcode','91',sys.executable,'-B',__file__,'quality',str(out/(name+'.json')),'--smoke'],
                stdout=stream,stderr=subprocess.STDOUT,check=True)
        evidence.extend(binding(out/(name+ext)) for ext in ('.json','.log'))
    put(out/'admission.json',dict(status='passed',sources=sources(),evidence=evidence))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['build','cpu','quality','admit']);p.add_argument('identity')
    p.add_argument('--cpu');p.add_argument('--smoke',action='store_true');a=p.parse_args()
    if a.action=='build':build(a.identity)
    elif a.action=='cpu':cpu(a.identity)
    elif a.action=='quality':quality(Path(a.identity),a.smoke)
    else:admit(a.identity,a.cpu)
