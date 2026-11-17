"""Long sparse rows: CPU/GPU rational enclosures and independent fixed updates."""
import argparse
from fractions import Fraction as Q
import json
from pathlib import Path
import subprocess
from lp_general_common import BASE,put,ref,require
from lp_general_device import BINARY,bits,fixed_reference
from lp_general_oracle import settings
from lp_general_models import generate

def run(identity,image=None,sanitizer=None):
    out=BASE/identity;out.mkdir(parents=True,exist_ok=False)
    doc,_=generate('rectangular',4097,790087);doc['constraints']=doc['constraints'][:3]
    for i,row in enumerate(doc['constraints']):
        row['lower']=dict(kind='finite',value=-1.);row['upper']=dict(kind='finite',value=1.)
        row['terms']=[dict(variable_id=3*j+7,coefficient=((j*17+i*11)%101-50)/37) for j in range(4097) if (j*17+i*11)%101!=50]
    model=out/'model.json';put(model,doc)
    formats=['native','fp32','fp4x1','fp4x2']
    def call(command,requests,name):
        argv=[str(BINARY),command,str(model)]+([str(image)] if image else [])
        log=out/(name+'.sanitizer')
        if sanitizer:argv=['/usr/local/cuda/bin/compute-sanitizer','--tool',sanitizer,'--error-exitcode','99','--log-file',str(log),*argv]
        put(out/(name+'.requests.json'),requests)
        p=subprocess.run(argv,input=''.join(json.dumps(r)+'\n' for r in requests),text=True,capture_output=True)
        (out/(name+'.jsonl')).write_text(p.stdout);(out/(name+'.stderr')).write_text(p.stderr)
        require(p.returncode==0,'long-row process')
        if sanitizer:require('ERROR SUMMARY: 0 errors' in log.read_text() or (sanitizer=='racecheck' and 'RACECHECK SUMMARY: 0 hazards' in log.read_text()),'long-row sanitizer')
        result=[json.loads(s) for s in p.stdout.splitlines()];require(len(result)==len(requests),'long-row coverage');return result
    requests=[]
    for tr in [False,True]:
        n=3 if tr else 4097;anchor=[((j*11)%17-8)/19 for j in range(n)]
        vector=[a+((j*13)%23-11)/29 for j,a in enumerate(anchor)]
        requests.extend(dict(settings=settings(f),transpose=tr,vector=vector,anchor=anchor) for f in formats)
    responses=call('gpu-probe' if image else 'operator',requests,'products');products=0
    for request,r in zip(requests,responses):
        matrix=r['operator']['columns' if request['transpose'] else 'rows']
        for i,(lo,hi) in enumerate(zip(matrix['offsets'],matrix['offsets'][1:])):
            exact=sum((Q(matrix['original'][j])*Q(request['vector'][matrix['indices'][j]]) for j in range(lo,hi)),Q(0))
            require(abs(Q(r['product']['values'][i])-exact)<=Q(r['product']['bounds'][i]),'long-row enclosure');products+=1
    if image:
        requests=[dict(settings=settings(f),count=5) for f in formats]
        for f,r in zip(formats,call('gpu-fixed',requests,'updates')):
            x,y=fixed_reference(r,f);require(r['valid'] and bits(x)==bits(r['primal']) and bits(y)==bits(r['dual']),'long-row fixed updates')
    put(out/'result.json',dict(status='passed',products=products,fixed_cases=4 if image else 0,
        binary=ref(BINARY),image=ref(image) if image else None,sanitizer=sanitizer))
    print(dict(status='passed',products=products,sanitizer=sanitizer),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--id',required=True);p.add_argument('--image',type=Path)
    p.add_argument('--sanitizer',choices=['memcheck','racecheck','initcheck','synccheck']);a=p.parse_args();run(a.id,a.image,a.sanitizer)
