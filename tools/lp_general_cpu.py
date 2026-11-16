"""Original construction certificates and public input conversion admission."""
import argparse
import json
import subprocess
from lp_general_common import BASE,ROOT,load,put,ref,require
from lp_general_oracle import BINARY,settings
from lp_general_device import serial
from lp_general_public import parse,SOURCE

def run(identity):
    out=BASE/identity;out.mkdir(parents=True,exist_ok=False);rows=[]
    for i,item in enumerate(load(BASE/'models-development-v1/manifest.json')['models']):
        model=ROOT/item['model']['path'];w=load(ROOT/item['construction']['path'])
        commands=[dict(settings={**settings(), 'tolerance':t},primal=w['primal'],dual=w['dual']) for t in (1e-7,1e-9)]
        p=subprocess.run([str(BINARY),'assess',str(model)],input=''.join(json.dumps(c)+'\n' for c in commands),text=True,capture_output=True,check=True)
        results=[json.loads(s) for s in p.stdout.splitlines()];require(len(results)==2,'construction coverage')
        for j,(command,result) in enumerate(zip(commands,results)):
            require(result['accepted'],'constructed optimum did not certify')
            original=serial(model,dict(primal=w['primal'],dual=w['dual'],certificate=result),command['settings']['tolerance'],out,f'witness-{i}-{j}')
            rows.append(dict(model=item['model'],tolerance=command['settings']['tolerance'],certificate=result,serial=original))
    public=[]
    for item in load(BASE/'public-development-v1/manifest.json')['models']:
        name=item['family'];source=ROOT/item['source']['path'];copy=out/(name+'.mps');options=out/(name+'.options')
        options.write_text(f'presolve = off\nthreads = 3\nwrite_presolved_model_file = {copy}\n')
        argv=[str(ROOT/'target/native/highs-1.11.0/install/bin/highs'),str(source),'--options_file',str(options)]
        p=subprocess.run(argv,text=True,capture_output=True,cwd=out);(out/(name+'.native.log')).write_text(p.stdout+p.stderr)
        require(p.returncode==0,'native public model reader')
        original,_=parse(source);roundtrip,_=parse(copy);roundtrip['model_id']=original['model_id']
        require(original==roundtrip,'native MPS roundtrip differs '+name)
        public.append(dict(source=ref(source),roundtrip=ref(copy),model=item['model'],exact=True))
    put(out/'result.json',dict(status='passed',construction_assessments=len(rows),rows=rows,public=public,binary=ref(BINARY),source_license=ref(SOURCE/'LICENSE.txt')))
    print(dict(status='passed',construction_assessments=len(rows),public=len(public)),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--id',required=True);a=p.parse_args();run(a.id)
