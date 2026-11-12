"""Independent CPU preparation and empirical observations for SPEC-0027."""
from fractions import Fraction as Q
from functools import lru_cache
import math
from bisect import bisect_left
import struct

import lp_fp4_contract as c
from lp_fp4_reference_v2 import fp32, rounded_encode

LANES=((64,1),(8,4),(16,2),(4,2),(4,4),(4,8))
VARIANTS=('split','fused','persistent','roundtrip')
WORKLOADS=('dense-32','irregular-29','dense-2048')

def decode(code,bits):
    if bits==4:return c.code_value(code)
    if bits==16:return Q(struct.unpack('<e',struct.pack('<H',code))[0])
    sign=-1 if code&128 else 1;e=(code>>3)&15;m=code&7
    if e==15 and m==7:raise ValueError('nonfinite E4M3')
    return sign*(Q(m,512) if e==0 else Q(8+m,8)*Q(2)**(e-7))

FP8=tuple((decode(i,8),i) for i in range(127))

def nearest(x,bits):
    if bits==4:return c.nearest_code(x)
    # Control conversion uses a local binary32 sum, as CUDA conversion does.
    x=fp32(x)
    if bits==16:
        code=struct.unpack('<H',struct.pack('<e',float(x)))[0]
        return 0 if code==32768 else code
    index=min(126,bisect_left(FP8,(abs(x),-1)))
    _,code=min(FP8[max(0,index-1):index+1],key=lambda pair:(abs(abs(x)-pair[0]),pair[1]&1))
    return code|(128 if x<0 and code else 0)

def pack(codes,bits):
    if bits not in (4,8,16) or len(codes)%(32//bits):raise ValueError('packing shape')
    for code in codes:
        if type(code)is not int or not 0<=code<1<<bits:raise ValueError('packing code')
        decode(code,bits)
    width=32//bits
    return [sum(codes[i+j]<<(j*bits) for j in range(width)) for i in range(0,len(codes),width)]

def unpack(words,bits,length):
    width=32//bits
    if len(words)*width!=length:raise ValueError('unpacking shape')
    return [(words[i//width]>>((i%width)*bits))&((1<<bits)-1) for i in range(length)]

@lru_cache(maxsize=1024)
def encode(values,bits,components):
    if (bits,components) not in LANES or bits==64:raise ValueError('unsupported component lane')
    residual=list(map(Q,values));words=[];exponents=[];represented=[Q(0)]*len(values)
    for _ in range(components):
        maximum=Q(6 if bits==4 else 448 if bits==8 else 65504)
        largest=max(map(abs,residual));e=-48
        while e<48 and largest>maximum*Q(2)**e:e+=1
        if largest>maximum*Q(2)**e:raise ValueError('scale overflow')
        codes=[nearest(v/Q(2)**e,bits) for v in residual]
        values_q=[decode(code,bits)*Q(2)**e for code in codes]
        words.extend(pack(codes,bits));exponents.append(e)
        residual=[a-b for a,b in zip(residual,values_q)]
        represented=[a+b for a,b in zip(represented,values_q)]
    return words,exponents,represented,max(map(abs,residual))

def decode_planes(words,exponents,bits,length):
    stride=length*bits//32;values=[Q(0)]*length
    for k,e in enumerate(exponents):
        codes=unpack(words[k*stride:(k+1)*stride],bits,length)
        values=[v+decode(code,bits)*Q(2)**e for v,code in zip(values,codes)]
    return values

def workload(name):
    if name not in WORKLOADS:raise ValueError('workload')
    n=29 if name=='irregular-29' else 32;blocks=64 if name=='dense-2048' else 1
    matrix=[];cb=[]
    for block in range(blocks):
        a=[((int(i==j)*32+((13*i+7*j+3*block)%17)-8)/64
             if i<n and j<n and (n==32 or i==j or (i+j)%5==0) else 0.)
           for i in range(32) for j in range(32)]
        target=[(j%5-2)/4 if j<n else 0. for j in range(32)]
        objective=[(i%7-3)/16 if i<n else 0. for i in range(32)]
        rhs=[sum(a[i*32+j]*target[j] for j in range(32)) for i in range(32)]
        matrix.extend(a);cb.extend(objective+rhs)
    return dict(n=n,blocks=blocks,matrix=matrix,cb=cb,initial=[0.]*(blocks*96))

def request(name,bits,components,variant='persistent',updates=32):
    r=workload(name);words=[];exponents=[]
    if bits!=64:
        for b in range(r['blocks']):
            w,e,_,_=encode(tuple(r['matrix'][b*1024:(b+1)*1024]),bits,components);words.extend(w);exponents.extend(e)
    r.update(format=bits,components=components,matrix_codes=words or [0],matrix_exponents=exponents or [0],variant=variant,updates=updates,mode='trajectory',cancel_after=None,inject_fault=False)
    return r

def reference(r,updates):
    values=list(r['initial']);n=r['n']
    for _ in range(updates):
        for b in range(r['blocks']):
            a=r['matrix'][b*1024:(b+1)*1024];cb=r['cb'][b*64:(b+1)*64]
            x=values[b*96:b*96+32];y=values[b*96+32:b*96+64]
            aty=[sum(a[i*32+j]*y[i] for i in range(32)) for j in range(32)]
            u=[min(1.,max(-1.,x[j]-(cb[j]-aty[j])/16.)) if j<n else 0. for j in range(32)]
            bar=[2*v-old for v,old in zip(u,x)]
            ax=[sum(a[i*32+j]*bar[j] for j in range(32)) for i in range(32)]
            v=[y[i]+(cb[32+i]-ax[i])/16. if i<n else 0. for i in range(32)]
            values[b*96:(b+1)*96]=u+v+bar
    return values

def product_reference(r):
    bits,k=r['format'],r['components'];trans=r['mode']=='transpose';result=[]
    for b in range(r['blocks']):
        a=list(map(Q,r['matrix'][b*1024:(b+1)*1024]));v=list(map(Q,r['initial'][b*96+(32 if trans else 64):b*96+(64 if trans else 96)]))
        if bits!=64:
            a=encode(tuple(a),bits,k)[2];v=encode(tuple(v),bits,k)[2]
        result.extend(sum(a[j*32+i if trans else i*32+j]*v[j] for j in range(32)) for i in range(32))
    return result

def observed_error(values,reference_values):
    if len(values)!=len(reference_values) or any(not math.isfinite(v) for v in values):raise ValueError('invalid observed vector')
    error=max(abs(a-b) for a,b in zip(values,reference_values))
    return dict(max_absolute=error,relative=error/max(1.,max(map(abs,reference_values))),proved_enclosure=False,certified=False)
