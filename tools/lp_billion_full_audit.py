"""Strict original-model endpoint audit with exact identity-based proof reuse."""
import argparse,json,select,subprocess,time
from pathlib import Path
from lp_billion_common import BASE,ROOT,put,load,ref,resolve,require
from lp_general_oracle import settings
from lp_billion_owned_process import stop_owned

def requests(response,project=True):
    require(response['has_solution'] if not project else 'endpoint' in response,'available endpoint')
    config=response['settings'] if project else settings('native')
    require(config['tolerance']==1e-9,'unchanged strict certificate tolerance')
    endpoints=[response,*response['assessments']] if project else [response]
    unique=[];indices={};mapping=[]
    for endpoint in endpoints:
        q=dict(settings=config,endpoint=endpoint['endpoint'])
        key=json.dumps(q,sort_keys=True,separators=(',',':'),allow_nan=False)
        if key not in indices:indices[key]=len(unique);unique.append(q)
        mapping.append(indices[key])
    return unique,mapping,endpoints

def validate(results,mapping,endpoints,model_hash,project):
    require(len(mapping)==len(endpoints) and len(results)==max(mapping)+1,'full endpoint coverage')
    for index,endpoint in zip(mapping,endpoints):
        proof=results[index]
        require(proof['model_sha256']==model_hash and proof['tolerance']==1e-9,'strict original-model identity')
        if project:
            for key,value in endpoint['certificate'].items():
                require(proof[key]==value,'original serial certificate differs '+key)
    return bool(results[0]['accepted'])

def audit(manifest,index):
    frozen=load(manifest);cell=frozen['cells'][index];out=BASE/(cell['id']+'-full-audit');out.mkdir(exist_ok=False)
    response_path=BASE/cell['id']/'response.json'
    if not response_path.exists():
        settled=load(BASE/'resources'/(cell['id']+'.settlement.json'))
        require(settled['status']=='refused','missing response must have failed receipt')
        put(out/'result.json',dict(status='retained_missing_response',cell=cell['id'],certified=False,checks=0))
        return
    response=load(response_path);project=cell['lane'] in ['native','fp32','fp4x2']
    if not project and not response['has_solution']:
        put(out/'result.json',dict(status='no_endpoint',response=ref(response_path),certified=False,checks=0,
            final_check_ns=0,offline_audit_ns=0,elapsed_ns=0))
        return
    qs,mapping,endpoints=requests(response,project);put(out/'requests.json',dict(requests=qs,mapping=mapping))
    checker=resolve(frozen['checker']);model=resolve(cell['model'])
    results=[];start=time.monotonic_ns()
    allowance=cell.get("audit_seconds",cell.get("check_seconds"))
    require(allowance is not None and allowance>30,"checker cleanup margin")
    deadline=time.monotonic()+allowance-30
    with (out/'stderr').open('w') as err,(out/'stdout.jsonl').open('w') as raw:
        p=subprocess.Popen([str(checker),'assess',str(model),str(BASE)],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=err,text=True)
        first_done=None
        try:
            for i,q in enumerate(qs):
                p.stdin.write(json.dumps(q,allow_nan=False)+'\n');p.stdin.flush()
                remaining=deadline-time.monotonic()
                require(remaining>0 and select.select([p.stdout],[],[],remaining)[0],'owned checker deadline; retain partial audit')
                line=p.stdout.readline();require(bool(line),'checker ended before full endpoint coverage')
                raw.write(line);raw.flush();results.append(json.loads(line))
                if i==0:first_done=time.monotonic_ns()
            tail_done=time.monotonic_ns();p.stdin.close()
            remaining=deadline-time.monotonic();require(remaining>0,'owned checker deadline')
            require(p.wait(timeout=remaining)==0 and p.stdout.read()=='','independent checker completion')
        finally:
            stop_owned(p)
            p.stdout.close()
            if not p.stdin.closed:p.stdin.close()
    finish=time.monotonic_ns()
    certified=validate(results,mapping,endpoints,cell['model']['sha256'],project)
    if project:require(certified==response['certified'],'strict final certificate status')
    # Final checking includes cold original input and actual process teardown;
    # only additional intermediate checks are excluded as offline research audit.
    offline=tail_done-first_done
    final=(first_done-start)+(finish-tail_done)
    require(final+offline==finish-start,'disjoint full checker cost coverage')
    put(out/'result.json',dict(status='passed',response=ref(response_path),model=cell['model'],checker=ref(checker),
        certified=certified,checks=len(qs),covered_endpoints=len(mapping),proof_mapping=mapping,results=results,
        final_check_ns=final,offline_audit_ns=offline,elapsed_ns=finish-start,
        timing_scope='final proof includes cold input and process teardown; distinct intermediate checks are offline audit',
        source=ref(__file__)))
    print(dict(cell=cell['id'],strict_certified=certified,checks=len(qs),endpoints=len(mapping),seconds=(finish-start)/1e9),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('manifest',type=Path);p.add_argument('index',type=int);a=p.parse_args();audit(a.manifest,a.index)
