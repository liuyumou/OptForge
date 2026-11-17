"""Independent sparse Tensor Core packing/product admission and bounded comparisons."""
import argparse
import json
import math
import random
import subprocess
import time
from fractions import Fraction as Q
from pathlib import Path
from lp_general_common import BASE,ROOT,load,put,ref,require
from lp_general_models import generate,FAMILIES
from lp_general_oracle import settings
from lp_general_device import serial,product as native_product,f32
RUN_OUT=None
RUN_COUNT=0
BINARY=ROOT/'research/lp-general-lowbit/target/release/lp-general-lowbit'


def invoke(model,mode,request,image=None,sanitizer=None):
    global RUN_COUNT
    args=[str(BINARY),mode,str(model)]+([str(image)] if image else [])
    if sanitizer:args=['/usr/local/cuda/bin/compute-sanitizer','--tool',sanitizer,'--error-exitcode','87',*args]
    wire=json.dumps(request)+'\n'
    p=subprocess.run(args,input=wire,text=True,capture_output=True)
    if RUN_OUT is not None:
        trace=RUN_OUT/'invocations';trace.mkdir(exist_ok=True);name=f'{RUN_COUNT:05d}';RUN_COUNT+=1
        put(trace/(name+'.json'),dict(argv=args,returncode=p.returncode))
        for suffix,data in [('input.jsonl',wire),('stdout',p.stdout),('stderr',p.stderr)]:
            with (trace/(name+'.'+suffix)).open('x') as f:f.write(data)
    require(p.returncode==0,p.stderr[-4000:]);lines=[s for s in p.stdout.splitlines() if s.startswith('{')]
    require(len(lines)==1,'one response required')
    if sanitizer:require('ERROR SUMMARY: 0 errors' in p.stderr+p.stdout or 'RACECHECK SUMMARY: 0 hazards' in p.stderr+p.stdout,'sanitizer summary missing')
    return json.loads(lines[0]),p.stderr


def unpack(t,k,compact=False):
    entries={};bounds={}
    for group,(lo,hi) in enumerate(zip(t['offsets'],t['offsets'][1:])):
        for tile in range(lo,hi):
            col=t['columns'][tile]*32
            for lane in range(32):
                for reg in range(4):
                    row=group*16+lane//4+(reg%2)*8
                    start=col+(lane%4)*4+(reg//2)*16
                    for z in range(4):
                        value=Q(0);absolute=Q(0)
                        for h in range(k):
                            if compact:
                                word=t['fragments'][(tile*k+h)*64+lane*2+reg//2];code=(word>>(16*(reg%2)+4*z))&15
                            else:
                                word=t['fragments'][(tile*k+h)*128+lane*4+reg];byte=(word>>(8*z))&255
                                require(byte&3==0 and byte<64,'invalid E2M1 byte fragment');code=byte>>2
                            require(code not in (1,9),'subnormal tensor input')
                            v=Q([0,.5,1,1.5,2,3,4,6][code&7])*(-1 if code&8 else 1)*Q(2)**t['exponents'][tile*k+h]
                            value+=v;absolute+=abs(v)
                        key=(row,start+z);require(key not in entries,'overlapping packed output')
                        entries[key]=value
                        local=(row%16);bounds.setdefault((tile,local),[Q(0),Q(0),[]])[1]+=absolute
                        bounds[(tile,local)][2].append(key)
    return entries,bounds


def packing(r):
    original={}
    o=r['operator']['rows'];nr=len(o['offsets'])-1;nc=len(r['operator']['columns']['offsets'])-1
    for row,(lo,hi) in enumerate(zip(o['offsets'],o['offsets'][1:])):
        for j in range(lo,hi):original[(row,o['indices'][j])]=Q(o['original'][j])
    k=r['packed']['components'];maps=[]
    for tr,name in enumerate(['rows','columns']):
        t=r['packed'][name];entries,guards=unpack(t,k,r['packed'].get('compact_fragments',False))
        for (tile,row),(err,mag,keys) in guards.items():
            err=sum((abs(original.get((c,a) if tr else (a,c),Q(0))-entries[(a,c)]) for a,c in keys),Q(0))
            require(Q(t['metadata'][tile*32+2*row])>=err,'coefficient error not enclosed')
            require(Q(t['metadata'][tile*32+2*row+1])>=mag,'component magnitude not enclosed')
        residual=t['residual'];seen={};covered=[0]*(nc if tr else nr)
        for row,(lo,hi) in enumerate(zip(residual['offsets'],residual['offsets'][1:])):
            for j in range(lo,hi):
                col=residual['indices'][j];require((row,col) not in entries,'tile/remainder overlap');seen[(row,col)]=Q(residual['original'][j])
        for key,value in original.items():
            oriented=(key[1],key[0]) if tr else key
            require(oriented in entries or seen.get(oriented)==value,'missing sparse coefficient')
            if oriented in entries:covered[oriented[0]]+=1
        require(covered==t['covered'],'FP4 work coverage incorrect')
        maps.append({((c,a) if tr else (a,c)):v for (a,c),v in entries.items() if a<(nc if tr else nr) and c<(nr if tr else nc)})
    require(maps[0]==maps[1],'represented transpose differs')


def represented_product(packed,vector):
    k=packed['components'];t=packed['orientation'];n=len(t['covered'])
    # Decode each MMA component independently from the PTX fragment layout.
    vc=[];ve=[]
    for lo in range(0,len(vector),32):
        residual=[f32(v) for v in vector[lo:lo+32]]+[0.]*(32-len(vector[lo:lo+32]))
        parts=[];ex=[]
        for h in range(k):
            largest=max(abs(v) for v in residual);e=max(-48,math.floor(math.log2(largest))-2) if largest else -48
            if largest>6*2.**e:e+=1
            codes=[]
            for value in residual:
                scaled=f32(value*2.**(-e));best=0;err=abs(scaled)
                for c in range(2,8):
                    error=abs(abs(scaled)-[0,.5,1,1.5,2,3,4,6][c])
                    if error<err or (error==err and c%2==0 and best%2):best=c;err=error
                codes.append((-1 if scaled<0 else 1)*[0,.5,1,1.5,2,3,4,6][best])
            residual=[f32(v-f32(c*2.**e)) for v,c in zip(residual,codes)]
            parts.append(codes);ex.append(e)
        vc.append(parts);ve.append(ex)
    values=native_product(t['residual'],vector)
    for group,(lo,hi) in enumerate(zip(t['offsets'],t['offsets'][1:])):
        for row in range(16):
            target=group*16+row
            if target>=n:continue
            total=0.
            for tile in range(lo,hi):
                col=t['columns'][tile]
                for h in range(k):
                    coeff=[]
                    for j in range(32):
                        lane=(row%8)*4+(j%16)//4;reg=(row//8)+2*(j//16)
                        if packed.get('compact_fragments',False):
                            word=t['fragments'][(tile*k+h)*64+lane*2+reg//2];c=(word>>(16*(reg%2)+4*(j%4)))&15
                        else:
                            word=t['fragments'][(tile*k+h)*128+lane*4+reg];c=(word>>(8*(j%4)+2))&15
                        coeff.append((-1 if c&8 else 1)*[0,.5,1,1.5,2,3,4,6][c&7])
                    for q in range(k):
                        dot=sum(a*b for a,b in zip(coeff,vc[col][q]))
                        total=f32(total+f32(dot*2.**(t['exponents'][tile*k+h]+ve[col][q])))
            values[target]+=total
    return values


def run(identity,image=None,sanitizer=None,solves=False):
    global RUN_OUT,RUN_COUNT
    out=BASE/identity;out.mkdir(parents=True,exist_ok=False);RUN_OUT=out;RUN_COUNT=0;records=[];outputs=0
    families=FAMILIES if not sanitizer else FAMILIES[:2]
    for f,family in enumerate(families):
        model,w=generate(family,65 if f%2 else 33,19+f);mp=out/(family+'.json');put(mp,model)
        for k in (1,2,3,4):
            fmt='fp4x'+str(k);base=dict(settings={**settings(),'format':fmt},tensor=dict(min_tile_nnz=1 if f%2 else 32,components=k))
            cpu,_=invoke(mp,'tensor-operator',base);packing(cpu);put(out/(family+f'-k{k}-packing.json'),cpu)
            if not image:continue
            for tr in (False,True):
                matrix=cpu['operator']['columns' if tr else 'rows'];n=len(cpu['operator']['rows' if tr else 'columns']['offsets'])-1
                rng=random.Random(100+f);v=[rng.uniform(-3,3)*(2.**((j%7)-3)) for j in range(n)]
                for case,vector,limit in [('random',v,1e300),('correction',v,0.),('zero',[0.]*n,1e300),('tiny',[x*2**-140 for x in v],1e300),('large',[x*2**32 for x in v],1e300),('anchored',v,1e300),('direct',v,1e300),('expanded',v,1e300),('wide',v,1e300)]:
                    if sanitizer and case not in ('random','correction','anchored','expanded','wide'):continue
                    anchor=[x*.99999 for x in vector] if case=='anchored' else [0.]*len(vector)
                    request={**base,'transpose':tr,'vector':vector,'anchor':anchor,'local_limit':limit}
                    if case=='wide':request['tensor']={**base['tensor'],'tensor_warps':4}
                    if case=='expanded':request['tensor']={**base['tensor'],'compact_fragments':False}
                    if case=='direct':request['tensor']={**base['tensor'],'incremental':False}
                    result,log=invoke(mp,'gpu-tensor-probe',request,image,sanitizer)
                    if case=='expanded':packing(result)
                    for row,(lo,hi) in enumerate(zip(matrix['offsets'],matrix['offsets'][1:])):
                        exact=sum((Q(matrix['original'][j])*Q(vector[matrix['indices'][j]]) for j in range(lo,hi)),Q(0))
                        value=result['product']['values'][row];bound=result['product']['bounds'][row]
                        require(math.isfinite(value) and math.isfinite(bound) and bound>=0,'nonfinite product/bound')
                        require(abs(Q(value)-exact)<=Q(bound),f'exact product outside enclosure {family}/{k}/{tr}/{case}/{row}')
                        outputs+=1
                    if case!='correction':
                        delta=[x-a for x,a in zip(vector,anchor)]
                        proposed=represented_product(dict(components=k,compact_fragments=cpu['packed'].get('compact_fragments',False),orientation=cpu['packed']['columns' if tr else 'rows']),delta)
                        expected=[a+b for a,b in zip(native_product(matrix,anchor),proposed)]
                        require(result['product']['values']==expected,'represented MMA arithmetic differs')
                    if case=='correction':require(result['product']['values']==native_product(matrix,vector),'local fallback not original FP64 product')
                    name=f'{family}-k{k}-t{int(tr)}-{case}';put(out/(name+'.response.json'),result);put(out/(name+'.request.json'),request)
                    (out/(name+'.log')).write_text(log);records.append(dict(name=name,response=ref(out/(name+'.response.json'))))
    if image:
        for family in families:
            mp=out/(family+'.json');cpu=load(out/(family+'-k1-packing.json'))
            for tr in (False,True):
                matrix=cpu['operator']['columns' if tr else 'rows'];n=len(cpu['operator']['rows' if tr else 'columns']['offsets'])-1
                vector=[((j*13)%101-50)/31 for j in range(n)];anchor=[x*.9375 for x in vector]
                for limit in [0.,1e300]:
                    request=dict(settings=settings('fp32'),transpose=tr,vector=vector,anchor=anchor,local_limit=limit)
                    r,log=invoke(mp,'gpu-tensor-probe',request,image,sanitizer)
                    m={**matrix,'ids':list(range(len(matrix['original'])))}
                    approximate=native_product(m,[f32(x-a) for x,a in zip(vector,anchor)],[[f32(a)] for a in matrix['original']])
                    expected=native_product(matrix,vector) if limit==0 else [a+b for a,b in zip(native_product(matrix,anchor),approximate)]
                    require(r['product']['values']==expected,'FP32-storage arithmetic differs')
                    for row,(lo,hi) in enumerate(zip(matrix['offsets'],matrix['offsets'][1:])):
                        exact=sum((Q(matrix['original'][j])*Q(vector[matrix['indices'][j]]) for j in range(lo,hi)),Q(0))
                        require(abs(Q(r['product']['values'][row])-exact)<=Q(r['product']['bounds'][row]),'FP32 enclosure');outputs+=1
                    name=f'{family}-fp32-t{int(tr)}-limit{int(limit==0)}';put(out/(name+'.response.json'),r);put(out/(name+'.request.json'),request);(out/(name+'.log')).write_text(log)
                    records.append(dict(name=name,response=ref(out/(name+'.response.json'))))
    if solves:
        require(image is not None,'solve admission needs an image')
        for f,family in enumerate(families):
            mp=out/(family+'.json')
            for fmt in ['native','fp32','fp4x1','fp4x2','fp4x3','fp4x4']:
                for fault in [None,'force_recovery_after','cancel_after']+(['no_tiles'] if fmt=='fp4x4' else []):
                    st={**settings(fmt),'iteration_limit':64 if sanitizer else 600,'check_interval':32 if sanitizer else 200}
                    if fault in ('force_recovery_after','cancel_after'):st[fault]=32
                    request=dict(settings=st,tensor=dict(min_tile_nnz=1024 if fault=='no_tiles' else 32,control_interval=16 if sanitizer else 100))
                    r,log=invoke(mp,'gpu-tensor',request,image,sanitizer)
                    require(sum(r['attempted'])==r['physical'] and sum(r['accepted'])==r['logical'],'iteration accounting')
                    require(all(a<=b for a,b in zip(r['accepted_product_work'],r['physical_product_work'])),'accepted work exceeds physical')
                    require(r['accepted_product_work'][1]<=r['accepted_product_work'][0],'used FP4 work exceeds attempted')
                    if fault=='no_tiles' and r['tile_count']==0:require(r['selected_initial_format']=='native' and r['accepted_product_work'][1]==0,'empty tile selection')
                    if fault=='cancel_after':require(r['status']=='cancelled' and r['logical']==(16 if sanitizer else 0) and r['physical']==32,'cancellation rollback')
                    if fault=='force_recovery_after':
                        require(r['physical']>r['logical'],'rejected work disappeared')
                        require(all(v['restored_exact'] for v in r['recoveries']),'checkpoint restoration failed')
                    name=f'{family}-{fmt}-{fault or "ordinary"}'
                    put(out/(name+'.response.json'),r);put(out/(name+'.request.json'),request)
                    endpoints=[*r['assessments'],dict(primal=r['primal'],dual=r['dual'],certificate=r['certificate'])]
                    for j,e in enumerate(endpoints):
                        e={**e,'bound_proof':r['bound_proof']}
                        serial(mp,e,st['tolerance'],out,name+f'-assessment-{j}')
                    records.append(dict(name=name,response=ref(out/(name+'.response.json'))))
    if solves and not sanitizer:
        finite=lambda v:dict(kind='finite',value=v)
        doc,_=generate('rectangular',5,99117)
        doc['model_id']='tensor-certificate-inequalities'
        doc['constraints']=[dict(id=11+5*j,lower=dict(kind='negative_infinity'),upper=finite(1.),terms=[dict(variable_id=7+3*j,coefficient=1.)]) for j in range(5)]
        for v in doc['variables']:v['upper']=finite(2.)
        doc['objective']=dict(sense='minimize',offset=0.,terms=[dict(variable_id=7+3*j,coefficient=-1.) for j in range(5)])
        mp=out/'certificate-inequalities.json';put(mp,doc)
        for fmt in ['native','fp32','fp4x1','fp4x2','fp4x3','fp4x4']:
            for tol in (1e-7,1e-9):
                request=dict(settings={**settings(fmt),'tolerance':tol,'iteration_limit':10000},tensor=dict(min_tile_nnz=1,control_interval=50))
                r,log=invoke(mp,'gpu-tensor',request,image)
                require(r['certified'],'strict Tensor Core solve did not certify '+fmt)
                if fmt.startswith('fp4'):require(r['accepted_product_work'][1]>0,'certified tensor solve did no accepted FP4 work')
                name=f'certified-{fmt}-{tol}';put(out/(name+'.response.json'),r);put(out/(name+'.request.json'),request)
                for j,e in enumerate([*r['assessments'],dict(primal=r['primal'],dual=r['dual'],certificate=r['certificate'])]):
                    serial(mp,{**e,'bound_proof':r['bound_proof']},tol,out,name+f'-assessment-{j}')
                records.append(dict(name=name,response=ref(out/(name+'.response.json'))))
    result=dict(status='passed',binary=ref(BINARY),image=ref(image) if image else None,sanitizer=sanitizer,products=outputs,records=records,families=families)
    put(out/'result.json',result);print({k:v for k,v in result.items() if k!='records'},flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--id',required=True);p.add_argument('--image',type=Path);p.add_argument('--solves',action='store_true');p.add_argument('--sanitizer',choices=['memcheck','racecheck','initcheck','synccheck']);a=p.parse_args();run(a.id,a.image,a.sanitizer,a.solves)
