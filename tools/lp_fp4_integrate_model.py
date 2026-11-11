"""Frozen bounded coupled LP fixtures and exact-original preparation for SPEC-0030."""
import math
import numpy as np
from lp_fp4_fast_prepare import encode_batch
from lp_fp4_integrate_common import put

FAMILIES=('coupled-equality','coupled-inequality','ranged-one-sided','fixed-active-bounds',
          'ill-scaled-coupled','irregular-tail-33','dense-rich-65','infinite-bound-refusal')
LANES=((64,1),(8,4),(16,2),(4,2),(4,4),(4,8))

def model(family,dimension=None):
 if family not in FAMILIES:raise ValueError('unknown fixture')
 n=65 if family=='dense-rich-65' else 33 if family in ('irregular-tail-33','infinite-bound-refusal') else 64
 if dimension is not None:
  if dimension not in (32,128):raise ValueError('boundary dimension')
  n=dimension
 i=np.arange(n);a=np.eye(n);a[i,(i+1)%n]=1/16;a[i,(i-1)%n]=-1/32
 if family=='dense-rich-65':a+=((13*i[:,None]+7*i[None,:])%17-8)/512
 if family=='ill-scaled-coupled':a*=np.exp2(i%5-2)[:,None]
 x=(i%5-2)/8+.5;y=(i%5-2)/8;lo=np.full(n,-1.);hi=np.full(n,1.)
 if family=='coupled-inequality':y=(i%3+1)/16
 if family=='fixed-active-bounds':
  x[i%3==0]=-1;x[i%3==1]=1;lo[i%7==0]=x[i%7==0];hi[i%7==0]=x[i%7==0]
 b=a@x;rl=b.copy();ru=b.copy()
 if family in ('coupled-inequality','ranged-one-sided'):
  ru[y>0]=np.inf;rl[y<0]=-np.inf;rl[y==0]-=.25;ru[y==0]+=.25
 z=np.zeros(n)
 if family=='fixed-active-bounds':z[x==-1]=.125;z[x==1]=-.125
 cost=a.T@y+z
 if family=='infinite-bound-refusal':
  a[:,-1]=0;cost[-1]=1;lo[-1]=-np.inf;hi[-1]=np.inf;b=a@x;rl=b.copy();ru=b.copy()
 sense='maximize' if family=='dense-rich-65' else 'minimize'
 def bound(v):return dict(kind='finite',value=float(v)) if math.isfinite(v) else dict(kind='positive_infinity' if v>0 else 'negative_infinity')
 variables=[dict(id=3*j+7,domain='continuous',lower=bound(lo[j]),upper=bound(hi[j])) for j in range(n)]
 rows=[dict(id=5*r+11,lower=bound(rl[r]),upper=bound(ru[r]),terms=[dict(variable_id=3*j+7,coefficient=float(a[r,j])) for j in range(n) if a[r,j]!=0]) for r in range(n)]
 document=dict(schema_version=1,model_id='fp4-integrate-v1-'+family,variables=variables,constraints=rows,objective=dict(sense=sense,offset=3.25,terms=[dict(variable_id=3*j+7,coefficient=float(cost[j] if sense=='minimize' else -cost[j])) for j in range(n) if cost[j]!=0]))
 return document,dict(a=a,c=cost,lo=lo,hi=hi,rl=rl,ru=ru,target_x=x,target_y=y)

def initial(data):
 n=len(data['c']);p=((n+31)//32)*32
 x=np.clip((np.arange(n)%3-1)/8,data['lo'],data['hi']);y=(np.arange(n)%7-3)/64
 out=np.zeros((5,p));out[0,:n]=x;out[1,:n]=y;out[2,:n]=x;out[3,:n]=x;out[4,:n]=y
 return out.reshape(-1).tolist()

def prepare(data,bits,components,raw=None,iteration=0,max_updates=600):
 if (bits,components) not in LANES:raise ValueError('lane')
 a=np.asarray(data['a']);m,n=a.shape;b=(max(m,n)+31)//32;p=32*b
 padded=np.zeros((p,p));padded[:m,:n]=a
 tiles=padded.reshape(b,32,b,32).transpose(0,2,1,3).reshape(b*b,1024)
 codes,scales=([0],[0]) if bits==64 else encode_batch(tiles,bits,components)
 norm=math.sqrt(np.max(np.sum(abs(a),axis=0))*np.max(np.sum(abs(a),axis=1)))
 shift=max(1,math.ceil(math.log2(norm/math.sqrt(.75))))
 return dict(format=bits,components=components,codes=codes,exponents=scales,initial=initial(data) if raw is None else raw,
             shift=shift,max_updates=max_updates,initial_iteration=iteration)

def observation(data,raw):
 n=len(data['c']);p=(n+31)//32*32;raw=np.asarray(raw);x=raw[:n];y=raw[p:p+n]
 if not np.isfinite(raw).all():raise ValueError('nonfinite audit')
 a=data['a'];ax=a@x;s=data['c']-a.T@y
 def maximum(v):return float(np.max(np.abs(v),initial=0))
 sx=max(1.,maximum(x),maximum(s),maximum(data['lo'][np.isfinite(data['lo'])]),maximum(data['hi'][np.isfinite(data['hi'])]))
 sy=max(1.,maximum(y),maximum(ax),maximum(data['rl'][np.isfinite(data['rl'])]),maximum(data['ru'][np.isfinite(data['ru'])]))
 terms=dict(row=maximum(ax-np.clip(ax,data['rl'],data['ru']))/sy,
            column=maximum(x-np.clip(x,data['lo'],data['hi']))/sx,
            primal_fixed=maximum(x-np.clip(x-s,data['lo'],data['hi']))/sx,
            dual_fixed=maximum(ax+np.clip(y-ax,-data['ru'],-data['rl']))/sy)
 return dict(**terms,rho=max(terms.values()),scale=min(max(1.,maximum(x)),max(1.,maximum(y))))

def reference(data,raw,steps,shift):
 n=len(data['c']);p=(n+31)//32*32;out=np.asarray(raw).reshape(5,p).copy();tau=2.**-shift
 for _ in range(steps):
  old=out[0,:n].copy();u=np.clip(old+tau*(data['a'].T@out[1,:n]-data['c']),data['lo'],data['hi'])
  out[0,:n]=u;out[2,:n]=2*u-old;v=out[1,:n]-tau*(data['a']@out[2,:n]);out[1,:n]=v-np.clip(v,-tau*data['ru'],-tau*data['rl'])
 return out.reshape(-1).tolist()
