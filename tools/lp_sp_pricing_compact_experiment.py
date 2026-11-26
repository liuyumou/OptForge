"""Fresh bounded compact-path development and confirmation, with retained controls."""
import argparse
from fractions import Fraction as Q
import json
from pathlib import Path
import resource
import sys
import time
from types import SimpleNamespace
import numpy as np
from lp_sp_pricing_budget import BASE,ROOT,NS,binding,put
from lp_sp_pricing_gpu_opt_compare import read,verify
from lp_sp_pricing_compact_study import sources,CRATE
from lp_sp_pricing_baselines import PYTHON,portable,audit,images
from lp_sp_pricing_study import generated
from lp_billion_owned_process import execute

sys.path.insert(0,str(CRATE/'python'))
from sp_pricing.compact_basis import Rows,PairedRows
from sp_pricing.compact_geometry import CompactOracle
from sp_pricing.compact_gpu import proposals
from sp_pricing.gpu_wave import WaveEngine,PackedBasis,IntervalProof
from sp_pricing.exact import Work,Limit

STUDY=BASE/'compact-experiment-v1'


def admission():
    path=BASE/'compact-gpu-admit-v3/admission.json';d=read(path)
    if d['status']!='passed' or d['sources']!=sources():raise RuntimeError('compact numerical admission changed')
    for item in d['evidence']:verify(item)
    if read(BASE/'resources/compact-gpu-admit-v3.settlement.json')['status']!='passed':raise RuntimeError('GPU admission not settled')
    return binding(path)


def freeze():
    gate=admission();STUDY.mkdir(exist_ok=False);aux=[];small=[];models=[]
    for case in ['dense-million','diagonal-million','factor-128m']:
        lanes=['wave','compact-serial','compact-pipeline'] if case!='factor-128m' else ['compact-serial','compact-pipeline']
        if case=='dense-million':lanes+=['compact-stream']
        for rep in range(2):
            for lane in (lanes if rep==0 else lanes[::-1]):
                aux.append(dict(id=f'{case}-r{rep}-{lane}',case=case,lane=lane,repetition=rep,
                    process_seconds=90 if case=='factor-128m' else 45))
    for i,family in enumerate(['coupled','dense','degenerate']):
        cell=dict(id=f'{family}-8-122011',family=family,columns=8,rows=16,seed=122011)
        out=STUDY/'models'/cell['id'];out.mkdir(parents=True);start=time.perf_counter_ns()
        model,witness=generated(cell);put(out/'rational.json',model);put(out/'construction.json',witness);portable(model,out/'portable.json')
        models.append(dict(**cell,rational=binding(out/'rational.json'),portable=binding(out/'portable.json'),encoding_ns=time.perf_counter_ns()-start))
        lanes=['wave','compact-cpu','compact-serial','compact-pipeline']
        for rep in range(2):
            shift=(i+rep)%4
            for lane in lanes[shift:]+lanes[:shift]:small.append(dict(id=f"{cell['id']}-r{rep}-{lane}",model_index=i,lane=lane,repetition=rep))
    prior=read(BASE/'million-v1/freeze.json')
    put(STUDY/'freeze.json',dict(status='frozen',admission=gate,auxiliary=aux,models=models,small=small,
        original_models=prior['original_models'],prior_original_evidence=binding(BASE/'million-v1/freeze.json'),
        numerical_sources=sources(),sources=[binding(Path(__file__)),binding(ROOT/'tools/lp_sp_pricing_compact_run.py')],
        images=images(),steps=64,width=32,original_seconds=20,original_process_seconds=30,
        small_seconds=10,small_process_seconds=15,
        scope='opt-in practical path; no literal-reference or broad-superiority claim',
        limits='unchanged physical limits and phase caps; exact fallback/recovery tableaus retain their existing one-million-cell limits'))
    print(json.dumps(dict(status='frozen',auxiliary_cells=len(aux),small_cells=len(small),large_candidate_cells=3)),flush=True)


def validate():
    f=read(STUDY/'freeze.json');verify(f['admission']);admission()
    for item in f['sources']+f['numerical_sources']:verify(item)
    for m in f['models']:verify(m['rational']);verify(m['portable'])
    for m in f['original_models']:verify(m['model'])
    if images()!=f['images']:raise RuntimeError('independent checker changed')
    return f


def fixture(name):
    if name=='factor-128m':
        matrix=PairedRows(Rows([{i:Q(1)} for i in range(4000)],8000),list(range(4000)))
        expected={i:1 if i<4000 else -1 for i in range(8000)}
        stored=4000;isotropic=0
    elif name=='diagonal-million':
        matrix=Rows([{2*i+1:Q(1)} for i in range(500)],2000)
        expected={i:1 if i<500 else -1 for i in range(1000)};stored=500;isotropic=0
    else:
        rng=np.random.default_rng(122009);pool={i:Q(i,16) for i in range(1,32)}
        matrix=Rows(({j:pool[int(v)] for j,v in enumerate(rng.integers(1,32,size=2000))} for _ in range(500)),2000)
        sums=[Q(0)]*2000
        for i in range(matrix.r):
            for j,q in matrix.row(i).items():sums[j]+=q
        # One explicit feasible positive combination proves every positive label.
        if min(sums)*4<max(sums):raise RuntimeError('independent dense fixture witness failed')
        expected={i:1 for i in range(1000)};stored=1000000;isotropic=None
    return matrix,expected,stored,isotropic


def auxiliary_child(identity):
    f=validate();cell=next(c for c in f['auxiliary'] if c['id']==identity);out=STUDY/'auxiliary'/identity
    start=time.perf_counter_ns();matrix,expected,stored,isotropic=fixture(cell['case'])
    seconds=75 if cell['case']=='factor-128m' else 35
    work=Work(seconds=seconds,max_operations=4000000000)
    oracle=CompactOracle(matrix,4,Q(1,1024*(matrix.s//2)),work,isotropic_error=isotropic)
    generated=time.perf_counter_ns();labels={};metadata={};status='completed';reason=None
    try:
        if cell['lane']=='wave':
            b=[[matrix.row(i).get(j,Q(0)) for j in range(matrix.s)] for i in range(matrix.r)]
            old=SimpleNamespace(b=b,r=matrix.r,n=matrix.s//2,h=oracle.h,epsilon=oracle.epsilon,
                broadcast_negative=oracle.broadcast_negative,work=work,epoch=0)
            prepared=time.perf_counter_ns();packed=PackedBasis(old);slots=list(range(matrix.s))
            with WaveEngine() as engine,IntervalProof(old,packed) as checker:
                load=engine.load(old,slots,packed,True)
                preparation_ns=time.perf_counter_ns()-prepared
                advance=engine.advance(f['steps'],[1]*len(slots));begin=time.perf_counter_ns()
                labels,checked=checker.batch(slots,[1]*len(slots),engine.x,engine.u,{})
                metadata=dict(preparation_ns=preparation_ns,advance=advance,check_ns=time.perf_counter_ns()-begin,
                    proof=checked,gpu_arena_bytes=load['arena_bytes'],resident_searches=len(slots))
        else:
            labels,metadata=proposals(oracle,width=f['width'],steps=f['steps'],pipeline=cell['lane']!='compact-serial',
                device_cache_bytes=0 if cell['lane']=='compact-stream' else 64<<20)
    except Limit as e:status='resource_limit';reason=str(e)
    if any(expected.get(i)!=v for i,v in labels.items()):raise ArithmeticError('independent fixture witness disagrees')
    result=dict(status=status,reason=reason,labels=len(labels),complete_labels=len(labels)==len(expected),
        expected_labels=len(expected),matrix_rows=matrix.r,matrix_columns=matrix.s,
        matrix_positions=matrix.r*matrix.s,stored_factor_entries=stored,
        generation_ns=generated-start,complete_ns=time.perf_counter_ns()-start,
        process_hwm_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,metadata=metadata,
        independent_validation='exact structural witnesses or dense common positive witness; all returned labels checked',
        fallback_constructed=oracle.fallback_constructions,work_operations=work.operations)
    put(out/'response.json',result);print(json.dumps({k:result[k] for k in ['status','labels','complete_ns','process_hwm_bytes']}),flush=True)


def auxiliary():
    f=validate()
    for cell in f['auxiliary']:
        out=STUDY/'auxiliary'/cell['id'];out.mkdir(parents=True,exist_ok=False)
        command=[str(PYTHON),'-B',__file__,'aux-child','--cell',cell['id']]
        put(out/'started.json',dict(cell=cell,command=command))
        proc=execute(command,out/'stdout',out/'stderr',cell['process_seconds'],None);put(out/'process.json',proc)
        print(json.dumps(dict(cell=cell['id'],process=proc)),flush=True)
    put(STUDY/'auxiliary-completed.json',dict(status='all_cells_attempted'))


def launch_candidate(model,out,lane,seconds,outer):
    out.mkdir(parents=True,exist_ok=False)
    if lane=='wave':command=[str(PYTHON),'-B',str(ROOT/'tools/lp_sp_pricing_wave_run.py'),str(model),str(out/'response.json'),'--seconds',str(seconds)]
    else:
        command=[str(PYTHON),'-B',str(ROOT/'tools/lp_sp_pricing_compact_run.py'),str(model),str(out/'response.json'),'--seconds',str(seconds)]
        if lane=='compact-cpu':command.append('--cpu')
        if lane=='compact-serial':command.append('--serial')
    put(out/'started.json',dict(command=command,model=binding(model),lane=lane))
    proc=execute(command,out/'stdout',out/'stderr',outer,None);put(out/'process.json',proc)
    print(json.dumps(dict(cell=out.name,process=proc)),flush=True)


def original():
    f=validate()
    for model in f['original_models']:
        launch_candidate(Path(model['model']['path']),STUDY/'original'/model['name'],'compact-pipeline',
            f['original_seconds'],f['original_process_seconds'])
    put(STUDY/'original-completed.json',dict(status='all_previously_unsupported_candidate_cells_attempted'))


def small():
    f=validate()
    for cell in f['small']:
        model=f['models'][cell['model_index']]
        launch_candidate(Path(model['rational']['path']),STUDY/'small'/cell['id'],cell['lane'],
            f['small_seconds'],f['small_process_seconds'])
    put(STUDY/'small-completed.json',dict(status='all_cells_attempted'))


def audits():
    f=validate();rows=[];large=[]
    if not (STUDY/'small-completed.json').exists() or not (STUDY/'original-completed.json').exists():raise RuntimeError('solve roster incomplete')
    for cell in f['small']:
        model=f['models'][cell['model_index']];out=STUDY/'small'/cell['id'];proc=read(out/'process.json')
        response=read(out/'response.json') if (out/'response.json').exists() else {}
        proof=audit('practical',Path(model['portable']['path']),Path(model['rational']['path']),out)
        rows.append(dict(**cell,model=model['id'],status=response.get('status','missing_response'),
            timely=proc['returncode']==0 and not proc['timed_out'] and response.get('solve_ns',float('inf'))<=f['small_seconds']*NS,
            exact_accepted=bool(proof.get('exact') and proof['exact']['accepted']),strict_accepted=proof['accepted'],
            complete_ns=model['encoding_ns']+proc['elapsed_ns']+proof['elapsed_ns'],response=binding(out/'response.json') if response else None,
            audit=binding(out/'audit.json')))
    for model in f['original_models']:
        out=STUDY/'original'/model['name'];proc=read(out/'process.json')
        response=read(out/'response.json') if (out/'response.json').exists() else {}
        proof=audit('copt_scale_off',Path(model['model']['path']),Path(model['model']['path']),out)
        large.append(dict(model=model['name'],status=response.get('status','missing_response'),reason=response.get('reason'),
            queries=response.get('queries'),strict_accepted=proof['accepted'],phase_ns=response.get('phase_ns'),
            complete_ns=model['encoding_ns']+proc['elapsed_ns']+proof['elapsed_ns'],
            response=binding(out/'response.json') if response else None,audit=binding(out/'audit.json')))
    put(STUDY/'audits.json',dict(status='all_original_endpoints_audited',small=rows,large=large))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['freeze','aux-child','auxiliary','original','small','audit']);p.add_argument('--cell');a=p.parse_args()
    if a.action=='freeze':freeze()
    elif a.action=='aux-child':auxiliary_child(a.cell)
    elif a.action=='auxiliary':auxiliary()
    elif a.action=='original':original()
    elif a.action=='small':small()
    else:audits()
