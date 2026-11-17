"""Long remainder rows and more than four tensor tiles per half-row admission."""
import argparse
import random
from pathlib import Path
from lp_general_common import BASE,put,ref,require
from lp_general_models import generate
from lp_general_oracle import settings
from lp_general_device import serial
from lp_general_fast import expected
import lp_general_tensor as tensor


def run(identity,image,sanitizer):
    out=BASE/identity;out.mkdir(exist_ok=False);tensor.RUN_OUT=out;tensor.RUN_COUNT=0
    doc,_=generate('dense',257,41091);model=out/'dense-tail.json';put(model,doc);records=[];products=0;solves=0
    for fmt in ['fp4x1','fp4x2','fp4x3','fp4x4']:
        request=dict(settings=settings(fmt),tensor=dict(min_tile_nnz=128,incremental=True),fast=dict(combined=True,adaptive_rows=True))
        cpu,_=tensor.invoke(model,'tensor-operator',request);tensor.packing(cpu)
        require(max(b-a for a,b in zip(cpu['packed']['rows']['offsets'],cpu['packed']['rows']['offsets'][1:]))>4,'long tile reduction required')
        require(max(b-a for a,b in zip(cpu['packed']['columns']['residual']['offsets'],cpu['packed']['columns']['residual']['offsets'][1:]))>=128,'long remainder row required')
        for tr in [False,True]:
            n=len(cpu['operator']['rows' if tr else 'columns']['offsets'])-1;rng=random.Random(41093)
            vector=[rng.uniform(-1,1)*2.**(i%13-6) for i in range(n)];anchor=[v*.75 for v in vector]
            request.update(transpose=tr,vector=vector,anchor=anchor);oracle=expected(cpu,request,32);name=fmt+'-'+str(tr)
            put(out/(name+'.expected.json'),oracle);put(out/(name+'.request.json'),request)
            if image:
                r,log=tensor.invoke(model,'gpu-fast-probe',request,image,sanitizer);put(out/(name+'.response.json'),r);(out/(name+'.log')).write_text(log)
                require(r['proposal_values']==oracle and r['enclosed'] is False,'combined long reduction arithmetic');records.append(ref(out/(name+'.response.json')))
            products+=len(oracle)
    if image:
        for fmt in ['native','fp32','fp4x2','fp4x4']:
            request=dict(settings={**settings(fmt),'iteration_limit':128,'check_interval':64},tensor=dict(control_interval=32,min_tile_nnz=128),fast=dict(combined=True))
            r,log=tensor.invoke(model,'gpu-fast',request,image,sanitizer);name=fmt+'-solve';put(out/(name+'.response.json'),r)
            for j,e in enumerate([*r['assessments'],r]):serial(model,{**e,'bound_proof':r['bound_proof']},1e-9,out,name+str(j))
            records.append(ref(out/(name+'.response.json')));solves+=1
        empty=dict(doc);empty['constraints']=[];empty['objective']={**doc['objective'],'terms':[]};mp=out/'empty-rows.json';put(mp,empty)
        for fmt in ['native','fp32','fp4x2']:
            request=dict(settings={**settings(fmt),'iteration_limit':32,'check_interval':16},tensor=dict(control_interval=16))
            r,log=tensor.invoke(mp,'gpu-fast',request,image,sanitizer);name=fmt+'-empty';put(out/(name+'.response.json'),r)
            require(r['certified'] and r['rows']==0,'empty original certificate')
            serial(mp,r,1e-9,out,name);records.append(ref(out/(name+'.response.json')));solves+=1
    put(out/'result.json',dict(status='passed',binary=ref(tensor.BINARY),image=ref(image) if image else None,products=products,solves=solves,sanitizer=sanitizer,records=records,source=ref(__file__)))
    print(dict(status='passed',products=products,solves=solves,sanitizer=sanitizer),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--id',required=True);p.add_argument('--image',type=Path);p.add_argument('--sanitizer',choices=['memcheck','racecheck','initcheck','synccheck']);a=p.parse_args();run(a.id,a.image,a.sanitizer)
