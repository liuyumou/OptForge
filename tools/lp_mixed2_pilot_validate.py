"""Independent product oracle and interval-union diagnostic contracts."""
from fractions import Fraction as F
import math
import struct
from lp_mixed2_pilot_common import require
from lp_delivery2_study import bits, matches


def union(intervals):
    ordered=sorted(intervals);total=0;end=None
    for a,b in ordered:
        require(type(a) is int and type(b) is int and 0<=a<=b,'invalid timestamp interval')
        total+=max(0,b-max(a,end if end is not None else a));end=max(b,end if end is not None else b)
    return total


def profile(lines):
    values=[v['mixed2_device_profile'] for v in lines if 'mixed2_device_profile' in v]
    matrix=cta=events=outer=0;updates=0;deltas=[]
    for v in values:
        outer+=v['outer_gpu_us']*1000;updates+=v['done']
        require(len(v['kernels'])==3*v['count'],'missing kernel observations')
        for k in v['kernels']:
            require(math.isfinite(k['event_ns']) and k['event_ns']>=0,'bad CUDA event')
            events+=k['event_ns']
            if k['phase']==2 or k['step']>=v['done']:continue
            stamps=k['stamps'];require(len(stamps)==v['blocks']*4,'missing CTA')
            rows=[stamps[i:i+4] for i in range(0,len(stamps),4)]
            require(all(0<a<=b<=c<=d for a,b,c,d in rows),'timestamp order')
            matrix+=union([(r[1],r[2]) for r in rows]);cta+=union([(r[0],r[3]) for r in rows])
            deltas.extend(b-a for r in rows for a,b in zip(r,r[1:]) if b>a)
    return dict(windows=len(values),updates=updates,matrix_union_ns=matrix,cta_union_ns=cta,kernel_event_ns=events,outer_event_ns=outer,min_positive_interval_ns=min(deltas,default=None))


def original_dots(inp):
    n,m=inp['rows'],inp['cols'];tr=inp['transpose'];a=inp['a'];x=list(map(F,inp['x']))
    return [sum((F(a[j*m+i] if tr else a[i*m+j])*x[j] for j in range(n if tr else m)),F(0)) for i in range(m if tr else n)]


def check_guard(inp,represented,bounds,exact=None):
    exact=original_dots(inp) if exact is None else exact
    require(len(represented)==len(bounds)>=len(exact),'guard shape')
    errors=[]
    for i,target in enumerate(exact):
        b=bounds[i];v=represented[i]
        require(math.isfinite(b) and b>=0 and math.isfinite(v),'nonfinite guard')
        error=abs(target-F(v));require(error<=F(b),'original rational dot outside guard')
        errors.append(float(error))
    require(all(v==0 for v in represented[len(exact):]),'nonzero padding')
    return dict(outputs=len(exact),maximum_error=max(errors,default=0),maximum_bound=max(bounds,default=0))


def exact_solve(result,old,binary,image):
    require(result['image_sha256']==image['sha256'],'image binding')
    normalized={**result,'image_sha256':old['image_sha256']}
    matches(normalized,old,binary)


def rhs(n):
    return [((-1.) if j%3==1 else 1.)*(1.0+(j*37%101)/113.) for j in range(n)]
