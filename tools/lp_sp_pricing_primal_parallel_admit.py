"""CPU-only proof admission and cold serial/parallel timing on retained endpoints."""
import argparse
import subprocess
import sys
import time
from pathlib import Path
from lp_sp_pricing_budget import ROOT,BASE,binding,put
from lp_sp_pricing_gpu_opt_compare import read,verify
from lp_sp_pricing_recovery_fast_admit import validate as previous
from lp_sp_pricing_baselines import PYTHON

OUT=BASE/'primal-parallel-cpu-v1'

def sources():
    return [binding(ROOT/'tools/lp_sp_pricing_primal_parallel_proof.py'),binding(__file__),binding(ROOT/'tests/integration/test_lp_sp_pricing_primal_parallel.py')]

def cpu():
    prior=previous();OUT.mkdir(exist_ok=False)
    subprocess.run([sys.executable,'-B','-m','unittest','discover','-s','tests/integration','-p','test_lp_sp_pricing_primal*.py','-v'],cwd=ROOT,check=True)
    rows=[]
    for i,family in enumerate(('dense-wide-1m','dense-wide-4m','sparse-wide-1m')):
        base=BASE/'recovery-development-v2';model=base/'models'/family/'portable.json';cert=base/'runs'/(family+'-candidate-cpu')/'postprocess/response.json'
        for lane in (('serial','parallel') if i%2==0 else ('parallel','serial')):
            dest=OUT/(family+'-'+lane);dest.mkdir();script='lp_sp_pricing_primal_proof.py' if lane=='serial' else 'lp_sp_pricing_primal_parallel_proof.py';start=time.perf_counter_ns()
            with (dest/'stdout').open('x') as out,(dest/'stderr').open('x') as err:subprocess.run([str(PYTHON),'-B',str(ROOT/'tools'/script),str(model),str(cert),str(dest/'proof.json')],stdout=out,stderr=err,check=True,timeout=120)
            elapsed=time.perf_counter_ns()-start;proof=read(dest/'proof.json')
            if not proof['accepted']:raise ArithmeticError('large retained proof rejected')
            rows.append(dict(family=family,lane=lane,cold_process_ns=elapsed,proof=binding(dest/'proof.json'),model=binding(model),certificate=binding(cert)))
    put(OUT/'result.json',dict(status='passed',sources=sources(),previous=prior,tests=14,rows=rows,
        scope='CPU checking of retained development endpoints only; no LP solve repeated, no historical certification time replaced.'))

def validate():
    previous();path=OUT/'result.json';d=read(path)
    if d['sources']!=sources() or read(BASE/'resources/primal-parallel-cpu-v1.settlement.json')['status']!='passed':raise RuntimeError('parallel primal admission')
    verify(d['previous']);return binding(path)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['cpu']);p.parse_args();cpu()
