"""Frozen host-ISA attribution on unchanged numerical source and device code."""
import argparse
from pathlib import Path
from lp_general_common import BASE,ROOT,CPU_CAPS,GPU_CAPS,NS,load,put,ref,require
from lp_general_budget import accounting
from lp_general_oracle import settings


def freeze(identity):
    proofs=[]
    for name in ['scale-cpu-v7','scale-target-gpu-v1']+['scale-target-'+s+'-v1' for s in ['memcheck','racecheck','initcheck','synccheck']]:
        p=BASE/'resources'/(name+'.settlement.json');require(load(p)['status']=='passed','host target admission '+name);proofs.append(ref(p))
    require(load(BASE/'resources/scale-frontier-report-v1.settlement.json')['status']=='passed','complete frozen scale cohorts first')
    for p in (ROOT/'research/lp-general-lowbit/src').glob('*.rs'):
        require(p.read_bytes()==(BASE/'sources/scale-cpu-v6'/p.relative_to(ROOT)).read_bytes(),'host target must preserve numerical source')
    require(ref(BASE/'scale-image-v6/tensor.cubin')['sha256']==ref(BASE/'scale-image-v7/tensor.cubin')['sha256'],'host target changed device code')
    fingerprint=next(p for p in (ROOT/'research/lp-general-lowbit/target/release/.fingerprint').glob('lp-general-lowbit-*/bin-lp-general-lowbit.json')
                     if load(p)['rustflags']==['-C','target-cpu=x86-64-v4'])
    saved=BASE/'scale-host-target-v1/candidate-fingerprint.json';saved.write_bytes(fingerprint.read_bytes())
    require(ref(ROOT/'research/lp-general-lowbit/target/release/lp-general-lowbit')['sha256']==ref(BASE/'scale-image-v7/executor')['sha256'],'host target executable differs')
    models=[m for m in load(BASE/'scale-final-main-v1/freeze.json')['models']
            if m.get('seed')==831001 or m['family'] in ['public-square31','public-scpm1']]
    require(len(models)==8,'host target complete planned population')
    cells=[]
    for i,m in enumerate(models):
        for repeat in range(2):
            lanes=['native','previous-native','fp32','previous-fp32','fp4x2','previous-fp4x2']
            shift=(i+repeat)%6;lanes=lanes[shift:]+lanes[:shift]
            if (i+repeat)%2:lanes.reverse()
            for lane in lanes:
                old=lane.startswith('previous-');fmt=lane.removeprefix('previous-')
                request=dict(settings={**settings(fmt),'iteration_limit':1000,'check_interval':250,'wall_ms':30000},
                    tensor=dict(control_interval=100,min_tile_nnz=128),fast=dict(host_reductions=True,host_preparation=True,host_certificates=True,auto_schedule=True))
                cells.append(dict(id=f'm{i:02d}-r{repeat}-t0-{lane}',model_index=i,lane=lane,tolerance=1e-9,repeat=repeat,
                    request=request,binary=ref(BASE/('scale-image-v6' if old else 'scale-image-v7')/'executor')))
    deadlines=[900 if m['family']=='public-scpm1' else 300 for m in models]
    cpu,gpu=accounting();require(cpu['development']+4*sum(deadlines)*NS<=CPU_CAPS['development']*NS,'complete host target CPU cohort')
    require(gpu['development']+sum(deadlines)*NS<=GPU_CAPS['development']*NS,'complete host target GPU cohort')
    out=BASE/identity;out.mkdir(exist_ok=False);runner=out/'runner.py';runner.write_bytes((ROOT/'tools/lp_general_scale_bench.py').read_bytes())
    put(out/'freeze.json',dict(mode='pilot',models=models,cells=cells,job_seconds=deadlines,seconds_per_job=300,
        binary=ref(BASE/'scale-image-v6/executor'),image=ref(BASE/'scale-image-v6/tensor.cubin'),harness=ref(runner),design=ref(__file__),
        baseline_worker=ref(ROOT/'tools/lp_general_scale_copt.py'),evidence_worker=ref(ROOT/'tools/lp_general_scale_evidence.py'),baseline_solve_seconds=30,proofs=proofs,
        original_fingerprint=ref(BASE/'scale-host-target-v1/original-fingerprint.json'),candidate_fingerprint=ref(saved),
        claim='Host build target only, with identical numerical source, CUDA image and requests. All six structural families and both public pilot anchors retained. Primary time still includes research response transport; no FP4-specific or broad confirmation claim.'))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--id',required=True);freeze(p.parse_args().id)
