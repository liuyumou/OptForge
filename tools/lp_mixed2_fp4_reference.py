"""Independent CPU/rational model of bounded FP32 tensor reconstruction."""
from fractions import Fraction as Q
import math
import random
import struct
import sys
from lp_mixed2_fp4_common import BASE,load,put,ref,require


def f32(x):return struct.unpack('f',struct.pack('f',x))[0]
def f32_up(x):
    y=f32(x)
    return struct.unpack("f",struct.pack("I",struct.unpack("I",struct.pack("f",y))[0]+1))[0] if y<x else y
def add(a,b):return math.nextafter(a+b,math.inf)
def mul(a,b):return math.nextafter(a*b,math.inf)
def decode(c):return [0,.5,1,1.5,2,3,4,6][c&7]*(-1 if c&8 else 1)


def encode(current,anchor,k):
    delta=[x-y for x,y in zip(current,anchor)];residual=list(map(f32,delta));decoded=[0.]*32;parts=[];magnitude=[0.]*32
    for h in range(k):
        maximum=max(map(abs,residual));e=max(-48,math.floor(math.log2(maximum))-2) if maximum else -48
        if maximum>math.ldexp(6.,e):e+=1
        plane=[]
        for i,r in enumerate(residual):
            x=abs(math.ldexp(r,-e));code=0
            for next0,mid in ((2,.5),(3,1.25),(4,1.75),(5,2.5),(6,3.5),(7,5.)):
                if x>mid or (x==mid and next0!=2 and next0%2==0):code=next0
            if r<0 and code:code|=8
            value=math.ldexp(decode(code),e);plane.append(value);residual[i]=f32(residual[i]-value);decoded[i]+=value;magnitude[i]=add(magnitude[i],abs(value))
        parts.append(plane)
    error=[];mag=[]
    for i,(v,a) in enumerate(zip(current,anchor)):
        rounding=add(mul(2.**-48,add(add(abs(v),abs(a)),magnitude[i])),2.**-1068)
        error.append(add(abs(delta[i]-decoded[i]),rounding));mag.append(add(abs(delta[i]),add(mul(2.**-52,add(abs(v),abs(a))),2.**-1073)))
        actual=Q(v)-Q(a);represented=sum(Q(row[i]) for row in parts)
        require(Q(error[-1])>=abs(actual-represented) and Q(mag[-1])>=abs(actual),'vector summary escapes exact difference')
    return parts,list(map(f32_up,[max(mag),max(error),max(magnitude),max(map(abs,anchor))]))


def check(d,k,current,anchor,tr):
    p=d['p'];b=p//32;pack=d['packs'][str(k)];vector=[];norms=[]
    for j in range(b):
        v,n=encode(current[32*j:32*j+32],anchor[32*j:32*j+32],k);vector.append(v);norms.append(n)
    vn=[max(x[q] for x in norms) for q in range(4)];checked=0
    for i in range(p):
        exact=sum((Q(d['a'][j*p+i if tr else i*p+j])*Q(current[j]) for j in range(p)),Q(0))
        native=[]
        for w in range(8):
            value=0.
            for j in range(w,p,8):value+=d['a'][j*p+i if tr else i*p+j]*anchor[j]
            native.append(value)
        reference=sum(native,0.);partial=[]
        for w in range(8):
            total=0.
            for j in range(w,b,8):
                tile=j*b+i//32 if tr else (i//32)*b+j
                val=0.
                for h in range(k):
                    for s in range(k):
                        dot=Q(0)
                        for t in range(32):
                            off=t*32+i%32 if tr else (i%32)*32+t
                            code=(pack['codes'][tile*k*128+h*128+off//8]>>(4*(off%8)))&15
                            coefficient=Q(decode(code))*Q(2)**pack['exponents'][tile*k+h]
                            dot+=coefficient*Q(vector[j][s][t])
                        # The exact MMA dot and power-of-two rescaling are representable.
                        require(Q(f32(float(dot)))==dot,'component product is not exactly FP32 representable')
                        val=f32(val+float(dot))
                total=f32(total+val)
            partial.append(total)
        inc=0.
        for v in partial:inc=f32(inc+v)
        result=reference+inc;z=(3*p if tr else 0)+i;an=pack['norms'][z];er=pack['norms'][z+p];cn=pack['norms'][z+2*p]
        bound=mul(mul((2*p+32)*2.**-52,an),vn[3]);bound=add(bound,mul(er,vn[0]));bound=add(bound,mul(cn,vn[1]))
        bound=add(bound,mul(mul((4*b*k*k+32)*2.**-23,cn),vn[2]));bound=add(bound,mul(2.**-52,add(abs(reference),abs(inc))));bound=add(bound,2.**-1000)
        require(abs(Q(result)-exact)<=Q(bound),'FP32 reconstruction escapes rational original-product bound');checked+=1
    return checked


def run(dest):
    rng=random.Random(380072);rows=[]
    for name in ('normal-code-pairs','rectangular-cancellation','scale-range','irregular-tail-33'):
        d=load(BASE/'cpu-v2'/(name+'.inspect.json'));p=d['p']
        for regime in ('ordinary','large-anchor','tiny'):
            anchor=[rng.uniform(-1,1)*(2.**20 if regime=='large-anchor' else 2.**-1000 if regime=='tiny' else 1) for _ in range(p)]
            current=[x+rng.uniform(-1,1)*(2.**-20 if regime=='large-anchor' else 2.**-1000 if regime=='tiny' else 1) for x in anchor]
            for k in (2,4):
                for tr in (False,True):rows.append(dict(case=name,regime=regime,k=k,transpose=tr,outputs=check(d,k,current,anchor,tr)))
    result=dict(status='passed',seed=380072,rows=rows,outputs=sum(x['outputs'] for x in rows),source=ref(__file__))
    put(dest,result);print(dict(status='passed',outputs=result['outputs']),flush=True)
if __name__=='__main__':run(sys.argv[1])
