"""Split schedule projection/cache/fusion contracts, including transactional faults."""
import argparse
from pathlib import Path
from lp_general_common import BASE,load,put,ref,require
from lp_general_models import generate
from lp_general_oracle import settings
from lp_general_device import serial
import lp_general_tensor as tensor


def run(identity,image,sanitizer):
    out=BASE/identity;out.mkdir(exist_ok=False);tensor.RUN_OUT=out;tensor.RUN_COUNT=0;records=[];pairs=0
    doc,_=generate('dense',257,41091);dense=out/'dense-tail.json';put(dense,doc)
    positive=out/'certificate-inequalities.json';put(positive,load(BASE/'tensor-gpu-v4/certificate-inequalities.json'))
    fields=['primal','dual','certificate','assessments','logical','physical','accepted','attempted','recoveries','restarts','accepted_product_work','physical_product_work']
    for model in [dense,positive]:
        for lanes in [1,4,8,32]:
            reference=None
            for fused in [True,False]:
                req=dict(settings={**settings('fp4x2'),'iteration_limit':128 if model==dense else 10000,'check_interval':64 if model==dense else 100},
                    tensor=dict(min_tile_nnz=128 if model==dense else 1,control_interval=32 if model==dense else 50),fast=dict(combined=False,lanes=lanes,fused_encode=fused))
                r,log=tensor.invoke(model,'gpu-fast',req,image,sanitizer);name=model.stem+f'-l{lanes}-f{fused}';put(out/(name+'.response.json'),r)
                if model==positive:require(r['certified'] and r['accepted_product_work'][1]>0,'split strict FP4 certificate')
                if fused:reference={k:r[k] for k in fields}
                else:require({k:r[k] for k in fields}==reference,'split fusion changed numerical work');pairs+=1
                for j,e in enumerate([*r['assessments'],r]):serial(model,{**e,'bound_proof':r['bound_proof']},1e-9,out,name+f'-a{j}')
                records.append(ref(out/(name+'.response.json')))
    for fault in ['cancel_after','force_recovery_after']:
        req=dict(settings={**settings('fp4x2'),'iteration_limit':128,'check_interval':64,fault:32},tensor=dict(min_tile_nnz=128,control_interval=32),fast=dict(combined=False,lanes=8))
        r,log=tensor.invoke(dense,'gpu-fast',req,image,sanitizer);put(out/(fault+'.response.json'),r)
        require(r['physical']>r['logical'],'rejected split work disappeared')
        if fault=='cancel_after':require(r['status']=='cancelled' and r['logical']==0 and r['physical']==32,'split cancellation')
        else:require(r['recoveries'] and all(e['restored_exact'] for e in r['recoveries']),'split restoration')
        for j,e in enumerate([*r['assessments'],r]):serial(dense,{**e,'bound_proof':r['bound_proof']},1e-9,out,fault+str(j))
        records.append(ref(out/(fault+'.response.json')))
    put(out/'result.json',dict(status='passed',binary=ref(tensor.BINARY),image=ref(image),sanitizer=sanitizer,solves=len(records),fused_pairs=pairs,records=records,source=ref(__file__)))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--id',required=True);p.add_argument('--image',type=Path,required=True);p.add_argument('--sanitizer',choices=['memcheck','racecheck','initcheck','synccheck']);a=p.parse_args();run(a.id,a.image,a.sanitizer)
