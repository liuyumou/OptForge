"""Frozen matched FP4 performance grid; all outcomes and costs remain visible."""
import argparse
import hashlib
from pathlib import Path
import time
import shutil
import subprocess
import numpy as np
from lp_fp4_fast_common import ROOT, BASE, DEVICE, put, load, ref, checked, require
from lp_fp4_fast_experiment import BINARY, execute
import lp_fp4_fast_prepare as prep
import lp_fp4_gpu_oracle as oracle

STUDY=BASE/'study-v1'


def cells():
    rows=[dict(id=f'{family}-{blocks}-{f}-{k}-{backend}-r{rep}',family=family,blocks=blocks,format=f,components=k,backend=backend,repetition=rep)
          for family in ('dyadic','rich') for blocks in (1,64,512,4096) for f,k in oracle.LANES
          for backend in (('legacy','native_cached') if f==64 else ('legacy','hardware')) for rep in range(3)]
    return sorted(rows,key=lambda row:hashlib.sha256(('120428:'+row['id']).encode()).digest())


def request(row):
    blocks,f,k=row['blocks'],row['format'],row['components']
    if row['family']=='dyadic':return prep.request(blocks,f,k,row['backend'],arrays=True,repetitions=7)
    # Build this model directly: no unused dyadic model or encoding is prepared.
    rng=np.random.default_rng(58219)
    a=rng.uniform(-.06,.06,(17,32,32))+np.eye(32)[None,:,:]*.5
    a=a[np.arange(blocks)%17]
    target=np.array([(j%5-2)/4 for j in range(32)])
    objective=np.array([(j%7-3)/16 for j in range(32)])
    cb=np.concatenate([np.broadcast_to(objective,(blocks,32)),(a*target).sum(axis=2)],axis=1)
    words,exponents=([0],[0]) if f==64 else prep.encode_batch(a.reshape(blocks,1024),f,k,arrays=True)
    return dict(n=32,blocks=blocks,matrix=a.reshape(-1),cb=cb.reshape(-1),initial=np.zeros(blocks*96),
        format=f,components=k,matrix_codes=words,matrix_exponents=exponents,backend=row['backend'],
        variant='persistent',updates=32,mode='trajectory',cancel_after=None,inject_fault=False,repetitions=7)


def reference(r):
    # Scalar accumulation order for each independent FP64 dot, vectorized only
    # across different rows/blocks. No approximate components or device outputs.
    a=np.asarray(r['matrix']).reshape(-1,32,32);cb=np.asarray(r['cb']).reshape(-1,64)
    v=np.asarray(r['initial']).reshape(-1,3,32).copy()
    for _ in range(r['updates']):
        aty=np.zeros((r['blocks'],32))
        for j in range(32):aty+=a[:,j,:]*v[:,1,j,None]
        x=np.clip(v[:,0,:]-(cb[:,:32]-aty)/16,-1,1)
        bar=2*x-v[:,0,:];ax=np.zeros_like(aty)
        for j in range(32):ax+=a[:,:,j]*bar[:,j,None]
        y=v[:,1,:]+(cb[:,32:]-ax)/16
        v=np.stack([x,y,bar],axis=1)
    return v.reshape(-1)


def freeze(build,admission):
    require(load(BASE/('admission-'+admission)/'result.json')['status']=='passed','final admission required')
    require(load(BASE/'resources/grid-cpu-v1.settlement.json')['status']=='passed','final grid CPU oracle tests required')
    STUDY.mkdir(exist_ok=False)
    paths=list((ROOT/'research/lp-fp4-fast/src').glob('*.rs'))+list((ROOT/'research/lp-fp4-fast/cuda').glob('*.cu'))
    paths+=list((ROOT/'research/lp-fp4-fast').glob('Cargo.*'))
    paths += [ROOT/'tools'/name for name in ('lp_fp4_fast_prepare.py','lp_fp4_fast_experiment.py','lp_fp4_fast_study.py','lp_fp4_fast_common.py','lp_fp4_fast_budget.py','lp_fp4_fast_admission.py','setup_fp4_fast.py')]
    paths += list((ROOT/'research/lp-tensor-expanded-device/cuda-sys/src').glob('*.rs'))
    paths += list((ROOT/'crates/optimizer-core/src').rglob('*.rs'))
    paths+=[ROOT/'tests/integration/test_lp_fp4_fast.py',ROOT/'docs/specifications/SPEC-0028-fp4-fast.md',ROOT/'research/lp-fp4-gpu-pilot/cuda/pilot_v3.cu',ROOT/'tools/lp_fp4_gpu_oracle.py',ROOT/'tools/lp_cpu_admission.py']
    frozen=STUDY/'frozen';sources=[]
    for path in sorted(paths):
        dest=frozen/path.relative_to(ROOT);dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(path.read_bytes());sources.append(ref(path))
    put(STUDY/'inventory.json',dict(device=DEVICE,inventory=subprocess.check_output(['nvidia-smi','--query-gpu=uuid,name,driver_version,memory.total,memory.used,utilization.gpu','--format=csv,noheader'],text=True),nvcc=subprocess.check_output(['/usr/local/cuda/bin/nvcc','--version'],text=True)))
    shutil.copyfile(BINARY,STUDY/'executor');(STUDY/'executor').chmod(0o755)
    put(STUDY/'manifest.json',dict(kind='fp4-fast-study-v1',sources=sources,image=ref(BASE/('build-'+build)/'fast.cubin'),binary=ref(STUDY/'executor'),build=ref(BASE/('build-'+build)/'receipt.json'),admission=ref(BASE/('admission-'+admission)/'result.json'),grid_cpu=ref(BASE/'resources/grid-cpu-v1.settlement.json'),device=DEVICE,inventory=ref(STUDY/'inventory.json'),cells=cells(),repetitions=7,certified=False))
    print('Frozen',len(cells()),'cold cells; seven fresh prepared windows per cell.')


def run():
    m=load(STUDY/'manifest.json')
    for item in m['sources']+[m['image'],m['binary'],m['build'],m['admission']]:checked(item)
    require(m['cells']==cells(),'frozen cells changed')
    directory=STUDY/'cells';directory.mkdir(exist_ok=False);rows=[];references={};endpoints={}
    shutil.copyfile(checked(m['binary']),directory/'executor');(directory/'executor').chmod(0o755)
    for row in m['cells']:
        start=time.monotonic_ns();r=request(row);preparation_ns=time.monotonic_ns()-start
        attempt,out=execute(directory,row['id'],r,checked(m['image']))
        require(out['status']=='completed' and out['physical_updates']==32,'formal profile refused: '+row['id'])
        key=(row['family'],row['blocks']);audit_start=time.monotonic_ns();reference_ns=0
        if key not in references:
            references[key]=reference(r);reference_ns=time.monotonic_ns()-audit_start
        delta=np.asarray(out['state'])-references[key]
        error=float(np.max(np.abs(delta)));require(np.isfinite(error),'nonfinite observed error')
        if row['format']==64:require(error<=1e-14,'independent native differential')
        endpoint=hashlib.sha256(repr((out['codes'],out['exponents'],out['state'],out['observed_flags'])).encode()).hexdigest()
        lane=key+(row['format'],row['components'])
        if lane in endpoints:require(endpoints[lane]==endpoint,'formal matched endpoints differ')
        else:endpoints[lane]=endpoint
        check_ns=time.monotonic_ns()-audit_start
        result={**row,**attempt,'samples':out['samples'],'phases_ns':out['phases_ns'],
            'preparation_ns':preparation_ns,'cold_input_to_export_ns':preparation_ns+attempt['serialization_ns']+attempt['elapsed_ns'],
            'independent_check_ns':check_ns,'reference_construction_ns':reference_ns,'observed_error':error,
            'original_a_primal_residual':out['original_a_primal_residual'],'endpoint_sha256':endpoint,'counts':out['counts'],'certified':False}
        put(directory/(row['id']+'.result.json'),result);rows.append(result)
        print(len(rows),row['id'],'cuda median ms',float(np.median([x['cuda_ms'] for x in out['samples']])),'error',error,flush=True)
    require(len(rows)==len(m['cells']),'incomplete formal grid')
    put(STUDY/'result.json',dict(status='passed',manifest=ref(STUDY/'manifest.json'),rows=rows,certified=False))


def main():
    p=argparse.ArgumentParser();p.add_argument('stage',choices=['freeze','run']);p.add_argument('--build',default='v6');p.add_argument('--admission',default='v6');a=p.parse_args()
    if a.stage=='freeze':freeze(a.build,a.admission)
    else:run()

if __name__=='__main__':main()
