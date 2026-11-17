"""Frozen, fully charged scale development; no cell retries or success filtering."""
import argparse
import json
import io
import subprocess
import time
from pathlib import Path
import numpy as np
from lp_general_common import BASE,ROOT,CPU_CAPS,GPU_CAPS,NS,put,load,ref,require
from lp_general_budget import accounting
from lp_general_oracle import settings
from lp_general_scale_copt import PYTHON
from lp_general_scale_evidence import save as save_response,read as read_response
from lp_general_scale_io import memory_estimate

BINARY=BASE/'scale-image-v6/executor'
IMAGE=BASE/'scale-image-v6/tensor.cubin'

def assess(model,requests,dest):
    before=time.monotonic_ns()
    p=subprocess.run([str(BINARY),'assess-proven',str(model)],input=''.join(json.dumps(r)+'\n' for r in requests),text=True,capture_output=True)
    elapsed=time.monotonic_ns()-before
    save_response(dest,p.stdout);dest.with_suffix('.stderr').write_text(p.stderr)
    require(p.returncode==0,'independent serial original-model assessment '+p.stderr)
    proofs=[]
    for line in io.StringIO(p.stdout):
        proof=json.loads(line)
        # The complete repeated proof remains byte-exact in the retained stream.
        # Avoid retaining another Python object copy for every endpoint.
        proof.pop('bound_proof',None);proofs.append(proof)
    return proofs,elapsed

def freeze(identity,mode,targets,seconds,model_version=None):
    proofs=[]
    for name in ['scale-cpu-v6','scale-gpu-v7','scale-input-refusal-v1','scale-copt-cpu-v1','scale-copt-gpu-disposition-v1','scale-smoke-v6']+['scale-'+s+'-v7' for s in ['memcheck','racecheck','initcheck','synccheck']]:
        path=BASE/name/'result.json';require(load(path)['status']=='passed','admission '+name);proofs.append(ref(path))
    deferred=mode=='scale' and min(targets)>=4000000
    if deferred:
        p=BASE/'scale-deferred-audit-v2/result.json';require(load(p)['status']=='passed','deferred history audit admission');proofs.append(ref(p))
        p=BASE/'scale-deferred-smoke-v1/result.json';require(load(p)['status']=='passed','complete deferred workflow admission');proofs.append(ref(p))
    models=[];unsupported=[]
    if mode=='broad':
        models=load(BASE/'fast-broad-v2/freeze.json')['models']
    else:
        for target in targets:
            version=model_version if model_version is not None else 2 if mode=='scale' else 1
            manifest=load(BASE/f'scale-models-{target}-v{version}/manifest.json')
            models += [m for m in manifest['models'] if m['status']=='generated' and (mode!='pilot' or m['seed']==831001)]
            unsupported += [m for m in manifest['models'] if m['status']!='generated']
            if target==16000000:require(all(m.get('bipartite_components')==1 for m in manifest['models'] if m['status']=='generated'),'16 M structural admission')
        if targets==[1000000]:models += [m for m in load(BASE/'scale-public-v1/manifest.json')['models'] if m['status']=='generated']
        if mode=='scale':
            require(load(BASE/'scale-inventory-v2/result.json')['status']=='complete','connected construction inventory first')
            if targets==[1000000]:models += [m for m in load(BASE/'scale-public-pds-v2/manifest.json')['models'] if m['status']=='generated']
    memory=[]
    if mode=='scale':
        for m in models:
            estimate=memory_estimate(m['rows'],m['columns'],m['nonzeros'])
            # Include retained trajectories, JSON transport and Python audit
            # objects, beyond the numerical solver's resident representation.
            snapshots=42;vectors=m['rows']+m['columns']
            host=estimate['host_allowance_bytes']+192*vectors*snapshots
            raw=64*vectors*snapshots+(1<<20)
            require(estimate['admits_domain'] and host<15<<30 and estimate['device_allowance_bytes']<12<<30 and raw<4<<30,'complete scale/evidence capacity preflight')
            memory.append(dict(model=m['model'],host_allowance_bytes=host,raw_response_allowance_bytes=raw,device_allowance_bytes=estimate['device_allowance_bytes'],
                limitation='Conservative preflight allowance, not a hard peak enclosure; sampled RSS and actual owned device buffers remain enforced.'))
    cells=[]
    for i,m in enumerate(models):
        for repeat in range(2 if mode=='pilot' else 1):
            for ti,tol in enumerate([1e-7,1e-9] if mode=='broad' else [1e-9]):
                lanes=['native','fp32','fp4x2','previous-native','previous-fp4x2','fp4x2-split'] if mode=='pilot' else ['native','fp32','fp4x2','copt-cpu-auto','copt-gpu-tight']
                if mode=='broad':lanes=['native','fp32','fp4x2']
                shift=(i+repeat+ti)%len(lanes);lanes=lanes[shift:]+lanes[:shift]
                if (i+repeat+ti)%2:lanes.reverse()
                for lane in lanes:
                    actual=lane.removeprefix('previous-').removesuffix('-split')
                    previous=lane.startswith('previous-')
                    request=None if lane.startswith('copt') else dict(settings={**settings(actual),'tolerance':tol,'iteration_limit':1000 if mode=='pilot' else 20000,'check_interval':250 if mode=='pilot' else 500,'wall_ms':10000 if mode=='pilot' else 30000},
                        tensor=dict(control_interval=100,min_tile_nnz=128),fast=dict(host_reductions=True,host_preparation=True,combined=not lane.endswith('-split'),**({} if previous else dict(host_certificates=True,auto_schedule=mode!='pilot'))))
                    cells.append(dict(id=f'm{i:02d}-r{repeat}-t{ti}-{lane}',model_index=i,lane=lane,tolerance=tol,repeat=repeat,request=request,binary=ref(BASE/'scale-image-v3/executor' if previous else BINARY)))
    job_seconds=[(max(seconds,450) if min(targets)>=4000000 else 360 if max(m.get('rows',0),m.get('columns',0))>400000 or m.get('nonzeros',0)>3000000 else 240) if mode=='scale' else max(seconds,300) if mode=='broad' else seconds for m in models]
    cpu,gpu=accounting();require(cpu['development']+4*sum(job_seconds)*NS<=CPU_CAPS['development']*NS,'complete CPU cohort reservation')
    require(gpu['development']+sum(job_seconds)*NS<=GPU_CAPS['development']*NS,'complete GPU cohort reservation')
    if deferred:require(cpu['reporting']+4*300*len(models)*NS<=CPU_CAPS['reporting']*NS,'complete deferred history audit reservation')
    out=BASE/identity;out.mkdir(exist_ok=False)
    runner=out/'runner.py';runner.write_bytes(Path(__file__).read_bytes())
    put(out/'freeze.json',dict(mode=mode,model_version=model_version,models=models,unsupported_models=unsupported,cells=cells,memory_preflight=memory,deferred_history_audit=deferred,seconds_per_job=seconds,job_seconds=job_seconds,proofs=proofs,binary=ref(BINARY),image=ref(IMAGE),harness=ref(runner),design=ref(__file__),
        baseline_worker=ref(ROOT/'tools/lp_general_scale_copt.py'),evidence_worker=ref(ROOT/'tools/lp_general_scale_evidence.py'),claim='Descriptive development. Every failed, limited, unsupported and zero-FP4 cell retained. No confirmation.',
        independent_check='Fresh CPU process; unchanged original serial certificate routines, separately admitted against the historical checker. All intermediate and final endpoints checked.',
        primary='fresh-process time through independent strict original-model certificate and owned teardown',baseline_solve_seconds=30,
        tiers='Scale development starts at strict 1e-9; the complete historical roster retains both 1e-7 and 1e-9. No confirmation.'))

def run(identity,index):
    f=load(BASE/identity/'freeze.json');require(f['harness']==ref(__file__),'frozen harness')
    for key,path in [('binary',BINARY),('image',IMAGE),('baseline_worker',ROOT/'tools/lp_general_scale_copt.py')]:require(f[key]==ref(path),'frozen source '+key)
    if 'evidence_worker' in f:require(f['evidence_worker']==ref(ROOT/'tools/lp_general_scale_evidence.py'),'frozen evidence helper')
    m=f['models'][index];model=ROOT/m['model']['path'];require(ref(model)==m['model'],'frozen input')
    out=BASE/identity/f'm{index:02d}';out.mkdir(exist_ok=False);rows=[]
    if 'construction' in m:
        w=np.load(ROOT/m['construction']['path']);proof,_=assess(model,[dict(settings=settings(),primal=w['primal'].tolist(),dual=w['dual'].tolist())],out/'construction.jsonl')
        require(proof[0]['accepted'],'generated original witness rejected; no solver cell launched')
    for c in [c for c in f['cells'] if c['model_index']==index]:
        name=c['id'];response=out/(name+'.response.json');before=time.monotonic_ns();archive_ns=0
        if c['lane'].startswith('copt'):
            command=[str(PYTHON),str(ROOT/'tools/lp_general_scale_copt.py'),'--model',str(model),'--output',str(response),'--method',c['lane'],'--tolerance',str(c['tolerance']),'--seconds',str(f['baseline_solve_seconds'])]
            p=subprocess.run(command,text=True,capture_output=True)
        else:
            binary=ROOT/c.get('binary',f['binary'])['path'];require(ref(binary)==c.get('binary',f['binary']),'cell executable changed')
            p=subprocess.run([str(binary),'gpu-fast',str(model),str(IMAGE)],input=json.dumps(c['request'])+'\n',text=True,capture_output=True)
            archive_start=time.monotonic_ns();save_response(response,p.stdout);archive_ns=time.monotonic_ns()-archive_start
        elapsed=time.monotonic_ns()-before
        elapsed-=archive_ns
        (out/(name+'.stdout')).write_text(p.stdout if c['lane'].startswith('copt') else '')
        (out/(name+'.stderr')).write_text(p.stderr)
        require(p.returncode==0,'failed process; retained without retry '+name+' '+p.stderr[:200])
        r=json.loads(p.stdout) if not c['lane'].startswith('copt') else read_response(response);endpoints=[]
        if c['lane'].startswith('copt'):
            if r['has_solution']:endpoints=[dict(primal=r['primal'],dual=r['dual'])]
        else:
            require(sum(r['accepted'])==r['logical'] and sum(r['attempted'])==r['physical'],'work accounting')
            endpoints=[*r['assessments'],r]
        requests=[dict(settings={**settings(),'tolerance':c['tolerance']},primal=e['primal'],dual=e['dual']) for e in endpoints]
        # The primary endpoint ends after an independent FINAL certificate.
        # Rechecking the research history is separately charged audit work.
        final,check_ns=assess(model,requests[-1:],out/(name+'.final.jsonl')) if requests else ([],0)
        primary_ns=time.monotonic_ns()-before-archive_ns
        pending=f.get('deferred_history_audit',False) and len(requests)>1
        history,audit_ns=assess(model,requests[:-1],out/(name+'.serial.jsonl')) if len(requests)>1 and not pending else ([],0)
        proofs=history+final
        if not c['lane'].startswith('copt'):
            for e,proof in zip(endpoints[-1:] if pending else endpoints,proofs):
                expected={k:v for k,v in e['certificate'].items() if k!='model_sha256'}
                observed={k:v for k,v in proof.items() if k not in ['model_sha256','bound_proof']}
                require(expected==observed,'independent serial certificate mismatch')
        row=dict(cell=c,response=ref(response),serial=ref(out/(name+'.final.jsonl')) if requests else None,audit=ref(out/(name+'.serial.jsonl')) if len(requests)>1 and not pending else None,process_ns=elapsed,independent_ns=check_ns,audit_ns=audit_ns,
            complete_ns=primary_ns,archive_ns=archive_ns,audit_pending=pending,research_total_ns=time.monotonic_ns()-before,certified=bool(proofs and proofs[-1]['accepted']),status=r['status'],cost_ns=r['cost_ns'],
            logical=r.get('logical'),physical=r.get('physical'),accepted_product_work=r.get('accepted_product_work'),tile_count=r.get('tile_count'),
            device_bytes_upper=r.get('device_bytes_upper'),selected_initial_format=r.get('selected_initial_format'),gpu_confirmed=r.get('gpu_confirmed'),
            certificate=proofs[-1] if proofs else None,model=m['model'],family=m['family'],nonzeros=r['nonzeros'],recoveries=r.get('recoveries'))
        put(out/(name+'.cell.json'),row);rows.append(row)
        print(dict(cell=name,certified=row['certified'],status=row['status'],seconds=round(row['complete_ns']/1e9,3),execution_ms=r['cost_ns'].get('execution',0)/1e6),flush=True)
    put(out/'result.json',dict(status='complete',rows=rows,freeze=ref(BASE/identity/'freeze.json')))

def audit_rows(rows,out,include_final=False):
    out.mkdir(exist_ok=False);results=[]
    for row in rows:
        if row['cell']['lane'].startswith('copt'):continue
        r=read_response(ROOT/row['response']['path']);endpoints=[*r['assessments'],r] if include_final else r['assessments']
        requests=[dict(settings={**settings(),'tolerance':row['cell']['tolerance']},primal=e['primal'],dual=e['dual']) for e in endpoints]
        proofs,elapsed=assess(ROOT/row['model']['path'],requests,out/(row['cell']['id']+'.jsonl')) if requests else ([],0)
        require(len(proofs)==len(endpoints),'history assessment count')
        for e,proof in zip(endpoints,proofs):
            expected={k:v for k,v in e['certificate'].items() if k!='model_sha256'}
            observed={k:v for k,v in proof.items() if k not in ['model_sha256','bound_proof']}
            require(expected==observed,'deferred original-model certificate mismatch')
        results.append(dict(cell=row['cell']['id'],response=row['response'],assessments=len(proofs),audit_ns=elapsed))
    put(out/'result.json',dict(status='passed',rows=results,binary=ref(BINARY)))

def audit_public(identity):
    f=load(BASE/'scale-final-main-v1/freeze.json');c=next(c for c in f['cells'] if c['model_index']==20 and c['lane']=='native')
    p=BASE/'scale-final-main-v1/m20'/(c['id']+'.response.json')
    row=dict(cell=c,model=f['models'][20]['model'],response=ref(p))
    audit_rows([row],BASE/identity,True)
    put(BASE/identity/'disposition.json',dict(scope='Offline recheck of retained original trajectory only; no scientific rerun, missing timing reconstruction, or historical pass.',
        failed_reservation=ref(BASE/'resources/scale-final-main-v1-m20.settlement.json'),original=ref(p),source=ref(__file__)))

def tail(identity):
    source=BASE/'scale-final-main-v1/freeze.json';f=load(source);model=f['models'][20];cells=[]
    require(load(BASE/'scale-deferred-audit-v2/result.json')['status']=='passed','large audit admission')
    require(load(BASE/'scale-deferred-smoke-v1/result.json')['status']=='passed','complete deferred workflow admission')
    prior=[BASE/'scale-final-main-v1/m20',BASE/'scale-final-main-tail-v1/m00'];attempted=[]
    for c in f['cells']:
        if c['model_index']!=20:continue
        if any((p/(c['id']+'.response.json')).exists() for p in prior):attempted.append(c['id']);continue
        cells.append({**c,'model_index':0})
    require(len(cells)==3 and len(attempted)==2,'never-started PDS tail coverage')
    cpu,gpu=accounting()
    require(cpu['development']+4*360*NS<=CPU_CAPS['development']*NS and gpu['development']+360*NS<=GPU_CAPS['development']*NS,'complete tail reservation')
    require(cpu['reporting']+4*300*NS<=CPU_CAPS['reporting']*NS,'complete tail audit reservation')
    out=BASE/identity;out.mkdir(exist_ok=False);runner=out/'runner.py';runner.write_bytes(Path(__file__).read_bytes())
    put(out/'freeze.json',{**f,'models':[model],'cells':cells,'harness':ref(runner),'design':ref(__file__),
        'evidence_worker':ref(ROOT/'tools/lp_general_scale_evidence.py'),'deferred_history_audit':True,'job_seconds':[360],
        'proofs':[*f['proofs'],ref(BASE/'scale-deferred-audit-v2/result.json'),ref(BASE/'scale-deferred-smoke-v1/result.json')],
        'continuation_of':ref(source),'prior_continuation':ref(BASE/'scale-final-main-tail-v1/freeze.json'),'excluded_attempted':attempted,
        'claim':'Only three never-started PDS lanes; the two attempted cells and their missing timings remain unchanged.'})

def audit(identity,index):
    f=load(BASE/identity/'freeze.json');require(f['harness']==ref(__file__) and f['binary']==ref(BINARY),'frozen audit sources')
    group=BASE/identity/f'm{index:02d}'
    audit_rows(load(group/'result.json')['rows'],group/'history-audit')

def campaign(identity):
    f=load(BASE/identity/'freeze.json')
    for i in range(len(f['models'])):
        name=f'{identity}-m{i:02d}';require(not (BASE/'resources'/(name+'.reservation.json')).exists(),'never retry scientific cells')
        seconds=f.get('job_seconds',[f['seconds_per_job']]*len(f['models']))[i]
        command=['python3',str(ROOT/'tools/lp_general_budget.py'),'--id',name,'--phase','development','--seconds',str(seconds),'--gpu','--',
            'python3',str(ROOT/'tools/lp_mixed2_reuse_place.py'),'python3',str(ROOT/f['harness']['path']),'run','--id',identity,'--index',str(i)]
        import os
        require(subprocess.run(command,env={**os.environ,'PYTHONPATH':str(ROOT/'tools')}).returncode==0,'campaign stopped; preserve remaining missing cells')
        if f.get('deferred_history_audit'):
            command=['python3',str(ROOT/'tools/lp_general_budget.py'),'--id',name+'-audit','--phase','reporting','--seconds','300','--',
                'python3',str(ROOT/f['harness']['path']),'audit','--id',identity,'--index',str(i)]
            require(subprocess.run(command,env={**os.environ,'PYTHONPATH':str(ROOT/'tools')}).returncode==0,'history audit failed; no scientific retry')

def smoke(identity,deferred=False):
    out=BASE/identity;out.mkdir(exist_ok=False);cells=[]
    for lane in ['native','old-native','fp32','fp4x2','fp4x2-split','copt-cpu-auto','copt-gpu-pdlp','copt-gpu-tight']:
        fmt=lane.removeprefix('old-').removesuffix('-split')
        request=None if lane.startswith('copt') else dict(settings={**settings(fmt),'iteration_limit':32,'check_interval':16},tensor=dict(control_interval=8),fast=dict(host_reductions=not lane.startswith('old-'),host_preparation=True,host_certificates=True,auto_schedule=True,combined=not lane.endswith('-split')))
        cells.append(dict(id=lane,model_index=0,lane=lane,tolerance=1e-9,repeat=0,request=request))
    put(out/'freeze.json',dict(mode='admission',deferred_history_audit=deferred,models=[dict(model=ref(BASE/'scale-gpu-v1/dense.lpcsr'),family='dense')],cells=cells,
        binary=ref(BINARY),image=ref(IMAGE),harness=ref(__file__),baseline_worker=ref(ROOT/'tools/lp_general_scale_copt.py'),baseline_solve_seconds=2))
    run(identity,0)
    if deferred:
        audit(identity,0)
        rows=load(out/'m00/result.json')['rows']
        require(all(r['audit'] is None and r['audit_pending'] for r in rows if not r['cell']['lane'].startswith('copt')),'deferred file contract')
    put(out/'result.json',dict(status='passed',rows=load(out/'m00/result.json')['rows']))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['freeze','run','campaign','smoke','smoke-deferred','audit','audit-smoke','audit-public','tail']);p.add_argument('--id',required=True);p.add_argument('--mode',choices=['pilot','scale','broad'],default='pilot');p.add_argument('--targets',type=int,nargs='+',default=[1000000]);p.add_argument('--seconds',type=int,default=300);p.add_argument('--index',type=int);p.add_argument('--model-version',type=int);a=p.parse_args()
    if a.action=='freeze':freeze(a.id,a.mode,a.targets,a.seconds,a.model_version)
    elif a.action=='run':run(a.id,a.index)
    elif a.action=='smoke':smoke(a.id)
    elif a.action=='smoke-deferred':smoke(a.id,True)
    elif a.action=='audit':audit(a.id,a.index)
    elif a.action=='audit-smoke':audit_rows(load(BASE/'scale-smoke-v6/m00/result.json')['rows'],BASE/a.id)
    elif a.action=='audit-public':audit_public(a.id)
    elif a.action=='tail':tail(a.id)
    else:campaign(a.id)
