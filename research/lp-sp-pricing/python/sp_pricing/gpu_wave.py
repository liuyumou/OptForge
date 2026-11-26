"""Synchronized auxiliary searches with rigorous interval/GMP acceptance."""
from concurrent.futures import ThreadPoolExecutor
import ctypes as C
import hashlib
import math
from pathlib import Path
import time

from .exact import Limit
from .gpu import GpuBatch
from .native_auxiliary import NativeAuxiliary
from .native_proof import NativeProof

CRATE=Path(__file__).resolve().parents[2]
GPU_LIBRARY=CRATE/'target/release/libsp_wave.so'
PROOF_LIBRARY=CRATE/'target/cpu/libsp_interval.so'
PTR=C.POINTER(C.c_double)
IPTR=C.POINTER(C.c_int)


def enclosure(q):
    """Enclose an original rational using an exact integer comparison."""
    f=float(q)
    if not math.isfinite(f):raise ValueError('coefficient outside finite binary64')
    numerator,denominator=f.as_integer_ratio()
    left=numerator*q.denominator;right=q.numerator*denominator
    return (f if left<=right else math.nextafter(f,-math.inf),
            f if left>=right else math.nextafter(f,math.inf))


class PackedBasis:
    def __init__(self,oracle):
        start=time.perf_counter_ns();size=oracle.r*2*oracle.n
        self.values=(C.c_double*size)();self.lo=(C.c_double*size)();self.hi=(C.c_double*size)()
        for i,q in enumerate(v for row in oracle.b for v in row):
            lo,hi=enclosure(q);self.values[i]=float(q);self.lo[i]=lo;self.hi[i]=hi
        self.h=enclosure(oracle.h);self.eps=enclosure(oracle.epsilon)
        self.elapsed_ns=time.perf_counter_ns()-start


class IntervalProof:
    def __init__(self,oracle,packed,library=PROOF_LIBRARY):
        self.oracle=oracle;self.handle=C.c_void_p();self.fallback=None;self.closed=False
        self.lib=C.CDLL(str(library));self.fallbacks=0
        self.lib.sp_interval_create.argtypes=[C.c_int,C.c_int,PTR,PTR]+[C.c_double]*4+[C.c_int,C.POINTER(C.c_void_p)]
        self.lib.sp_interval_create.restype=C.c_int
        self.lib.sp_interval_batch.argtypes=[C.c_void_p,C.c_int,IPTR,IPTR,PTR,PTR,IPTR,IPTR,IPTR,
            C.c_uint64,C.c_uint64,C.POINTER(C.c_uint64)]
        self.lib.sp_interval_batch.restype=C.c_int
        self.lib.sp_interval_destroy.argtypes=[C.c_void_p];self.lib.sp_interval_destroy.restype=None
        if packed.h[0]>0 and packed.eps[0]>0 and packed.eps[1]<.25:
            NativeAuxiliary.check(self.lib.sp_interval_create(oracle.r,2*oracle.n,packed.lo,packed.hi,
                *packed.h,*packed.eps,int(oracle.broadcast_negative),C.byref(self.handle)))

    def batch(self,slots,active,x,u,known):
        o=self.oracle;width=len(slots);labels=dict(known);stats=(C.c_uint64*4)()
        if self.closed or not 1<=width<=4096 or len(active)!=width or any(v not in (0,1) for v in active):
            raise ValueError('closed checker or batch dimensions')
        if any(type(s)!=int or not 0<=s<2*o.n for s in slots) or any(type(i)!=int or not 0<=i<o.n or sign not in (-1,1) for i,sign in known.items()):
            raise ValueError('invalid target or known label')
        if (isinstance(x,C.Array) and len(x)<width*o.r) or (isinstance(u,C.Array) and len(u)<width*2*o.n):
            raise ValueError('proposal buffer too short')
        targets=(C.c_int*width)(*(s//2 for s in slots));flags=(C.c_int*width)(*active)
        initial=(C.c_int*o.n)(*(known.get(i,0) for i in range(o.n)))
        output=(C.c_int*o.n)();uncertain=(C.c_int*width)()
        if self.handle:
            remaining=o.work.seconds-(time.monotonic()-o.work.started)
            if remaining<=0:raise Limit('deadline')
            NativeAuxiliary.check(self.lib.sp_interval_batch(self.handle,width,targets,flags,x,u,initial,output,uncertain,
                int(remaining*1e9),max(1,o.work.max_operations-o.work.operations),stats))
            o.work.tick(count=stats[0]);labels.update({i:sign for i,sign in enumerate(output) if sign})
        else:
            for i,flag in enumerate(active):uncertain[i]=flag
        fallbacks=0
        for offset,flag in enumerate(uncertain):
            if not flag or len(labels)==o.n:continue
            if self.fallback is None:self.fallback=NativeProof(o)
            proof=self.fallback.labels(slots[offset]//2,
                [x[offset*o.r+i] for i in range(o.r)],[u[offset*2*o.n+i] for i in range(2*o.n)])
            fallbacks+=1
            for i,sign in proof['established'].items():
                if i in labels and labels[i]!=sign:raise ArithmeticError('interval/GMP label contradiction')
                labels[i]=sign
        self.fallbacks+=fallbacks
        return labels,dict(interval_operations=int(stats[0]),checked_proposals=int(stats[1]),
            uncertain_proposals=int(stats[2]),interval_dual_certificates=int(stats[3]),gmp_fallbacks=fallbacks)

    def close(self):
        if self.fallback:self.fallback.close();self.fallback=None
        if self.handle:self.lib.sp_interval_destroy(self.handle);self.handle=C.c_void_p()
        self.closed=True
    def __enter__(self):return self
    def __exit__(self,*_):self.close()


class WaveEngine:
    def __init__(self,library=GPU_LIBRARY):
        start=time.perf_counter_ns();self.handle=C.c_void_p();self.path=Path(library)
        self.digest=hashlib.sha256(self.path.read_bytes()).hexdigest();self.lib=C.CDLL(str(self.path))
        self.lib.sp_wave_create.argtypes=[C.POINTER(C.c_void_p)];self.lib.sp_wave_create.restype=C.c_int
        self.lib.sp_wave_load.argtypes=[C.c_void_p,C.c_int,C.c_int,C.c_int,PTR,C.c_int,IPTR,C.c_double,C.c_double,PTR]
        self.lib.sp_wave_load.restype=C.c_int
        self.lib.sp_wave_advance.argtypes=[C.c_void_p,C.c_int,C.c_int,IPTR,PTR];self.lib.sp_wave_advance.restype=C.c_int
        self.lib.sp_wave_view.argtypes=[C.c_void_p,C.POINTER(PTR),C.POINTER(PTR)];self.lib.sp_wave_view.restype=C.c_int
        self.lib.sp_wave_destroy.argtypes=[C.c_void_p];self.lib.sp_wave_destroy.restype=C.c_int
        GpuBatch.check(self.lib.sp_wave_create(C.byref(self.handle)))
        self.initialization_ns=time.perf_counter_ns()-start

    def load(self,oracle,slots,packed,sparse):
        if not self.handle:raise ValueError('closed wave engine')
        self.width=len(slots);self.r=oracle.r;self.s=2*oracle.n;profile=(C.c_double*4)()
        start=time.perf_counter_ns()
        GpuBatch.check(self.lib.sp_wave_load(self.handle,self.r,self.s,int(sparse),packed.values,self.width,
            (C.c_int*self.width)(*slots),float(oracle.h),float(oracle.epsilon),profile))
        self.x=PTR();self.u=PTR();GpuBatch.check(self.lib.sp_wave_view(self.handle,C.byref(self.x),C.byref(self.u)))
        return dict(load_ns=time.perf_counter_ns()-start,host_pack_ns=int(profile[0]*1e9),
            allocation_ns=int(profile[1]*1e9),upload_and_views_ns=int(profile[2]*1e9),arena_bytes=int(profile[3]))

    def advance(self,steps,active):
        ids=[i for i,v in enumerate(active) if v];ms=C.c_double();start=time.perf_counter_ns()
        if len(active)!=self.width or any(v not in (0,1) for v in active):raise ValueError('active state dimensions')
        GpuBatch.check(self.lib.sp_wave_advance(self.handle,steps,len(ids),(C.c_int*max(1,len(ids)))(*ids),C.byref(ms)))
        return dict(elapsed_ns=time.perf_counter_ns()-start,device_iteration_ms=ms.value,
            active_slots=len(ids),steps=steps,width=self.width)

    def close(self):
        if self.handle:GpuBatch.check(self.lib.sp_wave_destroy(self.handle));self.handle=C.c_void_p()
    def __enter__(self):return self
    def __exit__(self,*_):self.close()


class WaveBackend:
    """One explicit solve-scoped backend; initialization overlaps CPU geometry."""
    def __init__(self,library=GPU_LIBRARY,asynchronous=True):
        self.library=library;self.engine=None;self.pool=None;self.future=None
        self.asynchronous=asynchronous;self.initialization_wait_ns=0
    def __enter__(self):
        if self.asynchronous:
            self.pool=ThreadPoolExecutor(max_workers=1,thread_name_prefix='pricing-cuda-init')
            self.future=self.pool.submit(WaveEngine,self.library)
        return self
    def __call__(self,oracle,library=None,width=64,sparse=True,steps=1000,backend='wave',**unused):
        if backend!='wave' or not 1<=steps<=10000:raise ValueError('wave configuration')
        if oracle.r*2*oracle.n>1000000 or 3*oracle.r+2*oracle.n>6144 or 2*oracle.n>4096 or 2*oracle.n*(3*oracle.r+2*oracle.n)>16000000:
            return {},[],dict(backend='wave',reason='wave_shape_limit',gpu_labels=0,batches=[],preparation_ns=0)
        packed=PackedBasis(oracle);wait=time.perf_counter_ns()
        if self.engine is None:self.engine=self.future.result() if self.future else WaveEngine(self.library)
        waited=time.perf_counter_ns()-wait;self.initialization_wait_ns+=waited
        # All signed objectives advance through common checkpoints. No padding,
        # separate precision pass or per-objective Python state reconstruction.
        slots=[2*i+h for i in range(oracle.n) for h in (1,0)]
        load=self.engine.load(oracle,slots,packed,sparse);labels={};batches=[];previous=0
        with IntervalProof(oracle,packed) as checker:
            for stage in sorted({min(64,steps),min(256,steps),steps}):
                active=[int(s//2 not in labels) for s in slots]
                if not any(active):break
                oracle.work.tick();row=self.engine.advance(stage-previous,active);previous=stage
                start=time.perf_counter_ns()
                labels,statistics=checker.batch(slots,active,self.engine.x,self.engine.u,labels)
                batches.append(dict(**row,**statistics,cumulative_steps=stage,exact_check_ns=time.perf_counter_ns()-start))
                if stage>=256 and not labels:break
        return labels,[],dict(backend='wave',gpu_labels=len(labels),batches=batches,sparse=sparse,
            preparation_ns=packed.elapsed_ns+waited+load['load_ns'],basis_conversion_ns=packed.elapsed_ns,
            initialization_wait_ns=waited,session_initialization_ns=self.engine.initialization_ns,
            preparation_components=load,native_sha256=self.engine.digest,synchronized_targets=len(slots),
            rigorous_interval_checks=True,gmp_fallbacks=checker.fallbacks,full_proposal_traces=False,
            tensor_cores=False,precision_restarts=0)
    def __exit__(self,*_):
        try:
            if self.engine is None and self.future is not None:self.engine=self.future.result()
            if self.engine:self.engine.close()
        finally:
            if self.pool:self.pool.shutdown(wait=True)
