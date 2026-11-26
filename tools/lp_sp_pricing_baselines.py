"""Fresh-study adapters to unchanged retained solvers and strict checker.

Only new study objects are written. The original generated rational coefficients
must survive the portable FP64 representation exactly; construction witnesses
are never passed to a solver. Installed COPT license contents are never inspected.
"""
import argparse
import json
import math
import os
from pathlib import Path
import sys
import time
import numpy as np
from lp_sp_pricing_budget import ROOT, BASE, binding, put
from lp_billion_arrays import write, read
from lp_billion_owned_process import execute
from lp_general_oracle import settings

sys.path.insert(0,str(ROOT/"research/lp-sp-pricing/python"))
from sp_pricing.exact import rational

RETAINED=Path('/storage/ai-optimizer-billion-v1')
PYTHON=ROOT/'artifacts/gpup-copt-adapter-env/venv/bin/python'


def images():
    image=json.loads((RETAINED/'image-v11/binding.json').read_text())
    result={}
    for name,item in image['files'].items():
        path=RETAINED/item['path']
        observed=binding(path)
        if observed['sha256']!=item['sha256'] or observed['bytes']!=item['bytes']:
            raise RuntimeError('retained image changed: '+name)
        result[name]=observed
    checker=RETAINED/'image-v1/executor'
    # Bind the checker to its original image manifest, rather than accepting
    # an arbitrary executable found at the historical pathname.
    old=json.loads((RETAINED/'image-v1/binding.json').read_text())
    expected=old['executor']
    result['checker']=binding(checker)
    if result['checker']['sha256']!=expected['sha256']:
        raise RuntimeError('original checker changed')
    return result


def portable(model,path):
    def exact_float(value):
        value=rational(value);approx=float(value)
        if not math.isfinite(approx) or rational(approx)!=value:
            raise ValueError('original coefficient not exactly representable in FP64')
        return approx
    n,m=len(model['c']),len(model['b'])
    offsets=[0];indices=[];values=[]
    for row in model['A']:
        if len(row)!=n:raise ValueError('original matrix dimensions')
        for j,value in enumerate(row):
            if rational(value):indices.append(j);values.append(exact_float(value))
        offsets.append(len(values))
    objectives=[j for j,value in enumerate(model['c']) if rational(value)]
    arrays={
        'column_ids':write(BASE,range(n),'u32le'),'row_ids':write(BASE,range(m),'u32le'),
        'column_lower':write(BASE,[-math.inf]*n),'column_upper':write(BASE,[math.inf]*n),
        'row_lower':write(BASE,[-math.inf]*m),'row_upper':write(BASE,list(map(exact_float,model['b']))),
        'offsets':write(BASE,offsets,'u64le'),'indices':write(BASE,indices,'u32le'),
        'values':write(BASE,values),'objective_indices':write(BASE,objectives,'u32le'),
        'objective_values':write(BASE,[exact_float(model['c'][j]) for j in objectives])}
    put(path,dict(schema_version=1,model_id=path.parent.name,rows=m,columns=n,nonzeros=len(values),sense='maximize',offset=0.,arrays=arrays))
    return binding(path)


def request(seconds):
    config=settings('fp4x2')
    config.update(wall_ms=int(1000*seconds),check_interval=500)
    return dict(settings=config,tensor=dict(control_interval=100,min_tile_nnz=128),profile=True,
        fast=dict(host_reductions=True,host_preparation=True,host_certificates=True,
                  auto_schedule=True,gpu_preparation=True,gpu_packing=True,
                  gpu_control=True,gpu_feasibility=True))


def copt(model,output,seconds,roundtrip=False):
    from scipy import sparse
    from lp_billion_copt_run import read_model,ptr,installation,roundtrip as check_import
    from lp_billion_copt_diagnostic import DiagnosticNative,settings as copt_settings,Journal,DurableClock,cooperative_solve
    from lp_copt import gpu_started
    journal=Journal(output/'phases.jsonl');clock=DurableClock(journal);api=None
    try:
        installed=installation();clock.enter('input_hash_validation')
        doc,data=read_model(model,BASE)
        clock.enter('library_environment');api=DiagnosticNative()
        params=copt_settings('scale-off',True,12000.)
        clock.enter('configuration');api.configure(params)
        log=output/'copt.log';api.call('SetLogFile',api.prob,str(log).encode())
        clock.enter('csr_to_csc')
        m,n=doc['rows'],doc['columns']
        csr=sparse.csr_matrix((data['values'],data['indices'],data['offsets']),shape=(m,n),copy=False)
        if not csr.has_canonical_format:raise ValueError('canonical CSR required')
        matrix=csr.tocsc(copy=True);objective=np.zeros(n)
        objective[data['objective_indices']]=data['objective_values']
        clock.enter('model_import')
        api.call('LoadProb',api.prob,n,m,-1,0.,ptr(objective),ptr(matrix.indptr),None,
            ptr(matrix.indices),ptr(matrix.data),None,ptr(data['column_lower']),ptr(data['column_upper']),
            None,ptr(data['row_lower']),ptr(data['row_upper']),None,None)
        if roundtrip:
            clock.enter('import_roundtrip');check_import(api,doc,data,matrix,objective)
        clock.enter('solve_configuration');api.configure({'TimeLimit':seconds})
        clock.enter('solve_call_opaque');start=time.monotonic_ns()
        code,interrupts=cooperative_solve(api,seconds,journal)
        native_ns=time.monotonic_ns()-start
        clock.enter('endpoint_extraction')
        status=api.get('LpStatus',True);has=bool(api.get('HasLpSol',True));endpoint=None
        if has:
            x,y=np.empty(n),np.empty(m)
            api.call('GetLpSolution',api.prob,ptr(x),None,ptr(y),None)
            np.negative(y,out=y)
            if not np.all(np.isfinite(x)) or not np.all(np.isfinite(y)):raise ArithmeticError('nonfinite endpoint')
            endpoint=dict(primal=write(BASE,x),dual=write(BASE,y))
        result=dict(status=status,has_solution=has,endpoint=endpoint,parameters=params,
            solve_returncode=code,interrupts=interrupts,model_sha256=binding(model)['sha256'],
            installation=installed,roundtrip_checked=roundtrip,native_ns=native_ns,
            returned_before_deadline=native_ns<=int(seconds*1e9),
            pdlp_iterations=api.get('PDLPIter',True))
        clock.enter('teardown');api.close();api=None
        result['gpu_confirmed']=gpu_started(log.read_text()) if log.exists() else False
        result['profile']=clock.finish();put(output/'response.json',result)
    finally:
        if api is not None:api.close()
        journal.close()


def launch(lane,model,rational_model,out,seconds,outer,config=None,roundtrip=False):
    out.mkdir(exist_ok=False)
    if lane=='copt_scale_off':
        command=[str(PYTHON),'-B',__file__,'copt',str(model),str(out),str(seconds)]
        if roundtrip:command.append('--roundtrip')
        stdin=None
    elif lane=='retained_image_v11':
        image=images();payload=request(seconds);put(out/'request.json',payload)
        command=[image['executor']['path'],'solve',str(model),str(BASE),image['tensor.cubin']['path']]
        stdin=json.dumps(payload)+'\n'
    elif lane=='practical':
        config=config or {}
        command=[str(PYTHON),'-B',str(ROOT/'tools/lp_sp_pricing_run.py'),str(rational_model),str(out/'response.json'),
                 '--seconds',str(seconds),'--operations','200000000','--market','flow']
        if config.get('gpu'):
            command += ['--gpu-library',str(ROOT/'research/lp-sp-pricing/target/release/liblp_sp_pricing.so'),
                        '--precision',config.get('precision','fp32x2'),'--batch',str(config.get('batch',32))]
            if config.get('sparse',True):command.append('--sparse')
        stdin=None
    else:raise ValueError('unknown lane')
    put(out/'started.json',dict(lane=lane,model=binding(model),rational_model=binding(rational_model),
        seconds=seconds,outer_seconds=outer,command=command,configuration=config))
    process=execute(command,out/'stdout.jsonl',out/'stderr',outer,stdin)
    put(out/'process.json',process)
    if lane=='retained_image_v11' and process['returncode']==0 and not process['timed_out']:
        put(out/'response.json',json.loads((out/'stdout.jsonl').read_text()))
    return process


def audit(lane,model,rational_model,out):
    """One cold strict checker process; check every image assessment as well."""
    started=time.monotonic_ns();response_path=out/'response.json'
    if not response_path.exists():
        result=dict(accepted=False,reason='missing_response',checks=0)
    else:
        response=json.loads(response_path.read_text());endpoint=response.get('endpoint')
        exact=None
        if lane=='practical':
            from lp_sp_pricing_verify import verify
            proof=response.get('certificate')
            exact=verify(json.loads(rational_model.read_text()),response) if proof else dict(accepted=False,reason='no_endpoint')
            if exact['accepted'] and proof['status']=='optimal':
                endpoint=dict(primal=write(BASE,[float(rational(v)) for v in proof['x']]),
                              dual=write(BASE,[-float(rational(v)) for v in proof['y']]))
            # The retained checker uses minimization-normalized row duals;
            # both the vendor adapter and practical adapter negate max duals.
        if endpoint is None:
            result=dict(accepted=False,reason='no_optimal_endpoint',checks=0,exact=exact)
        else:
            config=response['settings'] if lane=='retained_image_v11' else settings('native')
            endpoints=[endpoint]+([a['endpoint'] for a in response.get('assessments',[])] if lane=='retained_image_v11' else [])
            requests=[dict(settings=config,endpoint=e) for e in endpoints]
            put(out/'audit-requests.json',requests)
            checker=images()['checker']['path']
            proc=execute([checker,'assess',str(model),str(BASE)],out/'audit-stdout.jsonl',out/'audit-stderr',60,
                         ''.join(json.dumps(q)+'\n' for q in requests))
            put(out/'audit-process.json',proc)
            if proc['returncode']!=0 or proc['timed_out']:raise RuntimeError('cold strict checker failed')
            proofs=[json.loads(s) for s in (out/'audit-stdout.jsonl').read_text().splitlines()]
            if len(proofs)!=len(requests):raise RuntimeError('incomplete endpoint coverage')
            for p in proofs:
                if p['model_sha256']!=binding(model)['sha256'] or p['tolerance']!=1e-9:
                    raise RuntimeError('strict original-model identity differs')
            if lane=='retained_image_v11':
                for proof,claim in zip(proofs,[response,*response.get('assessments',[])]):
                    if any(proof[k]!=v for k,v in claim['certificate'].items()):
                        raise RuntimeError('independent original assessment differs')
            result=dict(accepted=bool(proofs[0]['accepted']),checks=len(proofs),exact=exact,
                        tolerance=1e-9,proofs=proofs,checker=binding(checker))
    result['elapsed_ns']=time.monotonic_ns()-started
    put(out/'audit.json',result)
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['copt']);p.add_argument('model',type=Path)
    p.add_argument('output',type=Path);p.add_argument('seconds',type=float);p.add_argument('--roundtrip',action='store_true')
    args=p.parse_args();copt(args.model,args.output,args.seconds,args.roundtrip)
