"""Separate source admission for the precomputed projection variant."""
import argparse
from pathlib import Path
import subprocess
import sys
from unittest.mock import patch
from lp_sp_pricing_budget import ROOT,BASE,binding,put
from lp_sp_pricing_gpu_opt_compare import read,verify
from lp_sp_pricing_factor_admit import validate as previous,quality as base_quality
from lp_sp_pricing_transform_run import LIBRARY
from sp_pricing import factor_projection


def sources():
    return [binding(p) for p in [ROOT/'research/lp-sp-pricing/native/factor_transform.cu',LIBRARY,
        ROOT/'tools/lp_sp_pricing_transform_run.py',Path(__file__).resolve(),
        ROOT/'tools/lp_sp_pricing_transform_endpoint.py',ROOT/'tools/lp_sp_pricing_factor_parallel_proof.py',
        ROOT/'tests/integration/test_lp_sp_pricing_factor_extended.py']]


def build(identity):
    previous();out=BASE/identity;out.mkdir(exist_ok=False)
    cmd=['/usr/local/cuda/bin/nvcc','-std=c++17','-O3','-lineinfo','-Xcompiler','-fPIC','-shared',
         '-gencode','arch=compute_120,code=sm_120','--cudart','shared','-Xlinker','-rpath=/usr/local/cuda/lib64',
         str(ROOT/'research/lp-sp-pricing/native/factor_transform.cu'),'-lcublas','-lcusolver','-o',str(LIBRARY)]
    subprocess.run(cmd,check=True);put(out/'result.json',dict(status='built',command=cmd,binary=binding(LIBRARY)))


def cpu(identity):
    previous();out=BASE/identity;out.mkdir(exist_ok=False)
    subprocess.run([sys.executable,'-B','-m','unittest','discover','-s','tests/integration','-p','test_lp_sp_pricing_factor*.py','-v'],cwd=ROOT,check=True)
    put(out/'result.json',dict(status='passed',sources=sources()))


def quality(output,smoke):
    with patch.object(factor_projection,'LIBRARY',LIBRARY):base_quality(Path(output),smoke)


def gpu(identity):
    previous();prior=BASE/'transform-cpu-admit-v1/result.json'
    if read(prior)['sources']!=sources() or read(BASE/'resources/transform-cpu-admit-v1.settlement.json')['status']!='passed':raise RuntimeError('CPU admission')
    out=BASE/identity;out.mkdir(exist_ok=False);quality(out/'quality.json',False);evidence=[binding(prior),binding(out/'quality.json')]
    for name in ('memcheck','racecheck','initcheck','synccheck'):
        with (out/(name+'.log')).open('x') as stream:
            subprocess.run(['/usr/local/cuda/bin/compute-sanitizer','--tool',name,'--target-processes','all','--error-exitcode','91',
                sys.executable,'-B',__file__,'quality',str(out/(name+'.json')),'--smoke'],stdout=stream,stderr=subprocess.STDOUT,check=True)
        evidence.extend([binding(out/(name+'.log')),binding(out/(name+'.json'))])
    put(out/'admission.json',dict(status='passed',sources=sources(),evidence=evidence))


def validate():
    previous();path=BASE/'transform-gpu-admit-v1/admission.json';d=read(path)
    if d['sources']!=sources() or read(BASE/'resources/transform-gpu-admit-v1.settlement.json')['status']!='passed':raise RuntimeError('GPU admission')
    for item in d['evidence']:verify(item)
    return binding(path)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['build','cpu','gpu','quality']);p.add_argument('identity');p.add_argument('--smoke',action='store_true');a=p.parse_args()
    if a.action=='build':build(a.identity)
    elif a.action=='cpu':cpu(a.identity)
    elif a.action=='gpu':gpu(a.identity)
    else:quality(a.identity,a.smoke)
