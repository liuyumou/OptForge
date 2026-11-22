"""Small CPU/GPU native COPT admission with independent strict scalar checks."""
import argparse
import copy
import json
import subprocess
import sys
import time
from lp_billion_common import BASE, ROOT, put, load, ref, require
from lp_general_models import generate
from lp_general_oracle import settings


def fixtures():
    finite=lambda v:dict(kind='finite',value=v)
    neg=dict(kind='negative_infinity');pos=dict(kind='positive_infinity')
    variables=[dict(id=7,domain='continuous',lower=finite(0.),upper=finite(4.)),
               dict(id=10,domain='continuous',lower=neg,upper=pos),
               dict(id=13,domain='continuous',lower=finite(2.),upper=finite(2.)),
               dict(id=16,domain='continuous',lower=finite(0.),upper=finite(1.))]
    rows=[dict(id=11,lower=finite(1.),upper=finite(3.),terms=[dict(variable_id=7,coefficient=1.)]),
          dict(id=16,lower=finite(0.),upper=finite(0.),terms=[dict(variable_id=10,coefficient=1.)]),
          dict(id=21,lower=neg,upper=pos,terms=[])]
    base=dict(schema_version=1,model_id='copt-native-geometry',variables=variables,constraints=rows,
              objective=dict(sense='minimize',offset=2.,terms=[dict(variable_id=7,coefficient=1.),dict(variable_id=16,coefficient=1.)]))
    cases=[]
    for sense in ['minimize','maximize']:
        doc=copy.deepcopy(base);doc['objective']['sense']=sense
        if sense=='maximize':
            for t in doc['objective']['terms']:t['coefficient']*=-1
        cases.append((sense,doc,'certified',30.))
    doc=copy.deepcopy(base);doc['variables'][0]['upper']=finite(.5)
    cases.append(('infeasible',doc,'infeasible',30.))
    doc=copy.deepcopy(base);doc['constraints']=[];doc['objective']['terms']=[dict(variable_id=10,coefficient=-1.)]
    cases.append(('unbounded',doc,'unbounded',30.))
    doc=copy.deepcopy(base);doc['constraints']=[];doc['objective']['terms']=[dict(variable_id=7,coefficient=1.)]
    cases.append(('empty-matrix',doc,'certified',30.))
    cases.append(('preparation-deadline',copy.deepcopy(base),'not_started',1e-12))
    for family in ['irregular','rectangular','dense_blocks','ill_scaled','degenerate','dense']:
        doc,_=generate(family,33,902000)
        cases.append((family,doc,'endpoint_checked',30.))
    return cases


def admit(identity):
    out=BASE/identity;out.mkdir(exist_ok=False)
    executor=BASE/'image-v1/executor';rows=[]
    checker_binding=ref(executor)
    for gpu in [False,True]:
      for base_name,doc,expect,wall in fixtures():
        name=('gpu-' if gpu else 'cpu-')+base_name
        model=out/(name+'.json');put(model,doc)
        p=subprocess.run([str(executor),'convert',str(model),str(BASE)],text=True,capture_output=True)
        require(p.returncode==0,'original conversion '+p.stderr)
        compact=out/(name+'.arrays.json');put(compact,json.loads(p.stdout))
        response=out/(name+'.response.json')
        started=time.monotonic_ns()
        p=subprocess.run([sys.executable,'-B',str(ROOT/'tools/lp_billion_copt_run.py'),str(compact),str(response),
                          '--roundtrip','--admission','--wall-seconds',str(wall),*(['--gpu'] if gpu else [])],text=True,capture_output=True)
        process_ns=time.monotonic_ns()-started
        (out/(name+'.stdout')).write_text(p.stdout);(out/(name+'.stderr')).write_text(p.stderr)
        require(p.returncode==0,'COPT admission '+name+': '+p.stderr[-3000:])
        r=load(response);profile=r['profile']
        require(profile['total_ns']<=process_ns and sum(profile['exclusive_ns'].values())==profile['total_ns'],'COPT process cost coverage')
        require(r['model_sha256']==ref(compact)['sha256'] and r['roundtrip_checked'],'exact imported model binding')
        proof=None;check_ns=0
        if r['has_solution']:
            request=dict(settings=settings('native'),endpoint=r['endpoint'])
            require(request['settings']['tolerance']==1e-9,'strict certificate tolerance')
            put(out/(name+'.check-request.json'),request)
            began=time.monotonic_ns()
            p=subprocess.run([str(executor),'assess',str(compact),str(BASE)],input=json.dumps(request)+'\n',text=True,capture_output=True)
            check_ns=time.monotonic_ns()-began
            (out/(name+'.check-stdout')).write_text(p.stdout);(out/(name+'.check-stderr')).write_text(p.stderr)
            require(p.returncode==0,'strict original-model check '+p.stderr)
            proof=json.loads(p.stdout)
            require(proof['model_sha256']==ref(compact)['sha256'],'checker original model')
            put(out/(name+'.check.json'),proof)
        if expect=='certified':require(r['optimal'] and proof is not None and proof['accepted'],'strict geometry certificate '+name)
        if expect=='infeasible':require(r['status']==2 and (proof is None or not proof['accepted']),'infeasible native status')
        if expect=='unbounded':require(r['status']==3 and (proof is None or not proof['accepted']),'unbounded native status')
        if expect=='not_started':require(not r['solve_called'] and r['deadline_before_solve'] and not r['has_solution'],'preparation counted in deadline')
        if expect=='endpoint_checked':require(proof is not None or (not r['optimal'] and r['status'] in [2,3,4,5,6,7,8,9,10]),'generated endpoint checked or explicit non-optimal terminal outcome')
        costs=dict(profile['exclusive_ns'],process_imports_serialization_cleanup=process_ns-profile['total_ns'],independent_final_check=check_ns)
        require(sum(costs.values())==process_ns+check_ns,'complete COPT coverage')
        rows.append(dict(name=name,response=ref(response),model=ref(compact),status=r['status'],
            certified=proof['accepted'] if proof else False,check=ref(out/(name+'.check.json')) if proof else None,
            process_ns=process_ns,final_check_ns=check_ns,complete_ns=process_ns+check_ns,exclusive_ns=costs,
            timing_scope='CPU/GPU adapter admission only; not a billion-scale performance cell'))
        print(dict(case=name,status=r['status'],strict_accepted=proof['accepted'] if proof else None),flush=True)
    import platform, numpy, scipy
    put(out/'result.json',dict(python=platform.python_version(),numpy=numpy.__version__,scipy=scipy.__version__,status='passed',cases=rows,checker=checker_binding,
        adapter=ref(ROOT/'tools/lp_billion_copt_run.py'),installation=r['installation'],gpu_executed=any(load(BASE/r['response']['path'])['gpu_confirmed'] for r in rows),
        billion_solves=0,full_cohort_frozen=False))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--id',required=True);a=p.parse_args();admit(a.id)
