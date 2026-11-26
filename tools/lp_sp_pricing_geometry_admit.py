"""Build, differential admission and bounded exact geometry diagnostics."""
import argparse
from fractions import Fraction as Q
import json
from pathlib import Path
import subprocess
import sys
import time
import numpy as np
from lp_sp_pricing_budget import ROOT,BASE,put,binding
from lp_sp_pricing_gpu_opt_compare import read,verify
CRATE=ROOT/'research/lp-sp-pricing';sys.path.insert(0,str(CRATE/'python'))

def sources():
 paths=list((CRATE/'native').glob('geometry_*.*'))+[CRATE/'python/sp_pricing/geometry_fast.py',
  CRATE/'target/cpu/libsp_geometry_exact.so',CRATE/'target/release/libsp_geometry_rank.so',
  ROOT/'tools/lp_sp_pricing_geometry_run.py',ROOT/'tests/integration/test_lp_sp_pricing_geometry.py',Path(__file__).resolve()]
 return [binding(p) for p in sorted(paths)]

def cpu(identity):
 out=BASE/identity;out.mkdir(exist_ok=False)
 gmp='/usr/lib/x86_64-linux-gnu/libgmp.so.10.4.1'
 commands=[['g++','-std=c++17','-O3','-fPIC','-shared',str(CRATE/'native/geometry_exact.cpp'),gmp,'-o',str(CRATE/'target/cpu/libsp_geometry_exact.so')],
 ['/usr/local/cuda/bin/nvcc','-std=c++17','-O3','-Xcompiler','-fPIC','-shared','-gencode','arch=compute_120,code=sm_120',
 '--cudart','shared','-Xlinker','-rpath=/usr/local/cuda/lib64',str(CRATE/'native/geometry_rank.cu'),'-o',str(CRATE/'target/release/libsp_geometry_rank.so')]]
 for cmd in commands:subprocess.run(cmd,check=True)
 for name in ['target/cpu/libsp_geometry_exact.so','target/release/libsp_geometry_rank.so']:
  (out/Path(name).name).write_bytes((CRATE/name).read_bytes())
 binary=out/'sanitized'
 subprocess.run(['g++','-std=c++17','-O1','-g','-fsanitize=address,undefined','-fno-omit-frame-pointer',
  str(CRATE/'native/geometry_exact.cpp'),str(CRATE/'native/geometry_exact_test.cpp'),gmp,'-o',str(binary)],check=True)
 with (out/'sanitizer.log').open('x') as stream:subprocess.run([str(binary)],stdout=stream,stderr=subprocess.STDOUT,check=True)
 subprocess.run([sys.executable,'-B','-m','unittest','discover','-s','tests/integration','-p','test_lp_sp_pricing_geometry.py','-v'],cwd=ROOT,check=True)
 put(out/'result.json',dict(status='passed',tests=8,sources=sources(),gmp=binding(gmp),sanitizer=binding(out/'sanitizer.log'),commands=commands))

def quality(path,smoke=False):
 from sp_pricing.geometry_fast import rank_proof
 from sp_pricing.compact_basis import Rows
 from sp_pricing.exact import Work
 records=[]
 for n in ([7,33] if smoke else [1,7,33,65,129]):
  for deficient in (False,True):
   rng=np.random.default_rng(122119+n);a=rng.integers(-7,8,size=(n+2,n)).tolist()
   if not deficient:
    for i in range(n):a[i][i]+=100
   else:
    for row in a:row[-1]=0
   source=Rows.dense(a);outcomes=[]
   for gpu in (False,True):
    proved,info=rank_proof(source.rows,n,Work(seconds=30,max_operations=100000000),gpu);outcomes.append((proved,info))
   if outcomes[0][0]!=outcomes[1][0] or outcomes[0][1]['rank']!=outcomes[1][1]['rank']:raise ArithmeticError('CPU/GPU modular rank mismatch')
   records.append(dict(n=n,deficient=deficient,cpu=outcomes[0],gpu=outcomes[1]))
 put(path,dict(status='passed',rows=records,sources=sources()))

def gpu(identity,cpu_identity):
 gate=BASE/cpu_identity/'result.json';d=read(gate)
 if d['status']!='passed' or d['sources']!=sources():raise RuntimeError('CPU source admission')
 if read(BASE/'resources'/f'{cpu_identity}.settlement.json')['status']!='passed':raise RuntimeError('CPU supervision')
 out=BASE/identity;out.mkdir(exist_ok=False);quality(out/'quality.json');evidence=[binding(gate),binding(out/'quality.json')]
 for name in ['memcheck','racecheck','initcheck','synccheck']:
  with (out/(name+'.log')).open('x') as stream:
   subprocess.run(['/usr/local/cuda/bin/compute-sanitizer','--tool',name,'--target-processes','all','--error-exitcode','91',
    sys.executable,'-B',__file__,'quality',str(out/(name+'.json')),'--smoke'],stdout=stream,stderr=subprocess.STDOUT,check=True)
  evidence.extend(binding(out/(name+ext)) for ext in ('.json','.log'))
 put(out/'admission.json',dict(status='passed',sources=sources(),evidence=evidence))

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('action',choices=['cpu','gpu','quality']);p.add_argument('identity');p.add_argument('--cpu-identity');p.add_argument('--smoke',action='store_true');a=p.parse_args()
 if a.action=='cpu':cpu(a.identity)
 elif a.action=='gpu':gpu(a.identity,a.cpu_identity)
 else:quality(Path(a.identity),a.smoke)
