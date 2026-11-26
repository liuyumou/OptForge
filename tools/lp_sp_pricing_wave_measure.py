"""Fixed-work diagnostics and a development-only step selection for wave searches."""
import argparse
import json
from pathlib import Path
import statistics
import sys
import time

from lp_sp_pricing_budget import BASE,ROOT,binding,put
from lp_sp_pricing_wave_quality import validate
from lp_sp_pricing_gpu_opt_measure import calibration
from lp_sp_pricing_study import generated,FAMILIES
from lp_sp_pricing_wave_run import run
from sp_pricing.exact import Work
from sp_pricing.geometry import LabelOracle
from sp_pricing.gpu_lean import LeanBatch
from sp_pricing.gpu_wave import WaveEngine,PackedBasis,IntervalProof
from sp_pricing.native_proof import NativeProof


def admission():
    for path in sorted(BASE.glob('wave-gpu-admit-v*/admission.json'),reverse=True):
        try:validate(path)
        except RuntimeError:continue
        return binding(path)
    raise RuntimeError('no current wave admission')


def micro(identity):
    gate=admission();out=BASE/identity;out.mkdir(exist_ok=False)
    p=BASE/'gpu-ladder-v2/coupled-8-73011/result.json';q=BASE/'cpu-ladder-v4/degenerate-16-73011/result.json'
    cases=[('coupled-first',*calibration(p,0)),('coupled-optimum',*calibration(p,2)),('degenerate-optimum',*calibration(q,2))]
    # These larger matrices isolate multi-RHS reuse, without claiming original-LP scalability.
    cases.append(('dense-256',[[((i*17+j*13)%19-9)/16 for j in range(512)] for i in range(256)],4,1/65536))
    cases.append(('sparse-512',[[float(j in {(2*i+k*37)%1024 for k in range(6)}) for j in range(1024)] for i in range(512)],4,1/65536))
    put(out/'plan.json',dict(admission=gate,cases=[dict(name=n,r=len(b),s=len(b[0])) for n,b,_,_ in cases],
        widths=[64,256],steps=256,repetitions=3,formats=['dense','csr'],fixed_work=True,
        scope='resident CUDA context; per-cell matrix/state preparation, iterations and downloads; host checking reported separately',
        scalar_equations_and_precision='same diagonal FP64 PDHG as lean',source=binding(__file__)))
    rows=[];proof_rows=[]
    with WaveEngine() as engine:
        for name,b,h,eps in cases:
            o=LabelOracle(b,h,eps,Work(max_operations=2000000000,seconds=600));packed=PackedBasis(o)
            for sparse in (False,True):
                for width in (64,256):
                    slots=[i%(2*o.n) for i in range(width)]
                    for repetition in range(3):
                        for lane in (['lean','wave'] if repetition%2==0 else ['wave','lean']):
                            start=time.perf_counter_ns();device=0
                            if lane=='wave':
                                prep=engine.load(o,slots,packed,sparse);result=engine.advance(256,[1]*width)
                                device=result['device_iteration_ms'];preparation=prep['load_ns']
                            else:
                                with LeanBatch(ROOT/'research/lp-sp-pricing/target/release/libsp_batch_optimized.so',b,sparse) as old:
                                    preparation=old.preparation_ns
                                    for first in range(0,width,64):
                                        old.begin(slots[first:first+64],h,eps);result=old.advance(256)
                                        device+=result['device_iteration_ms']
                            row=dict(case=name,sparse=sparse,width=width,repetition=repetition,lane=lane,
                                complete_ns=time.perf_counter_ns()-start,preparation_ns=preparation,device_ms=device)
                            rows.append(row);print(json.dumps(row),flush=True)
                            if lane=='wave' and sparse and width==64 and name in ('coupled-first','coupled-optimum','degenerate-optimum'):
                                # Same raw buffers and sequential resolution policy for both checkers.
                                with NativeProof(o) as exact,IntervalProof(o,packed) as fast:
                                    outputs={};cost={};fast_stats=None
                                    for check_lane in (['gmp','interval'] if repetition%2==0 else ['interval','gmp']):
                                        begin=time.perf_counter_ns();known={}
                                        if check_lane=='interval':known,fast_stats=fast.batch(slots,[1]*width,engine.x,engine.u,{})
                                        else:
                                            for offset,slot in enumerate(slots):
                                                if slot//2 in known:continue
                                                proof=exact.labels(slot//2,[engine.x[offset*o.r+i] for i in range(o.r)],
                                                    [engine.u[offset*2*o.n+i] for i in range(2*o.n)])
                                                known.update(proof['established'])
                                        cost[check_lane]=time.perf_counter_ns()-begin;outputs[check_lane]=known
                                    if outputs['gmp']!=outputs['interval']:raise RuntimeError('fixed-input check decisions differ')
                                    proof_rows.append(dict(case=name,repetition=repetition,proposals=width,
                                        gmp_ns=cost['gmp'],interval_ns=cost['interval'],labels=len(outputs['interval']),interval=fast_stats))
    put(out/'result.json',dict(status='passed',rows=rows,checks=proof_rows,admission=gate))


def ladder(identity,steps):
    gate=admission();out=BASE/identity;out.mkdir(exist_ok=False);rows=[]
    cells=[dict(id=f'{family}-{n}-73011',family=family,columns=n,
        rows=max(2,n//2) if family=='wide' else 4*n if family=='tall' else 2*n,seed=73011)
        for n in [4,8,16] for family in FAMILIES]
    put(out/'plan.json',dict(cells=cells,steps=steps,sparse=True,asynchronous_initialization=True,
        heldout=False,seconds=10,source=binding(__file__),admission=gate))
    for cell in cells:
        directory=out/cell['id'];directory.mkdir();model,witness=generated(cell)
        put(directory/'model.json',model);put(directory/'construction.json',witness)
        put(directory/'started.json',dict(model=binding(directory/'model.json')))
        result=run(model,'wave',steps=steps);put(directory/'result.json',result)
        row=dict(id=cell['id'],status=result['status'],accepted=result['audit']['accepted'],
            timely=result['solve_ns']<=10e9,elapsed_ns=result['complete_ns'],result=binding(directory/'result.json'))
        rows.append(row);print(json.dumps(row),flush=True)
    put(out/'result.json',dict(status='completed',rows=rows,steps=steps))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['micro','ladder','tune']);p.add_argument('identity')
    p.add_argument('--steps',type=int,default=1000);a=p.parse_args()
    if a.action=='micro':micro(a.identity)
    elif a.action=='ladder':ladder(a.identity,a.steps)
    else:
        micro('wave-micro-v1');ladder('wave-ladder-v1',1000);ladder('wave-ladder-v2',256)
