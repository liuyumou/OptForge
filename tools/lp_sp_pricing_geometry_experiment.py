"""Fresh geometry development and prospectively frozen million-NNZ COPT pairs."""
import argparse
from fractions import Fraction as Q
import json
from pathlib import Path
import sys
import time
import numpy as np
from lp_sp_pricing_budget import ROOT,BASE,NS,put,binding
from lp_sp_pricing_gpu_opt_compare import read,verify
from lp_sp_pricing_baselines import PYTHON,images,audit,launch
from lp_sp_pricing_million import matrix,ORIGINAL
from lp_sp_pricing_geometry_admit import sources
from lp_sp_pricing_geometry_run import load
from lp_billion_arrays import write
from lp_billion_owned_process import execute
from sp_pricing.geometry_fast import native_rref,rank_proof,certified_factor_proposal
from sp_pricing.compact_basis import Rows,Storage,sparse_rref
from sp_pricing.exact import Work,Limit

STUDY=BASE/'geometry-million-v1'

def admission():
 path=BASE/'geometry-gpu-admit-v2/admission.json';d=read(path)
 if d['status']!='passed' or d['sources']!=sources():raise RuntimeError('geometry numerical source changed')
 for item in d['evidence']:verify(item)
 if read(BASE/'resources/geometry-gpu-admit-v2.settlement.json')['status']!='passed':raise RuntimeError('GPU admission unsettled')
 return binding(path)

def model(spec,out,seed):
 start=time.perf_counter_ns();a=matrix(spec['m'],spec['n'],spec['degree'],seed,spec['shift']);m,n=a.shape
 rng=np.random.default_rng(seed+17);x=rng.integers(-8,9,size=n).astype(float)/8
 y=rng.integers(1,8,size=m).astype(float)/(1<<(m-1).bit_length());b=a@x;c=np.asarray(a.T@y).ravel()
 arrays=dict(column_ids=write(BASE,np.arange(n),'u32le'),row_ids=write(BASE,np.arange(m),'u32le'),
  column_lower=write(BASE,np.full(n,-np.inf)),column_upper=write(BASE,np.full(n,np.inf)),
  row_lower=write(BASE,np.full(m,-np.inf)),row_upper=write(BASE,b),offsets=write(BASE,a.indptr,'u64le'),
  indices=write(BASE,a.indices,'u32le'),values=write(BASE,a.data),objective_indices=write(BASE,np.arange(n),'u32le'),objective_values=write(BASE,c))
 out.mkdir(parents=True,exist_ok=False);path=out/'portable.json'
 put(path,dict(schema_version=1,model_id=f"{spec['name']}-million-{seed}-nonuniform",rows=m,columns=n,nonzeros=int(a.nnz),sense='maximize',offset=0.,arrays=arrays))
 encoding=time.perf_counter_ns()-start;witness=out/'construction';witness.mkdir()
 put(witness/'response.json',dict(endpoint=dict(primal=write(BASE,x),dual=write(BASE,-y))))
 checked=audit('copt_scale_off',path,path,witness)
 if not checked['accepted']:raise RuntimeError('fresh constructed original model did not certify')
 return dict(**spec,seed=seed,model=binding(path),nonzeros=int(a.nnz),encoding_ns=encoding,construction_audit=binding(witness/'audit.json'))

def development(identity):
 admission();out=BASE/identity;out.mkdir(exist_ok=False);rows=[]
 for name,m,n,degree in [('dense',64,65,65),('tall',64,256,64),('sparse',128,129,16)]:
  a=matrix(m,n,degree,122123);pool={i:Q(i,16) for i in range(1,32)}
  source=Rows(({int(a.indices[k]):pool[int(a.data[k]*16)] for k in range(a.indptr[i],a.indptr[i+1])} for i in range(m)),n)
  outputs=[]
  for lane,fn in [('fraction',sparse_rref),('native',native_rref)]:
   work=Work(seconds=20,max_operations=200000000);start=time.perf_counter_ns();status='completed';reason=None;answer=None
   try:answer=fn(source.rows,n,work,Storage())
   except Limit as e:status='resource_limit';reason=str(e)
   outputs.append(answer);rows.append(dict(case=name,lane=lane,status=status,reason=reason,elapsed_ns=time.perf_counter_ns()-start,operations=work.operations,peak_bits=work.peak_bits))
  if all(outputs) and (outputs[0][0].rows,outputs[0][1])!=(outputs[1][0].rows,outputs[1][1]):raise ArithmeticError('development RREF mismatch')
 proposals=[]
 for spec in ORIGINAL:
  item=model(spec,out/'models'/spec['name'],122127);a,b,c,_,_=load(Path(item['model']['path']))
  start=time.perf_counter_ns();proof,info=certified_factor_proposal(a,b,c,Work(seconds=30,max_operations=200000000))
  proposals.append(dict(model=item,elapsed_ns=time.perf_counter_ns()-start,proposal=info,certificate=proof is not None))
 put(out/'result.json',dict(status='development_complete',geometry=rows,proposals=proposals,sources=sources()))
 print(json.dumps(dict(geometry=rows,proposals=[dict(model=r['model']['name'],proposal=r['proposal']) for r in proposals])),flush=True)

def rank_development(identity):
 admission();out=BASE/identity;out.mkdir(exist_ok=False);rows=[]
 for name,n,degree in [('dense',1000,1000),('sparse',8000,125)]:
  a=matrix(n,n,degree,122129,1);pool={i:Q(i,16) for i in range(1,32)}
  source=Rows(({int(a.indices[k]):pool[int(a.data[k]*16)] for k in range(a.indptr[i],a.indptr[i+1])} for i in range(n)),n)
  for lane in ['fraction','native','gpu-rank']:
   start=time.perf_counter_ns();status='completed';detail={};proved=False;work=Work(seconds=45 if lane=='gpu-rank' else 5,max_operations=200000000)
   try:
    if lane=='gpu-rank':proved,detail=rank_proof(source.rows,n,work,True)
    else:
     answer,pivots=(native_rref if lane=='native' else sparse_rref)(source.rows,n,work,Storage());proved=len(pivots)==n
   except Limit as e:status='resource_limit';detail=dict(reason=str(e))
   row=dict(case=name,lane=lane,status=status,full_space_proved=proved,elapsed_ns=time.perf_counter_ns()-start,detail=detail)
   rows.append(row);print(json.dumps(row),flush=True)
 put(out/'result.json',dict(status='rank_development_complete',rows=rows,sources=sources()))

def freeze():
 gate=admission();STUDY.mkdir(exist_ok=False)
 development=BASE/'geometry-development-v1/result.json';rank=BASE/'geometry-rank-development-v1/result.json'
 if read(development)['status']!='development_complete' or read(rank)['status']!='rank_development_complete':raise RuntimeError('development incomplete')
 models=[model(spec,STUDY/'models'/spec['name'],122141) for spec in ORIGINAL];cells=[]
 for i,m in enumerate(models):
  for lane in (['candidate','copt'] if i%2==0 else ['copt','candidate']):cells.append(dict(id=m['name']+'-'+lane,model_index=i,lane=lane))
 put(STUDY/'freeze.json',dict(status='frozen',admission=gate,development=binding(development),rank_development=binding(rank),
  models=models,cells=cells,native_seconds=30,process_seconds=45,outer_seconds=330,
  sources=sources()+[binding(__file__)],images=images(),
  configuration='CPU exact-certified factor presolve; native sparse GMP pricing fallback; GPU full-space rank proof where applicable',
  limitations=['one cold repetition per lane; no cache flushing','three synthetic all-active models with nonuniform dyadic primal/dual witnesses',
   'presolve certificates do not demonstrate completion of the paper pricing algorithm','all preparation, teardown and independent endpoint checking included in complete cost']))

def validate():
 f=read(STUDY/'freeze.json');admission()
 for item in f['sources']:verify(item)
 for m in f['models']:verify(m['model']);verify(m['construction_audit'])
 if f['images']!=images():raise RuntimeError('checker/baseline image changed')
 return f

def run():
 f=validate()
 for cell in f['cells']:
  m=f['models'][cell['model_index']];out=STUDY/'runs'/cell['id'];out.parent.mkdir(exist_ok=True)
  if cell['lane']=='copt':proc=launch('copt_scale_off',Path(m['model']['path']),Path(m['model']['path']),out,f['native_seconds'],f['process_seconds'])
  else:
   out.mkdir(exist_ok=False);cmd=[str(PYTHON),'-B',str(ROOT/'tools/lp_sp_pricing_geometry_run.py'),m['model']['path'],str(out/'response.json'),'--seconds',str(f['native_seconds'])]
   put(out/'started.json',dict(command=cmd,model=m['model']));proc=execute(cmd,out/'stdout',out/'stderr',f['process_seconds'],None);put(out/'process.json',proc)
  print(json.dumps(dict(cell=cell['id'],process=proc)),flush=True)
 put(STUDY/'completed.json',dict(status='all_cells_attempted'))

def audits():
 f=validate()
 if not (STUDY/'completed.json').exists():raise RuntimeError('unfinished comparisons')
 rows=[]
 for cell in f['cells']:
  m=f['models'][cell['model_index']];out=STUDY/'runs'/cell['id'];proc=read(out/'process.json');path=out/'response.json';d=read(path) if path.exists() else {}
  checked=audit('copt_scale_off',Path(m['model']['path']),Path(m['model']['path']),out)
  native=d.get('solve_ns',d.get('native_ns'));timely=bool(native is not None and native<=f['native_seconds']*NS and proc['returncode']==0 and not proc['timed_out'])
  rows.append(dict(**cell,model=m['name'],status=d.get('status','missing_response'),reason=d.get('reason'),
   route=d.get('route'),timely=timely,strict_accepted=checked['accepted'],native_ns=native,process_ns=proc['elapsed_ns'],
   encoding_ns=m['encoding_ns'],audit_ns=checked['elapsed_ns'],complete_ns=m['encoding_ns']+proc['elapsed_ns']+checked['elapsed_ns'],
   response=binding(path) if path.exists() else None,audit=binding(out/'audit.json'),process=binding(out/'process.json')))
 put(STUDY/'audits.json',dict(status='all_endpoints_audited',rows=rows));print(json.dumps(rows),flush=True)

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('action',choices=['development','rank','freeze','run','audit']);p.add_argument('identity',nargs='?');a=p.parse_args()
 if a.action=='development':development(a.identity)
 elif a.action=='rank':rank_development(a.identity)
 elif a.action=='freeze':freeze()
 elif a.action=='run':run()
 else:audits()
