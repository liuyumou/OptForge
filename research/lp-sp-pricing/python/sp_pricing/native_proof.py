"""Native exact acceptance of GPU proposals; the Python oracle stays independent."""
import ctypes as C
from fractions import Fraction as Q
import math
from pathlib import Path
import time
from .exact import Limit, rational
from .native_auxiliary import NativeAuxiliary, strings

LIBRARY=Path(__file__).resolve().parents[2]/'target/cpu/libsp_proof.so'


class NativeProof:
    def __init__(self, oracle, library=LIBRARY):
        self.oracle=oracle;self.handle=C.c_void_p();self.lib=C.CDLL(str(library))
        self.lib.sp_proof_create.argtypes=[C.c_int,C.c_int,C.POINTER(C.c_char_p),C.c_char_p,C.c_char_p,
                                          C.c_uint64,C.c_int,C.POINTER(C.c_void_p)]
        self.lib.sp_proof_create.restype=C.c_int
        self.lib.sp_proof_check.argtypes=[C.c_void_p,C.c_int,C.POINTER(C.c_double),C.POINTER(C.c_double),
                                         C.c_int,C.c_uint64,C.c_uint64,C.POINTER(C.c_void_p)]
        self.lib.sp_proof_check.restype=C.c_int
        self.lib.sp_proof_labels.argtypes=self.lib.sp_proof_check.argtypes;self.lib.sp_proof_labels.restype=C.c_int
        self.lib.sp_proof_free_string.argtypes=[C.c_void_p];self.lib.sp_proof_free_string.restype=None
        self.lib.sp_proof_destroy.argtypes=[C.c_void_p];self.lib.sp_proof_destroy.restype=None
        begin=time.perf_counter_ns()
        text=lambda q:f'{q.numerator}/{q.denominator}'.encode()
        NativeAuxiliary.check(self.lib.sp_proof_create(oracle.r,2*oracle.n,strings(v for row in oracle.b for v in row),
            text(oracle.h),text(oracle.epsilon),oracle.work.max_bits,int(oracle.broadcast_negative),C.byref(self.handle)))
        oracle.work.tick(count=4*oracle.r*2*oracle.n)
        self.preparation_ns=time.perf_counter_ns()-begin

    def check(self,target,x,u,full_dual=False):
        o=self.oracle
        if not self.handle or not 0<=target<o.n or len(x)!=o.r or len(u)!=2*o.n:
            raise ValueError('proposal dimensions/closed checker')
        if any(not math.isfinite(v) for v in [*x,*u]):
            return dict(accepted=False,reason='nonfinite_proposal')
        remaining=o.work.seconds-(time.monotonic()-o.work.started)
        if remaining<=0:raise Limit('deadline')
        data=C.c_void_p();begin=time.perf_counter_ns()
        NativeAuxiliary.check(self.lib.sp_proof_check(self.handle,target,(C.c_double*len(x))(*x),(C.c_double*len(u))(*u),
            int(full_dual),int(remaining*1e9),max(1,o.work.max_operations-o.work.operations),C.byref(data)))
        try:lines=C.string_at(data).decode().splitlines()
        finally:self.lib.sp_proof_free_string(data)
        if len(lines)!=4+o.r+2*o.n:raise ArithmeticError('native proof output dimensions')
        values=list(map(Q,lines[4:]));x,y=values[:o.r],values[o.r:]
        upper=None if lines[2]=='none' else Q(lines[2])
        o.work.peak_bits=max(o.work.peak_bits,int(lines[1]));o.work.tick(*values,count=int(lines[0]))
        established={}
        for i in range(o.n):
            if y[2*i+1]>=Q(1,4):established[i]=1
            elif o.broadcast_negative and y[2*i]>=Q(1,4):established[i]=-1
        if upper is not None and upper<Q(1,4):
            if established.get(target)==1:raise ArithmeticError('contradictory exact proposals')
            established[target]=-1
        return dict(accepted=target in established,target=target,established=established,x=x,witness=y,
            dual=list(map(rational,u)) if upper is not None else None,dual_upper=upper,epoch=o.epoch,
            kind='exact_checked_native_gpu_proposal',integer_products=int(lines[3]),native_check_ns=time.perf_counter_ns()-begin)

    def close(self):
        if self.handle:self.lib.sp_proof_destroy(self.handle);self.handle=C.c_void_p()
    def __enter__(self):return self
    def __exit__(self,*_):self.close()

    def labels(self,target,x,u):
        """Return only exact label decisions; do not serialize unused witnesses."""
        o=self.oracle
        if not self.handle or not 0<=target<o.n or len(x)!=o.r or len(u)!=2*o.n:
            raise ValueError('proposal dimensions/closed checker')
        if any(not math.isfinite(v) for v in [*x,*u]):return dict(accepted=False,established={},reason='nonfinite_proposal')
        remaining=o.work.seconds-(time.monotonic()-o.work.started)
        if remaining<=0:raise Limit('deadline')
        data=C.c_void_p();begin=time.perf_counter_ns()
        NativeAuxiliary.check(self.lib.sp_proof_labels(self.handle,target,(C.c_double*len(x))(*x),(C.c_double*len(u))(*u),
            0,int(remaining*1e9),max(1,o.work.max_operations-o.work.operations),C.byref(data)))
        try:lines=C.string_at(data).decode().splitlines()
        finally:self.lib.sp_proof_free_string(data)
        if len(lines)!=4 or len(lines[3])!=o.n or any(c not in '+-0' for c in lines[3]):raise ArithmeticError('native label output dimensions')
        o.work.peak_bits=max(o.work.peak_bits,int(lines[1]));o.work.tick(count=int(lines[0]))
        established={i:1 if sign=='+' else -1 for i,sign in enumerate(lines[3]) if sign!='0'}
        return dict(accepted=target in established,established=established,integer_products=int(lines[2]),
                    native_check_ns=time.perf_counter_ns()-begin)
