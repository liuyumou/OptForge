"""Lean FP64 proposals: reusable state, one launch per stage, exact early exits."""
import ctypes as C
import time
from .gpu import GpuBatch
from .native_proof import NativeProof


class LeanBatch(GpuBatch):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        ptr=C.POINTER(C.c_double)
        self.lib.sp_begin.argtypes=[C.c_void_p,C.c_int,C.POINTER(C.c_int),C.c_double,C.c_double]
        self.lib.sp_begin.restype=C.c_int
        self.lib.sp_active.argtypes=[C.c_void_p,C.POINTER(C.c_int)];self.lib.sp_active.restype=C.c_int
        self.lib.sp_advance.argtypes=[C.c_void_p,C.c_int,ptr,ptr,ptr];self.lib.sp_advance.restype=C.c_int
        self.width=0

    def begin(self,slots,h,epsilon):
        if not self.handle or len(slots) not in (1,8,32,64):raise ValueError('batch width/closed engine')
        self.width=len(slots)
        self.check(self.lib.sp_begin(self.handle,self.width,(C.c_int*self.width)(*slots),float(h),float(epsilon)))
        self.x=(C.c_double*(self.width*self.r))();self.u=(C.c_double*(self.width*self.s))()

    def active(self,flags):
        if not self.handle or len(flags)!=self.width or any(v not in (0,1) for v in flags):
            raise ValueError('active-state dimensions')
        self.check(self.lib.sp_active(self.handle,(C.c_int*self.width)(*flags)))

    def advance(self,steps):
        if not self.handle or not self.width or not 1<=steps<=10000:raise ValueError('advance configuration')
        ms=C.c_double();begin=time.perf_counter_ns()
        self.check(self.lib.sp_advance(self.handle,steps,self.x,self.u,C.byref(ms)))
        return dict(x=[list(self.x[i*self.r:(i+1)*self.r]) for i in range(self.width)],
            dual=[list(self.u[i*self.s:(i+1)*self.s]) for i in range(self.width)],
            elapsed_ns=time.perf_counter_ns()-begin,device_iteration_ms=ms.value,
            width=self.width,steps=steps,mode='fp64')


def propose_labels(oracle,library,width,sparse=False,steps=1000):
    if width not in (1,8,32,64) or not 1<=steps<=10000:raise ValueError('lean proposal configuration')
    if oracle.r*2*oracle.n>1000000 or 3*oracle.r+2*oracle.n>6144:
        return {},[],dict(gpu_labels=0,batches=[],preparation_ns=0,reason='persistent_shape_limit',backend='lean')
    labels={};traces=[];checks=skipped=0;stalled=False
    # No precision restart: stages continue the same primal/dual state.
    stages=sorted({min(64,steps),min(256,steps),steps})
    with NativeProof(oracle) as checker,LeanBatch(library,oracle.b,sparse) as engine:
        pilot_count=min(oracle.n,max(1,width//2))
        pilot=[i*oracle.n//pilot_count for i in range(pilot_count)]
        sampled=set(pilot)
        order=pilot+[i for i in range(oracle.n) if i not in sampled]
        pending=[2*i+h for i in order for h in (1,0)]
        for start in range(0,len(pending),width):
            slots=[s for s in pending[start:start+width] if s//2 not in labels]
            if not slots:continue
            actual=min(w for w in (1,8,32,64) if w>=len(slots))
            padded=slots+[slots[-1]]*(actual-len(slots))
            engine.begin(padded,oracle.h,oracle.epsilon);previous=0
            for stage in stages:
                active=[int(i<len(slots) and s//2 not in labels) for i,s in enumerate(padded)]
                if not any(active):break
                oracle.work.tick();engine.active(active)
                result=engine.advance(stage-previous);previous=stage
                begin=time.perf_counter_ns();checked=0
                for offset,slot in enumerate(slots):
                    if not active[offset] or slot//2 in labels:
                        skipped+=1;continue
                    proof=checker.labels(slot//2,result['x'][offset],result['dual'][offset])
                    checked+=1;checks+=1
                    for i,sign in proof.get('established',{}).items():
                        if i in labels and labels[i]!=sign:raise ArithmeticError('inconsistent exact GPU labels')
                        labels[i]=sign
                traces.append({k:v for k,v in result.items() if k not in ('x','dual')}
                    |dict(active_slots=sum(active),checked_proposals=checked,cumulative_steps=stage,
                          exact_check_ns=time.perf_counter_ns()-begin))
                if stage>=256 and not labels:
                    stalled=True
                    break
            if stalled:break
        metadata=dict(backend='lean',preparation_ns=engine.preparation_ns,
            checker_preparation_ns=checker.preparation_ns,native_sha256=engine.digest,
            sparse=sparse,batches=traces,gpu_labels=len(labels),checked_proposals=checks,
            skipped_resolved_proposals=skipped,product_backend='persistent_cuda_fp64',
            tensor_cores=False,precision_restarts=0,full_proposal_traces=False,
            preconditioning='diagonal_absolute_row_column_sums',
            exact_cpu_handoff='no_exact_label_after_pilot' if stalled else 'unresolved_targets')
    # Checked witnesses are consumed here. The final original-model certificate
    # is retained and independently verified; optional proposal traces are not
    # required to drive the search and would add serialization/memory cost.
    return labels,[],metadata
