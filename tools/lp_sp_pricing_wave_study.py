"""Isolated preparation/checking/synchronous-search follow-up; no historical retries."""
import argparse
import ctypes as C
import json
from pathlib import Path
import shutil
import subprocess
import sys
import time

from lp_sp_pricing_budget import BASE,ROOT,binding,put

CRATE=ROOT/'research/lp-sp-pricing'
PYTHON=ROOT/'artifacts/gpup-copt-adapter-env/venv/bin/python'
NVCC='/usr/local/cuda/bin/nvcc'
OLD=CRATE/'target/release/libsp_batch_optimized.so'


def prepare(identity):
    out=BASE/identity;out.mkdir(exist_ok=False)
    paths=[p for p in CRATE.rglob('*') if p.is_file() and 'target' not in p.parts and '__pycache__' not in p.parts]
    paths+=list((ROOT/'tools').glob('lp_sp_pricing_*.py'))+list((ROOT/'tests/integration').glob('test_lp_sp_pricing*.py'))
    paths+=[OLD,CRATE/'target/cpu/libsp_proof.so',CRATE/'target/cpu/libsp_auxiliary.so',CRATE/'target/cpu/libsp_market.so']
    records=[]
    for p in paths:
        target=out/p.relative_to(ROOT);target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,target)
        records.append(dict(original=binding(p),retained=binding(target)))
    put(out/'baseline.json',dict(sources=records,preceding_checkpoint=binding(ROOT/'docs/benchmarks/lp-sp-pricing-gpu-checkpoint.json')))
    put(out/'plan.json',dict(authorization='user requests preparation/exact-check acceleration and synchronized auxiliary iteration',
        changes=['measure first-use CUDA separately from model preparation','native-architecture CUDA build',
                 'rigorous outward-rounded interval labels with exact GMP fallback',
                 'contiguous batched host checks without Python proposal copies',
                 'synchronous multi-RHS iteration sharing matrix coefficients across searches',
                 'persistent solve-scoped GPU session and compact native output'],
        evaluation='CPU differential/adversarial checks, CUDA scalar/differential/sanitizer admission, development then fresh frozen original-LP comparison including COPT',
        preserve='all prior sources, receipts, failures, original exact/1e-9 acceptance and current resource gates',
        allocation='unchanged 240000 CPU / 30000 GPU and original phase caps',
        comparison_note='COPT internal device initialization is inside its opaque solve call; no separately measured COPT device-preparation advantage is assumed'))
    commands=[];libraries=[]
    for name,extra in [('aot-static',['-gencode','arch=compute_120,code=sm_120']),
                       ('aot-shared',['-gencode','arch=compute_120,code=sm_120','--cudart','shared','-Xlinker','-rpath=/usr/local/cuda/lib64'])]:
        library=out/(name+'.so')
        command=[NVCC,'-std=c++17','-O3','--fmad=false','-Xcompiler','-fPIC','-shared',
                 str(CRATE/'native/batch_optimized.cu'),'-o',str(library),*extra]
        subprocess.run(command,check=True);commands.append(command);libraries.append(binding(library))
    info={}
    for name,p in [('old',OLD),('aot',out/'aot-static.so')]:
        info[name]=subprocess.check_output(['/usr/local/cuda/bin/cuobjdump','--list-elf',str(p)],text=True)
    put(out/'build.json',dict(commands=commands,libraries=libraries,architecture=info,
        source=binding(CRATE/'native/batch_optimized.cu')))
    print(json.dumps(dict(status='prepared',architecture=info)),flush=True)


def cold_child(library,explicit):
    sys.path.insert(0,str(CRATE/'python'))
    from sp_pricing.gpu import GpuBatch
    b=[[float(j==2*i+1) for j in range(34)] for i in range(17)]
    started=time.perf_counter_ns();runtime_init=0
    if explicit:
        runtime=C.CDLL('/usr/local/cuda/lib64/libcudart.so')
        runtime.cudaFree.argtypes=[C.c_void_p];runtime.cudaFree.restype=C.c_int
        before=time.perf_counter_ns();code=runtime.cudaFree(None);runtime_init=time.perf_counter_ns()-before
        if code:raise RuntimeError('CUDA initialization '+str(code))
    records=[]
    for repetition in range(2):
        before=time.perf_counter_ns()
        with GpuBatch(library,b,True) as engine:
            construction=time.perf_counter_ns()-before
            proposal=engine.propose([2*i+1 for i in range(17)]+[1]*15,4,1/65536,64,'fp64',True)
            if not all(abs(x[i]-2)<1e-12 for i,x in enumerate(proposal['x'][:17])):
                raise RuntimeError('preparation diagnostic numerical mismatch')
            records.append(dict(construction_ns=construction,preparation_ns=engine.preparation_ns,
                device_ms=proposal['device_iteration_ms'],proposal_ns=proposal['elapsed_ns']))
    print(json.dumps(dict(explicit_initialization=explicit,runtime_initialization_ns=runtime_init,
        complete_ns=time.perf_counter_ns()-started,records=records)),flush=True)


def diagnose(identity,prepared):
    out=BASE/identity;out.mkdir(exist_ok=False);rows=[]
    for repetition in range(3):
        lanes=[('old',OLD),('aot-static',prepared/'aot-static.so'),('aot-shared',prepared/'aot-shared.so')]
        lanes=lanes[repetition:]+lanes[:repetition]
        for name,path in lanes:
            for explicit in (False,True):
                cmd=[str(PYTHON),'-B',__file__,'cold-child',str(path)]
                if explicit:cmd.append('--explicit')
                result=subprocess.run(cmd,check=True,capture_output=True,text=True,timeout=20)
                row=json.loads(result.stdout);row.update(lane=name,repetition=repetition,library=binding(path))
                rows.append(row);print(json.dumps(row),flush=True)
    put(out/'result.json',dict(status='passed',rows=rows,prepared=binding(prepared/'build.json')))


def build(identity):
    out=BASE/identity;out.mkdir(exist_ok=False)
    gpu=CRATE/'target/release/libsp_wave.so';cpu=CRATE/'target/cpu/libsp_interval.so'
    preceding=[]
    for p in (gpu,cpu):
        if p.exists():
            dest=out/('preceding-'+p.name);shutil.copyfile(p,dest);preceding.append(binding(dest))
    commands=[['g++','-std=c++17','-O3','-fPIC','-shared','-ffp-contract=off','-fno-fast-math','-frounding-math',
        str(CRATE/'native/proof_interval.cpp'),'-o',str(cpu)],
        [NVCC,'-std=c++17','-O3','--fmad=false','-Xcompiler','-fPIC','-shared',
        '-gencode','arch=compute_120,code=sm_120','--cudart','shared','-Xlinker','-rpath=/usr/local/cuda/lib64',
        str(CRATE/'native/batch_wave.cu'),'-o',str(gpu)]]
    for command in commands:subprocess.run(command,check=True)
    retained=[]
    for p in (gpu,cpu):
        dest=out/p.name;shutil.copyfile(p,dest);retained.append(binding(dest))
    put(out/'build.json',dict(status='passed',commands=commands,preceding=preceding,libraries=[binding(cpu),binding(gpu)],
        retained_libraries=retained,sources=[binding(CRATE/'native'/n) for n in ('proof_interval.cpp','batch_wave.cu')]))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['prepare','diagnose','cold-child','build']);p.add_argument('target')
    p.add_argument('--prepared',type=Path);p.add_argument('--explicit',action='store_true');a=p.parse_args()
    if a.action=='prepare':prepare(a.target)
    elif a.action=='diagnose':diagnose(a.target,a.prepared.resolve())
    elif a.action=='build':build(a.target)
    else:cold_child(Path(a.target).resolve(),a.explicit)
