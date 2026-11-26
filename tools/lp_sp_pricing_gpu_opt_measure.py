"""Fresh fixed-work and original-LP development measurements for lean GPU proposals."""
import argparse
import json
from pathlib import Path
import statistics
import sys
import time
from lp_sp_pricing_budget import BASE,ROOT,binding,put
from lp_sp_pricing_gpu_opt_quality import LIBRARY,OLD,validate
from lp_sp_pricing_run import attempt
from lp_sp_pricing_study import FAMILIES,generated

sys.path.insert(0,str(ROOT/'research/lp-sp-pricing/python'))
from sp_pricing.exact import Work,rational
from sp_pricing.geometry import LabelOracle
from sp_pricing.gpu import GpuBatch,accept_proposal
from sp_pricing.native_proof import NativeProof


def admission():
    for path in sorted(BASE.glob('gpu-opt-admit-v*/admission.json'),reverse=True):
        try:validate(path)
        except RuntimeError:continue
        return binding(path)
    raise RuntimeError('no admission binds current lean implementation')

def calibration(path,index):
    data=json.loads(path.read_text())
    events=[e for e in data['events'] if 'calibration' in e]
    c=events[index]['calibration']
    return [[rational(v) for v in row] for row in c['basis']],rational(c['H']),rational(c['epsilon'])


def micro(identity):
    admitted=admission()
    out=BASE/identity;out.mkdir(exist_ok=False)
    source=BASE/'gpu-ladder-v2/coupled-8-73011/result.json'
    big=BASE/'cpu-ladder-v4/degenerate-16-73011/result.json'
    cases=[('coupled-first',source,0),('coupled-optimum',source,2),('degenerate-optimum',big,2)]
    configs=[('legacy_fp32x2',OLD,'fp32x2'),('legacy_fp64',OLD,'fp64'),('lean_fp64',LIBRARY,'fp64')]
    put(out/'plan.json',dict(cases=[dict(name=n,source=binding(p),event=i) for n,p,i in cases],
        widths=[32,64],formats=['dense','csr'],steps=1000,targets=64,repetitions=3,
        order='cyclic implementation rotations',source=binding(__file__),
        timing='shared-context warm CUDA; fresh per-cell matrix/workspace upload, 64 targets, exact native proof checks; no CPU fallback',
        no_original_lp_claim=True,admission=admitted,candidate_preconditioning='diagonal_absolute_sums',
        fixed_step_comparison_does_not_require_identical_iterates=True))
    # A separately recorded CUDA runtime initialization is excluded equally
    # from this resident-context diagnostic. Fresh-process LP tests include it.
    warm=time.perf_counter_ns()
    with GpuBatch(LIBRARY,[[0,1]],False):pass
    put(out/'warmup.json',dict(elapsed_ns=time.perf_counter_ns()-warm))
    rows=[];check_comparison=None
    for name,path,index in cases:
        b,h,eps=calibration(path,index)
        for sparse in (False,True):
            for width in (32,64):
                for rep in range(3):
                    for label,library,mode in configs[rep:]+configs[:rep]:
                        cell=f'{name}-{int(sparse)}-{width}-{rep}-{label}'
                        put(out/(cell+'-started.json'),dict(id=cell))
                        oracle=LabelOracle(b,h,eps,Work(max_operations=500000000,seconds=120))
                        begin=time.perf_counter_ns();device=wall=checks=accepted=0
                        with NativeProof(oracle) as checker,GpuBatch(library,b,sparse) as engine:
                            for start in range(0,64,width):
                                slots=[(start+i)%(2*oracle.n) for i in range(width)]
                                result=engine.propose(slots,h,eps,1000,mode,slot_targets=True)
                                wall+=result['elapsed_ns'];device+=result['device_iteration_ms']*1e6
                                check_start=time.perf_counter_ns()
                                proofs=[checker.check(s//2,result['x'][i],result['dual'][i],full_dual=True) for i,s in enumerate(slots)]
                                checks+=time.perf_counter_ns()-check_start;accepted+=sum(p['accepted'] for p in proofs)
                                # Once, time the unchanged Python checker on
                                # the exact same raw proposals and compare all
                                # proof values, rather than comparing solve work.
                                if check_comparison is None and name=='coupled-optimum' and label=='lean_fp64':
                                    compact_begin=time.perf_counter_ns()
                                    compact=[checker.labels(s//2,result['x'][i],result['dual'][i]) for i,s in enumerate(slots)]
                                    compact_ns=time.perf_counter_ns()-compact_begin
                                    stamp=time.perf_counter_ns()
                                    reference=[accept_proposal(oracle,s//2,result['x'][i],result['dual'][i]) for i,s in enumerate(slots)]
                                    python_ns=time.perf_counter_ns()-stamp
                                    for old,new in zip(reference,proofs):
                                        for key in ['x','witness','dual_upper','established']:
                                            if old[key]!=new[key]:raise AssertionError('checker benchmark proof mismatch')
                                    if any(a['established']!=b['established'] for a,b in zip(compact,reference)):
                                        raise AssertionError('compact checker benchmark decision mismatch')
                                    check_comparison=dict(proposals=width,python_ns=python_ns,native_ns=checks,
                                        native_compact_ns=compact_ns,source=binding(path),case=name,identical_raw_inputs=True)
                                    # The auxiliary cell's stopwatch excludes
                                    # this extra independent diagnostic work.
                                    begin+=python_ns+compact_ns
                            row=dict(id=cell,case=name,sparse=sparse,width=width,repetition=rep,implementation=label,
                                targets=64,steps=1000,accepted_targets=accepted,preparation_ns=engine.preparation_ns,
                                checker_preparation_ns=checker.preparation_ns,device_ns=device,proposal_ns=wall,
                                exact_check_ns=checks,complete_ns=time.perf_counter_ns()-begin)
                        row['complete_ns']=time.perf_counter_ns()-begin
                        put(out/(cell+'.json'),row);rows.append(row)
                        print(json.dumps({k:row[k] for k in ['id','complete_ns','device_ns','accepted_targets']}),flush=True)
    put(out/'result.json',dict(status='all_fixed_work_cells_completed',rows=rows,checker_comparison=check_comparison))


def ladder(identity,width=32,sparse=True,steps=1000):
    admitted=admission()
    out=BASE/identity;out.mkdir(exist_ok=False)
    cells=[dict(id=f'{family}-{n}-73011',family=family,columns=n,
        rows=max(2,n//2) if family=='wide' else 4*n if family=='tall' else 2*n,seed=73011)
        for n in [4,8,16] for family in FAMILIES]
    config=dict(library=str(LIBRARY),mode='fp64',sparse=sparse,backend='lean',steps=steps)
    put(out/'plan.json',dict(cells=cells,configuration=config,batch_width=width,seconds=10,
        compact_trace=True,source=binding(__file__),heldout=False,admission=admitted))
    rows=[]
    for cell in cells:
        directory=out/cell['id'];directory.mkdir()
        model,witness=generated(cell);put(directory/'model.json',model);put(directory/'construction.json',witness)
        put(directory/'started.json',dict(configuration=config,model=binding(directory/'model.json')))
        result=attempt(model,seconds=10,operations=200000000,gpu=config,batch=width,compact_trace=True,market_backend='flow')
        put(directory/'result.json',result)
        row=dict(id=cell['id'],status=result['status'],accepted=result['audit']['accepted'],
            reason=result.get('reason'),elapsed_ns=result['complete_ns'],queries=result.get('queries',0),
            phases=result['phase_ns'],result=binding(directory/'result.json'))
        rows.append(row);print(json.dumps(row),flush=True)
    put(out/'result.json',dict(status='all_fresh_candidate_development_cells_attempted',rows=rows))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['micro','ladder','tune','lean-tune']);p.add_argument('identity')
    p.add_argument('--width',type=int,default=32);p.add_argument('--dense',action='store_true');p.add_argument('--steps',type=int,default=1000)
    a=p.parse_args()
    if a.action=='micro':micro(a.identity)
    elif a.action=='ladder':ladder(a.identity,a.width,not a.dense,a.steps)
    elif a.action=='tune':
        micro('gpu-opt-micro-v2')
        ladder('gpu-opt-ladder-v1',64,True,1000)
        ladder('gpu-opt-ladder-v2',64,True,10000)
    else:
        from lp_sp_pricing_gpu_opt_compare import smoke
        smoke('gpu-opt-cold-smoke-v1',dict(width=64,steps=1000,sparse=True))
        micro('gpu-opt-micro-v3')
        ladder('gpu-opt-ladder-v3',64,True,1000)
        ladder('gpu-opt-ladder-v4',64,True,256)
