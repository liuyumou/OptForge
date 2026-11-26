"""Additive source-bound CPU/GPU admission and sanitizer checks."""
import argparse
from pathlib import Path
import subprocess
import sys
import numpy as np
from scipy import sparse
from lp_sp_pricing_budget import ROOT,BASE,binding,put
from lp_sp_pricing_gpu_opt_compare import read,verify
from lp_sp_pricing_transform_admit import validate as previous
from lp_sp_pricing_geometry_run import load
from sp_pricing.primal_recovery import LIBRARY,row_proposal,build
from lp_sp_pricing_primal_proof import verify_arrays

def sources():
    names=['research/lp-sp-pricing/native/wide_recovery.cu','research/lp-sp-pricing/python/sp_pricing/primal_recovery.py',
        'tools/lp_sp_pricing_primal_proof.py','tools/lp_sp_pricing_recovery_run.py','tools/lp_sp_pricing_recovery_endpoint.py',
        'tools/lp_sp_pricing_recovery_admit.py','tests/integration/test_lp_sp_pricing_primal_recovery.py']
    return [binding(ROOT/p) for p in names]+[binding(LIBRARY)]

def compile_native(identity):
    previous();out=BASE/identity;out.mkdir(exist_ok=False)
    cmd=['/usr/local/cuda/bin/nvcc','-std=c++17','-O3','-lineinfo','-Xcompiler','-fPIC','-shared','-gencode','arch=compute_120,code=sm_120',
        '--cudart','shared','-Xlinker','-rpath=/usr/local/cuda/lib64',str(ROOT/'research/lp-sp-pricing/native/wide_recovery.cu'),'-lcublas','-lcusolver','-o',str(LIBRARY)]
    subprocess.run(cmd,check=True);put(out/'result.json',dict(status='built',command=cmd,binary=binding(LIBRARY)))

def cpu(identity):
    previous();out=BASE/identity;out.mkdir(exist_ok=False)
    for p in sources():
        if p['path'].endswith('.py'):compile(Path(p['path']).read_text(),p['path'],'exec')
    subprocess.run([sys.executable,'-B','-m','unittest','discover','-s','tests/integration','-p','test_lp_sp_pricing_primal_recovery.py','-v'],cwd=ROOT,check=True)
    put(out/'result.json',dict(status='passed',sources=sources(),tests=8))

def quality(output,smoke):
    records=[]
    for m,n in ([(1,3),(7,19)] if smoke else [(1,3),(7,19),(17,49),(65,131)]):
        rng=np.random.default_rng(126071+m);a=rng.integers(-7,8,size=(m,n)).astype(float)/8;a[:,:m]+=np.eye(m)*3
        x=rng.integers(-8,9,size=n)/8;y=rng.integers(1,8,size=m)/128;b=a@x;c=a.T@y;a=sparse.csr_matrix(a)
        xc,yc,_=row_proposal(a,b,c,False);xg,yg,_=row_proposal(a,b,c,True)
        if not np.allclose(xc,xg,rtol=1e-9,atol=1e-10) or not np.allclose(yc,yg,rtol=1e-9,atol=1e-10):raise ArithmeticError('CPU/GPU row recovery disagreement')
        cert,detail=build(a,b,c,xg,yg);proof=verify_arrays(a.indptr,a.indices,a.data,b,c,cert['x0'],cert['y'],cert['columns'],cert['inverse'])
        if not proof['accepted']:raise ArithmeticError('GPU proposal fails independent exact proof')
        records.append(dict(m=m,n=n,x_error=float(np.max(np.abs(xc-xg))),y_error=float(np.max(np.abs(yc-yg))),construction=detail,proof=proof))
    try:row_proposal(sparse.csr_matrix((3,7)),np.ones(3),np.ones(7),True)
    except ArithmeticError:records.append(dict(singular_factor_rejected=True))
    else:raise ArithmeticError('singular GPU factor accepted')
    put(output,dict(status='passed',records=records,sources=sources()))

def gpu(identity,cpu_identity):
    previous();prior=BASE/cpu_identity/'result.json'
    if read(prior)['sources']!=sources() or read(BASE/'resources'/f'{cpu_identity}.settlement.json')['status']!='passed':raise RuntimeError('CPU admission changed')
    out=BASE/identity;out.mkdir(exist_ok=False);quality(out/'quality.json',False);evidence=[binding(prior),binding(out/'quality.json')]
    for name in ('memcheck','racecheck','initcheck','synccheck'):
        with (out/(name+'.log')).open('x') as stream:subprocess.run(['/usr/local/cuda/bin/compute-sanitizer','--tool',name,'--target-processes','all','--error-exitcode','91',sys.executable,'-B',__file__,'quality',str(out/(name+'.json')),'--smoke'],stdout=stream,stderr=subprocess.STDOUT,check=True)
        evidence.extend([binding(out/(name+'.log')),binding(out/(name+'.json'))])
    put(out/'admission.json',dict(status='passed',sources=sources(),evidence=evidence))

def validate():
    previous();path=BASE/'recovery-gpu-admit-v1/admission.json';d=read(path)
    if d['sources']!=sources() or read(BASE/'resources/recovery-gpu-admit-v1.settlement.json')['status']!='passed':raise RuntimeError('recovery admission')
    for item in d['evidence']:verify(item)
    return binding(path)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['build','cpu','gpu','quality']);p.add_argument('identity');p.add_argument('--cpu-identity');p.add_argument('--smoke',action='store_true');a=p.parse_args()
    if a.action=='build':compile_native(a.identity)
    elif a.action=='cpu':cpu(a.identity)
    elif a.action=='gpu':gpu(a.identity,a.cpu_identity)
    else:quality(Path(a.identity),a.smoke)
