"""Exact independent admission of runtime bound implications and certificates."""
import argparse
import json
import random
import subprocess
from lp_general_common import ROOT,BASE,load,put,ref,require
from lp_general_oracle import BINARY,settings
from lp_general_implied import verify
from lp_general_device import serial
from lp_general_models import generate

def run(identity):
    out=BASE/identity;out.mkdir(parents=True,exist_ok=False);rows=[]
    def call(model,commands,kind,name):
        p=subprocess.run([str(BINARY),kind,str(model)],input=''.join(json.dumps(q)+'\n' for q in commands),capture_output=True,text=True)
        (out/(name+'.response.jsonl')).write_text(p.stdout);(out/(name+'.stderr')).write_text(p.stderr)
        require(p.returncode==0,'bound producer failed '+name)
        r=[json.loads(s) for s in p.stdout.splitlines()];require(len(r)==len(commands),'bound response coverage');return r
    models=[ROOT/r['model']['path'] for r in load(BASE/'models-development-v1/manifest.json')['models']]
    models += [ROOT/r['model']['path'] for r in load(BASE/'public-development-v1/manifest.json')['models']]
    for i in range(64):
        model,_=generate('irregular',9,799000+i);rng=random.Random(799000+i)
        for v in model['variables']:
            if rng.randrange(2):v['upper']=dict(kind='positive_infinity')
            if rng.randrange(2):v['lower']=dict(kind='negative_infinity')
        path=out/f'adversarial-{i}.model.json';put(path,model);models.append(path)
    for i,model in enumerate(models):
        result=call(model,[dict(settings=settings())],'tighten',f'proof-{i}')[0]
        verify(load(model),result['model'],result['bound_proof'])
        rows.append(dict(model=ref(model),steps=len(result['bound_proof']),verified=True))
    external=[]
    for r in load(BASE/'external-reference-v2/result.json')['rows']:
        model=ROOT/r['model']['path'];native=load(ROOT/r['native']['path']);x=[v['value'] for v in native['record']['candidate']['values']];y=native['diagnostics']['dual']
        requests=[dict(settings={**settings(),'tolerance':t},primal=x,dual=y) for t in [1e-7,1e-9]]
        responses=call(model,requests,'assess-proven','external-'+str(r['model_index']))
        for j,(q,c) in enumerate(zip(requests,responses)):
            check=serial(model,dict(primal=x,dual=y,certificate=c),q['settings']['tolerance'],out,f'external-{r["model_index"]}-{j}')
            external.append(dict(family=r['family'],certificate=c,serial=check))
    put(out/'result.json',dict(status='passed',binary=ref(BINARY),models=len(rows),rows=rows,external=external,
        accepted=sum(r['certificate']['accepted'] for r in external),assessments=len(external)))
    print(dict(models=len(rows),accepted=sum(r['certificate']['accepted'] for r in external),assessments=len(external)),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--id',required=True);run(p.parse_args().id)
