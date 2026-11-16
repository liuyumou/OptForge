"""Independent decoded proposal arithmetic and original-certificate admission."""
import argparse
import json
import math
import random
from pathlib import Path

from lp_general_common import BASE, ROOT, load, put, ref, require
from lp_general_models import generate, FAMILIES
from lp_general_oracle import settings
from lp_general_device import f32, product as original_product, serial
import lp_general_tensor as tensor


def vector_components(vector, k):
    parts=[];exponents=[]
    for lo in range(0,len(vector),32):
        remainder=[f32(v) for v in vector[lo:lo+32]]+[0.]*(32-len(vector[lo:lo+32]))
        block=[];scales=[]
        for _ in range(k):
            largest=max(abs(v) for v in remainder)
            e=max(-48,math.floor(math.log2(largest))-2) if largest else -48
            if largest>6*2.**e:e+=1
            values=[]
            for j,value in enumerate(remainder):
                scaled=f32(value*2.**(-e));best=0;error=abs(scaled)
                for code in range(2,8):
                    candidate=[0,.5,1,1.5,2,3,4,6][code]
                    distance=abs(abs(scaled)-candidate)
                    if distance<error or (distance==error and code%2==0 and best%2):best=code;error=distance
                v=[0,.5,1,1.5,2,3,4,6][best]*(-1 if scaled<0 else 1)
                values.append(v);remainder[j]=f32(value-f32(v*2.**e))
            block.append(values);scales.append(e)
        parts.append(block);exponents.append(scales)
    return parts,exponents


def partials(packed, orientation, vector):
    k=packed['components'];t=packed[orientation];vc,ve=vector_components(vector,k)
    out=[]
    for tile,col in enumerate(t['columns']):
        values=[]
        for row in range(16):
            sums=[0.]*4
            for h in range(k):
                coeff=[]
                for j in range(32):
                    lane=(row%8)*4+(j%16)//4;reg=(row//8)+2*(j//16)
                    if packed['compact_fragments']:
                        word=t['fragments'][(tile*k+h)*64+lane*2+reg//2]
                        code=(word>>(16*(reg%2)+4*(j%4)))&15
                    else:
                        word=t['fragments'][(tile*k+h)*128+lane*4+reg]
                        code=(word>>(8*(j%4)+2))&15
                    coeff.append([0,.5,1,1.5,2,3,4,6][code&7]*(-1 if code&8 else 1))
                for s in range(k):
                    dot=sum(a*b for a,b in zip(coeff,vc[col][s]))
                    value=f32(dot*2.**(t['exponents'][tile*k+h]+ve[col][s]))
                    sums[s//2]=f32(sums[s//2]+value)
            values.append(f32(f32(sums[0]+sums[2])+f32(sums[1]+sums[3])))
        out.append(values)
    return out


def expected(cpu, request, lanes):
    tr=request['transpose'];name='columns' if tr else 'rows';fmt=request['settings']['format']
    native=fmt=='native';packed=fmt.startswith('fp4');inc=request['tensor'].get('incremental',True) and not native
    combined=packed and request.get('fast',{}).get('combined',False)
    if combined:lanes=32
    original=cpu['operator'][name];t=cpu['packed'][name]
    matrix=t['residual'] if packed else original
    vector=request['vector'];anchor=request['anchor']
    delta=[x-a for x,a in zip(vector,anchor)] if inc else vector
    tile=partials(cpu['packed'],name,delta) if packed else []
    reference=original_product(original,anchor) if inc else [0.]*(len(original['offsets'])-1)
    result=[]
    for row,(lo,hi) in enumerate(zip(matrix['offsets'],matrix['offsets'][1:])):
        if combined and request.get('fast',{}).get('adaptive_rows',False):
            first=row//4*4;last=min(first+4,len(matrix['offsets'])-1)
            lanes=32 if any(matrix['offsets'][q+1]-matrix['offsets'][q]>64 for q in range(first,last)) else 8
        sums=[0.]*lanes
        for lane in range(lanes):
            for j in range(lo+lane,hi,lanes):
                a=matrix['original'][j];x=delta[matrix['indices'][j]]
                sums[lane]=sums[lane]+a*x if native else f32(sums[lane]+f32(f32(a)*f32(x)))
            if packed and not combined:
                for q in range(t['offsets'][row//16]+lane,t['offsets'][row//16+1],lanes):
                    sums[lane]=f32(sums[lane]+tile[q][row%16])
        d=lanes//2
        while d:
            previous=sums[:]
            for lane in range(lanes-d):
                v=previous[lane]+previous[lane+d];sums[lane]=v if native else f32(v)
            d//=2
        value=sums[0]
        if combined:
            groups=[0.]*4;start=t['offsets'][row//16];end=t['offsets'][row//16+1]
            for g in range(4):
                for q in range(start+g,end,4):groups[g]=f32(groups[g]+tile[q][row%16])
            value=f32(value+f32(f32(groups[0]+groups[2])+f32(groups[1]+groups[3])))
        result.append(value+reference[row] if inc else value)
    return result


def run(identity,image=None,sanitizer=None):
    out=BASE/identity;out.mkdir(exist_ok=False);tensor.RUN_OUT=out;tensor.RUN_COUNT=0
    records=[];outputs=0;solves=0;fused_pairs=0
    families=FAMILIES if not sanitizer else FAMILIES[:2]
    for f,family in enumerate(families):
        model,_=generate(family,65 if f%2 else 33,41079+f);mp=out/(family+'.json');put(mp,model)
        for fi,fmt in enumerate(['native','fp32','fp4x1','fp4x2','fp4x3','fp4x4']):
            base=dict(settings=settings(fmt),tensor=dict(min_tile_nnz=1 if f%2 else 32,incremental=True,compact_fragments=True))
            cpu,_=tensor.invoke(mp,'tensor-operator',base)
            tensor.packing(cpu)
            for tr in [False,True]:
                n=len(cpu['operator']['rows' if tr else 'columns']['offsets'])-1
                rng=random.Random(1000+f);v=[rng.uniform(-3,3)*2.**((j%7)-3) for j in range(n)]
                cases=['anchored','direct'] if sanitizer else ['anchored','direct','tiny','large']
                for ci,case in enumerate(cases):
                    value=[x*(2.**-140 if case=='tiny' else 2.**32 if case=='large' else 1.) for x in v]
                    anchor=[x*.9375 for x in value];lane=[1,4,8,32][(fi+ci+f)%4]
                    request={**base,'transpose':tr,'vector':value,'anchor':anchor,'fast':dict(lanes=lane,fused_encode=True,combined=ci%2==0,adaptive_rows=ci==0),
                        'tensor':{**base['tensor'],'incremental':case!='direct'}}
                    oracle=expected(cpu,request,lane)
                    name=f'{family}-{fmt}-t{int(tr)}-{case}'
                    put(out/(name+'.expected.json'),oracle);put(out/(name+'.request.json'),request)
                    if image:
                        r,log=tensor.invoke(mp,'gpu-fast-probe',request,image,sanitizer)
                        put(out/(name+'.response.json'),r);(out/(name+'.log')).write_text(log)
                        require(r['enclosed'] is False and 'bounds' not in r,'proposal is not an enclosure')
                        require(r['proposal_values']==oracle,'independent proposal arithmetic differs '+name)
                        shape=(8 if request['fast']['adaptive_rows'] else 32) if fmt.startswith('fp4') and request['fast']['combined'] else lane
                        require(r['lanes']==[shape,shape],'explicit lane mapping differs')
                        records.append(ref(out/(name+'.response.json')))
                    outputs+=len(oracle)
        if not image:continue
        for fmt in ['native','fp32','fp4x1','fp4x2','fp4x3','fp4x4']:
            regular=None
            for fault in ['ordinary','unfused','force_recovery_after','cancel_after']:
                if sanitizer and fault=='unfused':continue
                st={**settings(fmt),'iteration_limit':64 if sanitizer else 600,'check_interval':32 if sanitizer else 200}
                if fault in ['force_recovery_after','cancel_after']:st[fault]=32
                request=dict(settings=st,tensor=dict(min_tile_nnz=32,control_interval=16 if sanitizer else 100),fast=dict(fused_encode=fault!='unfused'))
                r,log=tensor.invoke(mp,'gpu-fast',request,image,sanitizer)
                name=f'{family}-{fmt}-{fault}';put(out/(name+'.response.json'),r);put(out/(name+'.request.json'),request);(out/(name+'.log')).write_text(log)
                require(sum(r['accepted'])==r['logical'] and sum(r['attempted'])==r['physical'],'step accounting')
                require(all(a<=b for a,b in zip(r['accepted_product_work'],r['physical_product_work'])),'accepted work')
                if fault=='cancel_after':require(r['status']=='cancelled' and r['physical']==32 and r['logical']==(16 if sanitizer else 0),'cancel rollback')
                if fault=='force_recovery_after':
                    require(r['physical']>r['logical'],'rejected steps disappeared')
                    require(all(v['restored_exact'] for v in r['recoveries']),'inexact restoration')
                fields=['primal','dual','certificate','assessments','logical','physical','accepted','attempted','recoveries','restarts','accepted_product_work','physical_product_work']
                if fault=='ordinary':regular={k:r[k] for k in fields}
                if fault=='unfused':require({k:r[k] for k in fields}==regular,'fused encoding changes arithmetic');fused_pairs+=1
                for j,e in enumerate([*r['assessments'],dict(primal=r['primal'],dual=r['dual'],certificate=r['certificate'])]):
                    serial(mp,{**e,'bound_proof':r['bound_proof']},st['tolerance'],out,name+f'-a{j}')
                records.append(ref(out/(name+'.response.json')));solves+=1
    if image and not sanitizer:
        source=BASE/'tensor-gpu-v4/certificate-inequalities.json';mp=out/'certificate-inequalities.json';put(mp,load(source))
        for fmt in ['native','fp32','fp4x1','fp4x2','fp4x3','fp4x4']:
            for tol in [1e-7,1e-9]:
                req=dict(settings={**settings(fmt),'tolerance':tol,'iteration_limit':10000},tensor=dict(min_tile_nnz=1,control_interval=50))
                r,log=tensor.invoke(mp,'gpu-fast',req,image);name=f'certified-{fmt}-{tol}';put(out/(name+'.response.json'),r);put(out/(name+'.request.json'),req)
                require(r['certified'],'positive strict certificate required '+name)
                if fmt.startswith('fp4'):require(r['accepted_product_work'][1]>0,'strict solve used no FP4')
                for j,e in enumerate([*r['assessments'],dict(primal=r['primal'],dual=r['dual'],certificate=r['certificate'])]):
                    serial(mp,{**e,'bound_proof':r['bound_proof']},tol,out,name+f'-a{j}')
                records.append(ref(out/(name+'.response.json')));solves+=1
    result=dict(status='passed',binary=ref(tensor.BINARY),image=ref(image) if image else None,sanitizer=sanitizer,products=outputs,solves=solves,fused_pairs=fused_pairs,records=records,oracle=ref(__file__))
    put(out/'result.json',result);print({k:v for k,v in result.items() if k!='records'},flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--id',required=True);p.add_argument('--image',type=Path);p.add_argument('--sanitizer',choices=['memcheck','racecheck','initcheck','synccheck']);a=p.parse_args();run(a.id,a.image,a.sanitizer)
