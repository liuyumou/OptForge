"""Vectorized, exact-residual host preparation for the bounded component domain.

Each nonzero nearest component is between half and twice its residual magnitude.
Sterbenz subtraction is therefore exact in binary64. Zero components leave the
original binary64 residual unchanged. Scaling is by normal powers of two;
underflowed scaled values round to zero and never replace that residual.
"""
import json
from pathlib import Path
import struct
import numpy as np
from lp_fp4_gpu_oracle import LANES, FP8

FP4_VALUES=np.array([0,.5,1,1.5,2,3,4,6],dtype=np.float64)
FP4_MID=(FP4_VALUES[:-1]+FP4_VALUES[1:])/2
FP8_VALUES=np.array([float(v) for v,_ in FP8],dtype=np.float64)


def encode_batch(values,bits,components,arrays=False):
    if (bits,components) not in LANES or bits==64:
        raise ValueError('unsupported component lane')
    residual=np.asarray(values,dtype=np.float64).copy()
    if residual.ndim!=2 or residual.shape[1]%32 or not np.isfinite(residual).all():
        raise ValueError('finite block matrix required')
    maximum=6 if bits==4 else 448 if bits==8 else 65504
    width=32//bits; words=[];exponents=[]
    for _ in range(components):
        largest=np.max(np.abs(residual),axis=1)
        if np.any(largest>np.ldexp(float(maximum),48)):
            raise ValueError('scale overflow')
        e=np.frexp(largest)[1]-1-(2 if bits==4 else 8 if bits==8 else 15)
        e+=largest>np.ldexp(float(maximum),e)
        e=np.where(largest==0,-48,np.maximum(e,-48))
        scaled=np.ldexp(residual,-e[:,None]);negative=scaled<0;mag=np.abs(scaled)
        if bits==4:
            index=np.searchsorted(FP4_MID,mag,side='left')
            mid=FP4_MID[np.minimum(index,6)]
            index+=((index<7)&(mag==mid)&((index&1)!=0))
            codes=index.astype(np.uint32)|np.where(negative&(index!=0),8,0).astype(np.uint32)
            decoded=np.where(negative,-FP4_VALUES[index],FP4_VALUES[index])
        elif bits==8:
            mag=mag.astype(np.float32).astype(np.float64)
            hi=np.minimum(np.searchsorted(FP8_VALUES,mag),126);lo=np.maximum(hi-1,0)
            dl=mag-FP8_VALUES[lo];dh=FP8_VALUES[hi]-mag
            index=np.where((dh<dl)|((dh==dl)&((hi&1)==0)),hi,lo)
            codes=index.astype(np.uint32)|np.where(negative&(index!=0),128,0).astype(np.uint32)
            decoded=np.where(negative,-FP8_VALUES[index],FP8_VALUES[index])
        else:
            half=scaled.astype(np.float32).astype(np.float16)
            codes=half.view(np.uint16).astype(np.uint32);codes[codes==32768]=0
            decoded=half.astype(np.float64)
        packed=np.bitwise_or.reduce(codes.reshape(len(codes),-1,width)<<np.arange(0,32,bits,dtype=np.uint32),axis=2)
        words.append(packed);exponents.append(e)
        residual-=np.ldexp(decoded,e[:,None])
    result=(np.stack(words,axis=1).reshape(-1).astype('<u4'),
            np.stack(exponents,axis=1).reshape(-1).astype('<i4'))
    return result if arrays else tuple(a.tolist() for a in result)


def workload(blocks,n=32,arrays=False):
    if not 1<=blocks<=4096 or not 1<=n<=32:
        raise ValueError('bounded workload dimensions')
    b=np.arange(blocks)[:,None,None];i=np.arange(32)[None,:,None];j=np.arange(32)[None,None,:]
    a=((i==j)*32+(13*i+7*j+3*b)%17-8)/64
    a=np.where((i<n)&(j<n)&((n==32)|(i==j)|((i+j)%5==0)),a,0.)
    target=np.where(np.arange(32)<n,(np.arange(32)%5-2)/4,0.)
    objective=np.where(np.arange(32)<n,(np.arange(32)%7-3)/16,0.)
    rhs=(a*target).sum(axis=2)
    cb=np.concatenate([np.broadcast_to(objective,(blocks,32)),rhs],axis=1)
    r=dict(n=n,blocks=blocks,matrix=a.reshape(-1),cb=cb.reshape(-1),initial=np.zeros(blocks*96))
    if not arrays:
        for key in ('matrix','cb','initial'):r[key]=r[key].tolist()
    return r


def request(blocks,bits,components,backend='columns',n=32,updates=32,repetitions=1,arrays=False):
    r=workload(blocks,n,arrays)
    words,exponents=([0],[0]) if bits==64 else encode_batch(np.asarray(r['matrix']).reshape(blocks,1024),bits,components,arrays)
    r.update(format=bits,components=components,matrix_codes=words,matrix_exponents=exponents,
             variant='persistent',updates=updates,mode='trajectory',cancel_after=None,inject_fault=False,
             backend=backend,repetitions=repetitions)
    return r


ARRAY_FIELDS=(('matrix','<f8'),('matrix_codes','<u4'),('matrix_exponents','<i4'),('cb','<f8'),('initial','<f8'))


def write_binary(path,r):
    """Versioned little-endian transport; original binary64 coefficients retained."""
    meta=dict(r)
    for field,_ in ARRAY_FIELDS:meta[field]=[]
    header=json.dumps(meta,separators=(',',':'),allow_nan=False).encode()
    if len(header)>16384:raise ValueError('binary header too large')
    with Path(path).open('xb') as f:
        f.write(b'FP4FAST1'+struct.pack('<I',len(header))+header)
        for field,dtype in ARRAY_FIELDS:f.write(np.asarray(r[field],dtype=dtype).tobytes())


def read_binary(path):
    data=Path(path).read_bytes()
    if data[:8]!=b'FP4FAST1' or len(data)<12:raise ValueError('binary header')
    length=struct.unpack_from('<I',data,8)[0]
    if length>16384 or 12+length>len(data):raise ValueError('binary header length')
    r=json.loads(data[12:12+length]);b=r['blocks'];f=r['format'];k=r['components']
    if (f,k) not in LANES or not 1<=b<=4096:raise ValueError('binary shape')
    sizes=(b*1024,1 if f==64 else b*k*32*f,1 if f==64 else b*k,b*64,b*96)
    offset=12+length
    for (field,dtype),size in zip(ARRAY_FIELDS,sizes):
        count=size*np.dtype(dtype).itemsize
        if offset+count>len(data):raise ValueError('truncated array')
        r[field]=np.frombuffer(data,dtype=dtype,count=size,offset=offset).tolist();offset+=count
    if offset!=len(data):raise ValueError('trailing bytes')
    return r
