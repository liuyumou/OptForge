"""First-window guard attribution without modifying the admitted solver/image."""
import argparse
from fractions import Fraction as Q
import json
import math
from pathlib import Path
import subprocess
from lp_general_common import ROOT,BASE,put,load,ref,require
from lp_general_device import BINARY,product,f32,bits
from lp_general_oracle import settings

def tree(values):
    if not values:return 0.
    while True:
        next=[]
        for begin in range(0,len(values),1024):
            a=values[begin:begin+1024]+[0.]*(1024-len(values[begin:begin+1024]))
            d=512
            while d:
                for i in range(d):a[i]+=a[i+d]
                d//=2
            next.append(a[0])
        if len(next)==1:return next[0]
        values=next

def root_product(matrix,x):
    return [tree([matrix['original'][j]*x[matrix['indices'][j]] for j in range(lo,hi)]) for lo,hi in zip(matrix['offsets'],matrix['offsets'][1:])]

def projections(r,x,y,aty,ax=None):
    tau=r['step']/r['weight'];sigma=r['step']*r['weight'];lo,hi=r['column_bounds']
    nx=[min(u if u is not None else math.inf,max(l if l is not None else -math.inf,old-tau*(c-a))) for old,c,a,l,u in zip(x,r['objective'],aty,lo,hi)]
    extra=[2*a-b for a,b in zip(nx,x)]
    if ax is None:return nx,extra
    lo,hi=r['row_bounds'];ny=[]
    for old,a,l,u in zip(y,ax,lo,hi):
        raw=old-sigma*a;ny.append(raw-sigma*min(-l if l is not None else math.inf,max(-u if u is not None else -math.inf,raw/sigma)))
    return nx,ny

def run(identity,image):
    out=BASE/identity;out.mkdir(parents=True,exist_ok=False);frozen=load(BASE/'development-pilot-v1/freeze.json');rows=[]
    for index in [0,2,4,6,8,10,12]:
        cell=next(r for r in frozen['cells'] if r['model_index']==index);model=ROOT/cell['model']['path'];s=settings('fp4x2')
        def call(command,requests,name):
            put(out/(name+'.requests.json'),requests)
            p=subprocess.run([str(BINARY),command,str(model),str(image)],input=''.join(json.dumps(q)+'\n' for q in requests),text=True,capture_output=True)
            (out/(name+'.jsonl')).write_text(p.stdout);(out/(name+'.stderr')).write_text(p.stderr)
            require(p.returncode==0,'guard diagnostic process');return [json.loads(v) for v in p.stdout.splitlines()]
        r=call('gpu-fixed',[dict(settings=s,count=16)],f'm{index}-fixed')[0]
        x=r['initial_x'][:];y=r['initial_y'][:];anchor_x=x[:];anchor_y=y[:];matrices=r['operator']
        native_at=root_product(matrices['columns'],y);native_x,extra=projections(r,x,y,native_at)
        _,native_y=projections(r,x,y,native_at,root_product(matrices['rows'],extra))
        error=max([abs(a-b) for a,b in zip(x,native_x)]+[abs(a-b) for a,b in zip(y,native_y)]+[0.])
        limit=min(max(error,s['tolerance']),1.)*max([1.,*map(abs,x),*map(abs,y)])/8
        references={False:product(matrices['rows'],x),True:product(matrices['columns'],y)}
        commands=[]
        def apply(tr,v,anchor):
            commands.append(dict(settings=s,transpose=tr,vector=v[:],anchor=anchor[:]))
            delta=[f32(a-b) for a,b in zip(v,anchor)]
            return [a+b for a,b in zip(references[tr],product(matrices['columns' if tr else 'rows'],delta,r['components']))]
        for t in range(16):
            aty=apply(True,y,anchor_y);nx,extra=projections(r,x,y,aty)
            ax=apply(False,extra,anchor_x);_,ny=projections(r,x,y,aty,ax)
            toward=(t+1)/(t+2);back=1/(t+2)
            x=[toward*v+back*a for v,a in zip(nx,anchor_x)];y=[toward*v+back*a for v,a in zip(ny,anchor_y)]
        require(bits(x)==bits(r['primal']) and bits(y)==bits(r['dual']),'unguarded diagnostic trajectory mismatch')
        products=call('gpu-probe',commands,f'm{index}-products');first=None;records=[]
        for j,(request,p) in enumerate(zip(commands,products)):
            step=r['step']/r['weight'] if request['transpose'] else r['step']*r['weight']
            k=max(range(len(p['product']['bounds'])),key=lambda i:p['product']['bounds'][i])
            enclosure=step*p['product']['bounds'][k];matrix=p['operator']['columns' if request['transpose'] else 'rows']
            lo,hi=matrix['offsets'][k:k+2]
            exact=sum((Q(matrix['original'][q])*Q(request['vector'][matrix['indices'][q]]) for q in range(lo,hi)),Q(0))
            actual=float(abs(Q(p['product']['values'][k])-exact))*step
            record=dict(update=j//2+1,transpose=request['transpose'],row=k,bound=enclosure,actual_error=actual,limit=limit,ratio=enclosure/limit)
            records.append(record)
            if first is None and enclosure>limit:first=record
        row=dict(model_index=index,family=cell['family'],model=cell['model'],initial_projected_merit=error,limit=limit,first_bound_rejection=first,records=records,
            scope='unguarded original first window only; after the first rejected update the live guarded trajectory may differ')
        put(out/f'm{index}.json',row);rows.append(row);print(dict(model_index=index,family=cell['family'],first_bound_rejection=first),flush=True)
    put(out/'result.json',dict(status='passed',rows=rows,binary=ref(BINARY),image=ref(image)))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--id',required=True);p.add_argument('--image',required=True,type=Path);a=p.parse_args();run(a.id,a.image)
