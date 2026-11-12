"""Explicitly released v2 packing recovery; v1 scientific evidence stays closed."""
import argparse
from copy import deepcopy
from fractions import Fraction as Q
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import time

from lp_fp4_gpu_common import BASE as PRIOR_BASE, ROOT, DEVICE, checked, load, put, ref, require
import lp_fp4_gpu_oracle as o

BASE=ROOT/'artifacts/gpup-fp4-gpu-pilot-v2'
BINARY=ROOT/'research/lp-fp4-gpu-pilot/target/release/lp-fp4-gpu-pilot'
IMAGE=PRIOR_BASE/'build-v2/pilot.cubin'
MANIFEST=BASE/'manifest.json'

def identity(name,bits,k,variant,rep):return f'{name}-{bits}-{k}-{variant}-r{rep}'

def cells():
    rows=[dict(id=identity(name,f,k,v,rep),workload=name,format=f,components=k,variant=v,repetition=rep)
          for name in o.WORKLOADS for rep in range(3) for f,k in o.LANES for v in o.VARIANTS]
    return sorted(rows,key=lambda r:hashlib.sha256(('17112:'+r['id']).encode()).digest())

def sources():
    paths=[ROOT/'research/lp-fp4-gpu-pilot/cuda/pilot_v2.cu',ROOT/'research/lp-fp4-gpu-pilot/Cargo.toml',ROOT/'research/lp-fp4-gpu-pilot/Cargo.lock']
    paths+=list((ROOT/'research/lp-fp4-gpu-pilot/src').glob('*.rs'))
    paths+=list((ROOT/'research/lp-tensor-expanded-device/cuda-sys').rglob('*.rs'))
    paths+=list((ROOT/'crates/optimizer-core/src').rglob('*.rs'))
    paths+=[ROOT/'crates/optimizer-core/Cargo.toml',ROOT/'research/lp-tensor-expanded-device/cuda-sys/Cargo.toml']
    paths+=list((ROOT/'tools').glob('lp_fp4_gpu_*.py'))
    paths+=[ROOT/f'tools/{p}' for p in ['setup_fp4_gpu_pilot.py','lp_fp4_contract.py','lp_fp4_reference_v2.py','lp_cpu_admission.py','lp_baseline_common.py','lp_baseline_contract.py','validate_artifacts.py']]
    paths+=[ROOT/'tests/integration/test_lp_fp4_gpu_pilot.py',ROOT/'docs/specifications/SPEC-0027-fp4-gpu-pilot.md',ROOT/'docs/decisions/ADR-0059-fp4-gpu-pilot.md']
    paths+=[ROOT/'tools/setup_fp4_gpu_pilot_v2.py',ROOT/'tests/integration/test_lp_fp4_gpu_packing_v2.py',ROOT/'docs/plans/lp-fp4-gpu-pilot-packing-recovery.md']
    return sorted(set(paths))

def freeze():
    completion=PRIOR_BASE/'resources/native-completion-v3.settlement.json'
    require(completion.exists() and load(completion)['status']=='passed','CPU/native completion required')
    require(hashlib.sha256((ROOT/'research/lp-fp4-gpu-pilot/cuda/pilot_v2.cu').read_bytes()).hexdigest()==load(PRIOR_BASE/'build-v2/receipt.json')['source_sha256'],'compiled source differs')
    release=PRIOR_BASE/'recovery-authorization-v2.json'
    require(release.exists() and load(release).get('explicit_user_release') is True,'explicit recovery release required')
    for name in ('packing-correction-cpu-v2','corrected-compile-v2'):
        require(load(PRIOR_BASE/('resources/'+name+'.settlement.json'))['status']=='passed','correction CPU acceptance')
    BASE.mkdir(exist_ok=False)
    root=BASE/'frozen';root.mkdir(exist_ok=False)
    refs=[]
    for path in sources():
        relative=path.relative_to(ROOT);dest=root/relative;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(path.read_bytes());refs.append(ref(path))
    inventory=subprocess.check_output(['nvidia-smi','--query-gpu=uuid,name,driver_version,memory.total,memory.used,utilization.gpu','--format=csv,noheader'],text=True)
    require(DEVICE in inventory,'device inventory missing')
    put(BASE/'inventory.json',dict(text=inventory,nvcc=subprocess.check_output(['/usr/local/cuda/bin/nvcc','--version'],text=True)))
    put(MANIFEST,dict(kind='fp4-gpu-pilot-v2',recovery_release=ref(release),prior_failed_manifest=ref(PRIOR_BASE/'manifest.json'),correction_test=ref(PRIOR_BASE/'resources/packing-correction-cpu-v2.settlement.json'),correction_build=ref(PRIOR_BASE/'resources/corrected-compile-v2.settlement.json'),sources=refs,binary=ref(BINARY),image=ref(IMAGE),build=ref(PRIOR_BASE/'build-v2/receipt.json'),ptx=ref(PRIOR_BASE/'build-v2/pilot.ptx'),sass=ref(PRIOR_BASE/'build-v2/pilot.sass'),inventory=ref(BASE/'inventory.json'),cpu_acceptance=ref(completion),kernel_path_bridge=ref(PRIOR_BASE/'kernel-path-bridge.json'),cells=cells(),device=DEVICE,certified=False))
    print('Frozen 216 profile cells and source/compiler/device identities.')

def verify():
    m=load(MANIFEST)
    for item in m['sources']+[m['binary'],m['image'],m['build'],m['ptx'],m['sass'],m['inventory'],m['cpu_acceptance'],m['kernel_path_bridge'],m['recovery_release'],m['prior_failed_manifest'],m['correction_test'],m['correction_build']]:checked(item)
    require(m['cells']==cells() and m['device']==DEVICE,'frozen protocol differs')
    require(os.environ.get('AI_OPTIMIZER_GPU_LEASE')=='inherited' and os.environ.get('CUDA_VISIBLE_DEVICES')==DEVICE,'shared lease required')
    return m

def execute(directory,name,request,sanitizer=None):
    input_path=directory/(name+'.input.json');output=directory/(name+'.output.json')
    put(input_path,request)
    command=[str(BINARY),str(input_path),str(IMAGE),str(output)]
    if sanitizer:command=['/usr/local/cuda/bin/compute-sanitizer','--tool',sanitizer,'--error-exitcode','86','--target-processes','all']+command
    start=time.monotonic_ns();completed=subprocess.run(command,capture_output=True,text=True,timeout=60)
    elapsed=time.monotonic_ns()-start
    (directory/(name+'.stdout')).write_text(completed.stdout);(directory/(name+'.stderr')).write_text(completed.stderr)
    row=dict(id=name,input=ref(input_path),elapsed_ns=elapsed,returncode=completed.returncode,
             stdout=ref(directory/(name+'.stdout')),stderr=ref(directory/(name+'.stderr')))
    if output.exists():row['output']=ref(output)
    put(directory/(name+'.attempt.json'),row)
    require(completed.returncode==0,'device worker failure: '+name)
    result=load(output)
    if sanitizer:
        text=completed.stdout+completed.stderr
        pattern=r'RACECHECK SUMMARY: 0 hazards' if sanitizer=='racecheck' else r'ERROR SUMMARY: 0 errors'
        require(re.search(pattern,text) is not None,'missing zero-error sanitizer summary: '+name)
    return row,result

def primitive():
    m=verify();directory=BASE/'primitive';directory.mkdir(exist_ok=False);rows=[]
    retained=load(ROOT/'docs/benchmarks/data/fp4-gpu-pilot-diagnosis-v1.json')
    retained_rows=[r for r in retained['rows'] if r['comparison_passed']]
    require(len(retained_rows)==30,'retained control comparison coverage')
    for row in retained_rows:
        for key in ('input','output','stdout','stderr'):checked(row[key])
    for f,k in ((4,2),(4,4),(4,8)):
        for trans in (False,True):
            for pattern in ('dense','tail','codebook','tiny','huge'):
                r=o.request('irregular-29' if pattern=='tail' else 'dense-32',f,k)
                r['mode']='transpose' if trans else 'forward'
                v=[(i%15-7)/8 if i<r['n'] else 0. for i in range(32)]
                if pattern in ('codebook','tiny','huge'):
                    exponent=-48 if pattern=='tiny' else 48 if pattern=='huge' else 0
                    codes=[i if i!=8 else 0 for i in range(16)]
                    r['matrix']=[float(o.decode(codes[(i*13+j*7)%16],4)*Q(2)**exponent) for i in range(32) for j in range(32)]
                    v=[float(o.decode(codes[i%16],4)*Q(2)**exponent) for i in range(32)]
                    if f!=64:r['matrix_codes'],r['matrix_exponents'],_,_=o.encode(tuple(r['matrix']),f,k)
                r['initial'][32 if trans else 64:64 if trans else 96]=v
                expected=o.product_reference(r)
                name=f'{f}-{k}-{r["mode"]}-{pattern}';row,result=execute(directory,name,r)
                require(result['status']=='completed','primitive refusal')
                error=max(abs(Q(a)-b) for a,b in zip(result['product'],expected))
                scale=max(Q(1,1<<96),max(map(abs,expected)))
                # Primitive oracle threshold fixed before device execution. FP4
                # group sums are exact; pairs/scales have a separate comparison.
                relative=Q(1,1<<38) if f in (4,64) else Q(1,1<<19)
                require(error<=relative*scale,'independent primitive mismatch: '+name)
                row.update(error=float(error),comparison_limit=float(relative*scale));rows.append(row)
    put(BASE/'primitive.json',dict(status='passed',manifest=ref(MANIFEST),rows=rows,reused_control_rows=retained_rows,reused_control_diagnosis=ref(ROOT/'docs/benchmarks/data/fp4-gpu-pilot-diagnosis-v1.json'),certified=False))
    print(f'{len(rows)} independent primitive comparisons passed.')

def device():
    verify();require(load(BASE/'primitive.json')['status']=='passed','primitive prerequisite')
    directory=BASE/'device';directory.mkdir(exist_ok=False);rows=[]
    for f,k in o.LANES:
        endpoints={}
        for v in o.VARIANTS:
            for updates in (1,8,32):
                r=o.request('irregular-29',f,k,v,updates)
                name=f'{f}-{k}-{v}-{updates}';row,out=execute(directory,name,r)
                require(out['status']=='completed' and out['physical_updates']==updates,'trajectory admission')
                require(all(pair[0]==0 and pair[1]==updates for pair in zip(out['observed_flags'][::2],out['observed_flags'][1::2])),'update/sticky count')
                reference=o.reference(r,updates);row['observed_error']=o.observed_error(out['state'],reference)
                if f==64:require(row['observed_error']['max_absolute']<=1e-14,'native original-A differential')
                if v!='roundtrip':
                    if updates in endpoints:require(out['codes']==endpoints[updates]['codes'] and out['exponents']==endpoints[updates]['exponents'] and out['state']==endpoints[updates]['state'],'fusion/persistence changes recurrence')
                    else:endpoints[updates]=out
                rows.append(row)
        for scenario in ('pre_cancel','cancel','fault'):
            r=o.request('irregular-29',f,k)
            r['cancel_after']=0 if scenario=='pre_cancel' else 8 if scenario=='cancel' else None
            r['inject_fault']=scenario=='fault'
            name=f'{f}-{k}-{scenario}';row,out=execute(directory,name,r)
            require(out['status']==('refused' if scenario=='fault' else 'cancelled'),'failure/cancellation status')
            require(out['state']==r['initial'],'complete rollback')
            if scenario!='pre_cancel':require(out['rollback_exact'] and out['physical_updates']>0 and out['logical_updates']==0,'physical accounting or rollback')
            rows.append(row)
    put(BASE/'device.json',dict(status='passed',rows=rows,manifest=ref(MANIFEST),certified=False))
    print(f'{len(rows)} trajectory and transactional safety cases passed.')

def sanitizer(tool):
    verify();require(load(BASE/'device.json')['status']=='passed','device prerequisite')
    directory=BASE/tool;directory.mkdir(exist_ok=False);rows=[]
    for f,k in o.LANES:
        for variant in o.VARIANTS:
            name=f'{f}-{k}-{variant}'
            row,out=execute(directory,name,o.request('irregular-29',f,k,variant),tool)
            require(out['status']=='completed','sanitizer numerical refusal');rows.append(row)
    put(BASE/(tool+'.json'),dict(status='passed',rows=rows,manifest=ref(MANIFEST)))
    print(f'{tool}: all {len(rows)} scoped paths passed.')

def profile(workload,repetition):
    m=verify()
    for tool in ('memcheck','racecheck','initcheck','synccheck'):require(load(BASE/(tool+'.json'))['status']=='passed','sanitizer prerequisite')
    directory=BASE/f'profiles-{workload}-{repetition}';directory.mkdir(exist_ok=False);rows=[]
    for cell in m['cells']:
        if cell['workload']!=workload or cell['repetition']!=repetition:continue
        start=time.monotonic_ns();o.encode.cache_clear()
        request=o.request(workload,cell['format'],cell['components'],cell['variant'])
        preparation=time.monotonic_ns()-start
        row,out=execute(directory,cell['id'],request)
        require(out['status']=='completed' and out['physical_updates']==32,'profile numerical refusal')
        expected=o.reference(request,32);observation=o.observed_error(out['state'],expected)
        nonzeros=sum(v!=0 for v in request['matrix']);k=cell['components'];f=cell['format'];blocks=request['blocks']
        row.update(cell,preparation_ns=preparation,cold_ns=preparation+row['elapsed_ns'],observation=observation,
            original_a_primal_residual=out['original_a_primal_residual'],counts=out['counts'],phases_ns=out['phases_ns'],cuda_stream_span_ms=out['cuda_stream_span_ms'],
            work=dict(useful_original_flops=4*nonzeros*32,component_pairs_per_product=1 if f==64 else k*k,
                      mma_instructions=0 if f==64 else blocks*32*2*2*k*k*(2 if f==16 else 1),
                      mma_flops=0 if f==64 else blocks*32*2*2*k*k*2*16*8*32,
                      single_rhs_utilization=1 if f==64 else 1/8,
                      padded_coordinates=blocks*(32-request['n']),matrix_nonzeros=nonzeros,
                      vector_normalizations=0 if f==64 else blocks*32*3*k,
                      projection_coordinates=blocks*request['n']*32),certified=False)
        rows.append(row)
        print(cell['id'],row['cold_ns']/1e6,'ms',flush=True)
    require(len(rows)==24,'profile cell coverage')
    put(BASE/f'profiles-{workload}-{repetition}.json',dict(status='passed',manifest=ref(MANIFEST),rows=rows))

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('stage',choices=['freeze','primitive','device','sanitizer','profile']);p.add_argument('--tool');p.add_argument('--workload');p.add_argument('--repetition',type=int);a=p.parse_args()
    if a.stage=='freeze':freeze()
    elif a.stage=='primitive':primitive()
    elif a.stage=='device':device()
    elif a.stage=='sanitizer':sanitizer(a.tool)
    else:profile(a.workload,a.repetition)

if __name__=='__main__':main()
