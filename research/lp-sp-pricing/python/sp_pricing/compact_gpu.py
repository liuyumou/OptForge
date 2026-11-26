"""Bounded tile uploads and one CPU check overlapped with the next GPU batch."""
from concurrent.futures import ThreadPoolExecutor
from collections import OrderedDict
import ctypes as C
from fractions import Fraction as Q
from pathlib import Path
import time

import numpy as np

from .compact_basis import TileSource, product
from .exact import Limit
from .gpu_wave import enclosure
from .native_auxiliary import NativeAuxiliary

ROOT=Path(__file__).resolve().parents[2]
GPU_LIBRARY=ROOT/'target/release/libsp_compact.so'
PROOF_LIBRARY=ROOT/'target/cpu/libsp_compact_proof.so'
PTR=C.POINTER(C.c_double)
IPTR=C.POINTER(C.c_int)


def pointer(array): return array.ctypes.data_as(PTR)


def check(code):
    if code: raise ArithmeticError('compact_cuda_'+str(code))


def prefetched(source, pool):
    """One pending producer task; no unbounded tile queue."""
    iterator=iter(source.descriptors)
    key=next(iterator,None)
    if key is None:return
    pending=pool.submit(source.tile,key)
    try:
        while key is not None:
            tile=pending.result(); following=next(iterator,None)
            pending=pool.submit(source.tile,following) if following is not None else None
            yield key,tile
            key=following
    finally:
        if pending is not None:pending.result()


class TileEngine:
    def __init__(self, source, width=64, device_cache_bytes=64<<20, sparse=True):
        if not 1<=width<=64 or device_cache_bytes<0:raise ValueError('bounded batch/cache')
        self.source=source;self.width=width;self.sparse=sparse;self.handle=C.c_void_p()
        self.lib=C.CDLL(str(GPU_LIBRARY));self.pool=ThreadPoolExecutor(max_workers=1,thread_name_prefix='compact-tile')
        self.lib.sp_compact_create.argtypes=[C.c_int]*5+[C.c_uint64,C.POINTER(C.c_void_p)]
        self.lib.sp_compact_create.restype=C.c_int
        self.lib.sp_compact_push.argtypes=[C.c_void_p]+[C.c_int]*4+[PTR,C.c_int];self.lib.sp_compact_push.restype=C.c_int
        self.lib.sp_compact_batch.argtypes=[C.c_void_p,C.c_int,C.c_double,C.c_double,PTR,PTR,PTR];self.lib.sp_compact_batch.restype=C.c_int
        self.lib.sp_compact_phase.argtypes=[C.c_void_p,C.c_int,C.c_int];self.lib.sp_compact_phase.restype=C.c_int
        self.lib.sp_compact_run.argtypes=[C.c_void_p,C.c_int];self.lib.sp_compact_run.restype=C.c_int
        self.lib.sp_compact_timer.argtypes=[C.c_void_p,C.c_int];self.lib.sp_compact_timer.restype=C.c_int
        self.lib.sp_compact_result.argtypes=[C.c_void_p,PTR,PTR,PTR];self.lib.sp_compact_result.restype=C.c_int
        self.lib.sp_compact_destroy.argtypes=[C.c_void_p];self.lib.sp_compact_destroy.restype=None
        estimate=(24*source.nnz+len(source.descriptors)*(4*(source.tr+source.tc+2)+128)
                  if sparse else sum(min(source.tr,source.r-i)*min(source.tc,source.s-j)*8+16 for i,j in source.descriptors))
        self.cached=estimate<=device_cache_bytes and device_cache_bytes>0
        self.device_cache_bytes=max(16,estimate) if self.cached else 0
        self.state_bytes=8*(width*(4*source.r+2*source.s)+source.r+source.s)
        self.pushes=0;start=time.perf_counter_ns()
        try:
            check(self.lib.sp_compact_create(source.r,source.s,width,source.tr,source.tc,self.device_cache_bytes,C.byref(self.handle)))
            if self.cached:
                for key,tile in prefetched(source,self.pool):self.push(key,tile)
        except BaseException:
            self.close();raise
        self.preparation_ns=time.perf_counter_ns()-start

    def push(self,key,tile):
        i,j=key;nr,nc=tile.shape[1:]
        check(self.lib.sp_compact_push(self.handle,i,j,nr,nc,pointer(tile[0]),int(self.sparse)));self.pushes+=1

    def propose(self, slots, h, epsilon, steps):
        if not self.handle or not 1<=len(slots)<=self.width or not 1<=steps<=10000:
            raise ValueError('closed engine or proposal dimension')
        if any(type(s)!=int or not 0<=s<self.source.s for s in slots):raise ValueError('target slot')
        start=time.perf_counter_ns();cost=self.source.objectives(slots)
        check(self.lib.sp_compact_batch(self.handle,len(slots),float(h),float(epsilon),pointer(self.source.tau),pointer(self.source.sigma),pointer(cost)))
        check(self.lib.sp_compact_timer(self.handle,0))
        if self.cached:check(self.lib.sp_compact_run(self.handle,steps))
        else:
            for _ in range(steps):
                for phase in (0,1):
                    check(self.lib.sp_compact_phase(self.handle,phase,0))
                    for key,tile in prefetched(self.source,self.pool):self.push(key,tile)
                    check(self.lib.sp_compact_phase(self.handle,phase,1))
        check(self.lib.sp_compact_timer(self.handle,1))
        x=np.empty((len(slots),self.source.r));u=np.empty((len(slots),self.source.s));ms=C.c_double()
        check(self.lib.sp_compact_result(self.handle,pointer(x),pointer(u),C.byref(ms)))
        if not np.isfinite(x).all() or not np.isfinite(u).all():raise ArithmeticError('nonfinite compact proposal')
        return x,u,dict(width=len(slots),steps=steps,elapsed_ns=time.perf_counter_ns()-start,
            advancement_ms=ms.value,cached=self.cached,state_bytes=self.state_bytes,
            device_cache_bytes=self.device_cache_bytes,tile_uploads=self.pushes)

    def close(self):
        if self.handle:self.lib.sp_compact_destroy(self.handle);self.handle=C.c_void_p()
        if self.pool:self.pool.shutdown(wait=True);self.pool=None
    def __enter__(self):return self
    def __exit__(self,*_):self.close()


def exact_labels(oracle,target,x,u):
    if not np.isfinite(x).all() or not np.isfinite(u).all():return {}
    x=[max(-oracle.h,min(oracle.h,Q(float(v)))) for v in x]
    y=product(oracle.matrix,x,True,oracle.work);scale=Q(1)
    for value in y:
        if value>2:scale=min(scale,2/value)
        elif value < -oracle.epsilon:scale=min(scale,-oracle.epsilon/value)
    y=[v*scale for v in y];labels={}
    for i in range(oracle.n):
        if y[2*i+1]>=Q(1,4):labels[i]=1
        elif oracle.broadcast_negative and y[2*i]>=Q(1,4):labels[i]=-1
    if target not in labels:
        u=list(map(lambda v:Q(float(v)),u));bound=Q(0)
        for i in range(oracle.r):
            row=oracle.matrix.row(i)
            residual=row.get(2*target+1,Q(0))-sum((q*u[j] for j,q in row.items() if u[j]),Q(0))
            bound+=oracle.h*abs(residual);oracle.work.tick(bound,count=2*len(row))
        bound+=sum((2*v if v>=0 else -oracle.epsilon*v for v in u),Q(0))
        if bound<Q(1,4):labels[target]=-1
    return labels


class TileProof:
    def __init__(self,oracle,source):
        self.oracle=oracle;self.source=source;self.handle=C.c_void_p();self.closed=False;self.lib=C.CDLL(str(PROOF_LIBRARY))
        self.lib.sp_compact_proof_create.argtypes=[C.c_int,C.c_int]+[C.c_double]*4+[C.c_int,C.POINTER(C.c_void_p)]
        self.lib.sp_compact_proof_create.restype=C.c_int
        self.lib.sp_compact_proof_begin.argtypes=[C.c_void_p,C.c_int,PTR,PTR,C.c_uint64,C.c_uint64];self.lib.sp_compact_proof_begin.restype=C.c_int
        self.lib.sp_compact_proof_tile.argtypes=[C.c_void_p]+[C.c_int]*5+[PTR,PTR];self.lib.sp_compact_proof_tile.restype=C.c_int
        self.lib.sp_compact_proof_sparse.argtypes=[C.c_void_p]+[C.c_int]*6+[IPTR,IPTR,PTR,PTR];self.lib.sp_compact_proof_sparse.restype=C.c_int
        self.lib.sp_compact_proof_finish.argtypes=[C.c_void_p,C.c_int,IPTR,IPTR,C.POINTER(C.c_uint64)];self.lib.sp_compact_proof_finish.restype=C.c_int
        self.lib.sp_compact_proof_destroy.argtypes=[C.c_void_p];self.lib.sp_compact_proof_destroy.restype=None
        h,eps=enclosure(oracle.h),enclosure(oracle.epsilon)
        if h[0]>0 and eps[0]>0 and eps[1]<.25:
            NativeAuxiliary.check(self.lib.sp_compact_proof_create(oracle.r,2*oracle.n,*h,*eps,int(oracle.broadcast_negative),C.byref(self.handle)))
        self.sparse_cache=OrderedDict();self.sparse_bytes=0;self.sparse_peak=0

    def sparse_tile(self,key,tile):
        if key in self.sparse_cache:
            self.sparse_cache.move_to_end(key);return self.sparse_cache[key]
        rows,cols=np.nonzero((tile[1]!=0)|(tile[2]!=0))
        offsets=np.zeros(tile.shape[1]+1,dtype=np.int32)
        offsets[1:]=np.cumsum(np.bincount(rows,minlength=tile.shape[1]))
        arrays=(offsets,np.asarray(cols,dtype=np.int32),np.ascontiguousarray(tile[1,rows,cols]),np.ascontiguousarray(tile[2,rows,cols]))
        size=sum(a.nbytes for a in arrays)
        while self.sparse_cache and self.sparse_bytes+size>self.source.limit:
            _,old=self.sparse_cache.popitem(last=False);self.sparse_bytes-=sum(a.nbytes for a in old)
        if size<=self.source.limit:self.sparse_cache[key]=arrays;self.sparse_bytes+=size
        self.sparse_peak=max(self.sparse_peak,self.sparse_bytes)
        return arrays

    def batch(self,slots,x,u,known=None):
        o=self.oracle;labels=dict(known or {});fallbacks=checked=0;start=time.perf_counter_ns()
        if self.closed or any(type(i)!=int or not 0<=i<o.n or v not in (-1,1) for i,v in labels.items()):raise ValueError('closed checker or labels')
        if not x.flags.c_contiguous or not u.flags.c_contiguous or x.dtype!=np.float64 or u.dtype!=np.float64:raise ValueError('contiguous binary64 proposals required')
        if x.shape!=(len(slots),o.r) or u.shape!=(len(slots),2*o.n):raise ValueError('proof dimensions')
        for q,slot in enumerate(slots):
            target=slot//2
            if not 0<=slot<2*o.n:raise ValueError('proof slot')
            if target in labels:continue
            checked+=1;uncertain=C.c_int();ops=C.c_uint64();out=(C.c_int*o.n)(*(labels.get(i,0) for i in range(o.n)))
            if self.handle:
                remaining=o.work.seconds-(time.monotonic()-o.work.started)
                if remaining<=0:raise Limit('deadline')
                NativeAuxiliary.check(self.lib.sp_compact_proof_begin(self.handle,target,pointer(x[q]),pointer(u[q]),
                    int(remaining*1e9),max(1,o.work.max_operations-o.work.operations)))
                for phase in (0,1):
                    if phase and out[target]:break
                    for key in self.source.descriptors:
                        nr=min(self.source.tr,self.source.r-key[0]);nc=min(self.source.tc,self.source.s-key[1])
                        if self.source.nnz*4<self.source.r*self.source.s:
                            if key in self.sparse_cache:
                                self.sparse_cache.move_to_end(key);offsets,indices,lo,hi=self.sparse_cache[key]
                            else:offsets,indices,lo,hi=self.sparse_tile(key,self.source.tile(key))
                            NativeAuxiliary.check(self.lib.sp_compact_proof_sparse(self.handle,phase,*key,nr,nc,len(indices),
                                offsets.ctypes.data_as(IPTR),indices.ctypes.data_as(IPTR),pointer(lo),pointer(hi)))
                        else:
                            tile=self.source.tile(key)
                            NativeAuxiliary.check(self.lib.sp_compact_proof_tile(self.handle,phase,*key,nr,nc,pointer(tile[1]),pointer(tile[2])))
                    NativeAuxiliary.check(self.lib.sp_compact_proof_finish(self.handle,phase,out,C.byref(uncertain),C.byref(ops)))
                o.work.tick(count=ops.value);labels.update({i:v for i,v in enumerate(out) if v})
            else:uncertain.value=1
            if uncertain.value and len(labels)<o.n:
                found=exact_labels(o,target,x[q],u[q]);fallbacks+=1
                for i,v in found.items():
                    if i in labels and labels[i]!=v:raise ArithmeticError('tiled interval/exact contradiction')
                    labels[i]=v
        return labels,dict(checked=checked,exact_fallbacks=fallbacks,host_check_ns=time.perf_counter_ns()-start,
                           sparse_check_cache_peak=self.sparse_peak)

    def close(self):
        if self.handle:self.lib.sp_compact_proof_destroy(self.handle);self.handle=C.c_void_p()
        self.closed=True
    def __enter__(self):return self
    def __exit__(self,*_):self.close()


def proposals(oracle,width=32,steps=128,pipeline=True,device_cache_bytes=64<<20,host_cache_bytes=32<<20,sparse=True):
    try:
        if not np.isfinite(float(oracle.h)) or float(oracle.epsilon)<=0:raise OverflowError()
    except OverflowError:
        return {},dict(backend='compact_tiles',reason='compact_float_range',batches=[])
    width=min(width,max(1,(256<<20)//(8*(4*oracle.r+4*oracle.n))))
    if width>64 or width<1:raise ValueError('bounded width')
    begin=time.perf_counter_ns();source=TileSource(oracle.matrix,cache_bytes=host_cache_bytes)
    labels={};records=[];pending=None
    with TileEngine(source,width,device_cache_bytes,sparse) as engine,TileProof(oracle,source) as checker,ThreadPoolExecutor(max_workers=1,thread_name_prefix='compact-proof') as pool:
        prep=time.perf_counter_ns()-begin
        def merge(future):
            found,metadata=future.result()
            for i,v in found.items():
                if i in labels and labels[i]!=v:raise ArithmeticError('pipelined label contradiction')
                labels[i]=v
            return metadata
        slots=[2*i+h for i in range(oracle.n) for h in (1,0)]
        try:
            for first in range(0,len(slots),width):
                oracle.work.tick();requested=[s for s in slots[first:first+width] if s//2 not in labels]
                if not requested:continue
                x,u,record=engine.propose(requested,oracle.h,oracle.epsilon,steps)
                if pending is not None:records[-1]['proof']=merge(pending);pending=None
                if len(labels)==oracle.n:
                    record['proof']=dict(reason='resolved_by_prior_batch',checked=0,host_check_ns=0)
                    records.append(record);break
                future=pool.submit(checker.batch,requested,x,u,dict(labels));records.append(record)
                if pipeline:pending=future
                else:record['proof']=merge(future)
            if pending is not None:records[-1]['proof']=merge(pending);pending=None
        finally:
            if pending is not None:pending.result()
        return labels,dict(backend='compact_tiles',preparation_ns=prep,batches=records,
            pipeline=pipeline,max_inflight_checks=1,max_resident_searches=width,
            matrix_entries=oracle.r*2*oracle.n,nonzeros=source.nnz,
            host_tile_cache_peak=source.peak_bytes,device_cache_bytes=engine.device_cache_bytes,
            scalar_conversions=source.conversions,tile_cache_hits=source.hits)
