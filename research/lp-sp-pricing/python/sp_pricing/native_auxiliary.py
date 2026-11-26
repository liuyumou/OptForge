"""Native exact GMP auxiliary proposals, independently checked by geometry.py."""
import ctypes as C
from fractions import Fraction as Q
from pathlib import Path
import time
from .exact import Limit,rational

LIBRARY=Path(__file__).resolve().parents[2]/'target/cpu/libsp_auxiliary.so'


def strings(values):
    values=[rational(v) for v in values]
    return (C.c_char_p*len(values))(*(f'{v.numerator}/{v.denominator}'.encode() for v in values))


class NativeAuxiliary:
    def __init__(self,a,b,work,library=LIBRARY):
        self.work=work;self.m=len(b);self.n=len(a[0]);self.handle=C.c_void_p()
        self.lib=C.CDLL(str(library));ptr=C.POINTER(C.c_char_p)
        self.lib.sp_aux_create.argtypes=[C.c_int,C.c_int,ptr,ptr,C.c_uint64,C.POINTER(C.c_void_p)]
        self.lib.sp_aux_create.restype=C.c_int
        self.lib.sp_aux_solve.argtypes=[C.c_void_p,ptr,C.c_uint64,C.c_uint64,C.POINTER(C.c_void_p)]
        self.lib.sp_aux_solve.restype=C.c_int
        self.lib.sp_aux_destroy.argtypes=[C.c_void_p];self.lib.sp_aux_destroy.restype=None
        self.lib.sp_aux_free_string.argtypes=[C.c_void_p];self.lib.sp_aux_free_string.restype=None
        self.check(self.lib.sp_aux_create(self.m,self.n,strings(v for row in a for v in row),strings(b),work.max_bits,C.byref(self.handle)))
        work.tick(count=self.m*self.n)

    @staticmethod
    def check(code):
        if code in (1,2,3):raise Limit({1:'deadline',2:'native_auxiliary_operation_limit',3:'arithmetic_bit_limit'}[code])
        if code:raise ArithmeticError('native_auxiliary_'+str(code))

    def solve(self,objective):
        if not self.handle or len(objective)!=self.n:raise ValueError('auxiliary handle/dimension')
        remaining=self.work.seconds-(time.monotonic()-self.work.started)
        if remaining<=0:raise Limit('deadline')
        output=C.c_void_p();begin=time.perf_counter_ns()
        self.check(self.lib.sp_aux_solve(self.handle,strings(objective),int(remaining*1e9),
            max(1,self.work.max_operations-self.work.operations),C.byref(output)))
        try:lines=C.string_at(output).decode().splitlines()
        finally:self.lib.sp_aux_free_string(output)
        if len(lines)!=4+self.n+self.m:raise ArithmeticError('native auxiliary output length')
        x=list(map(Q,lines[3:3+self.n]));y=list(map(Q,lines[3+self.n:-1]));value=Q(lines[-1])
        self.work.tick(*x,*y,value,count=int(lines[2]))
        return dict(status=lines[0],pivots=int(lines[1]),x=x,y=y,value=value,
                    native_ns=time.perf_counter_ns()-begin,oracle='gmp_exact_shared_tableau_with_target_exit')

    def close(self):
        if self.handle:
            self.lib.sp_aux_destroy(self.handle);self.handle=C.c_void_p()

    def __enter__(self):return self
    def __exit__(self,*_):self.close()


def rref(a,work,columns):
    m,n=len(a),len(a[0]);lib=C.CDLL(str(LIBRARY));ptr=C.POINTER(C.c_char_p)
    lib.sp_rref.argtypes=[C.c_int]*3+[ptr,C.c_uint64,C.c_uint64,C.c_uint64,C.POINTER(C.c_void_p)]
    lib.sp_rref.restype=C.c_int
    lib.sp_aux_free_string.argtypes=[C.c_void_p];lib.sp_aux_free_string.restype=None
    remaining=work.seconds-(time.monotonic()-work.started)
    if remaining<=0:raise Limit('deadline')
    output=C.c_void_p()
    NativeAuxiliary.check(lib.sp_rref(m,n,columns,strings(v for row in a for v in row),work.max_bits,
        int(remaining*1e9),max(1,work.max_operations-work.operations),C.byref(output)))
    try:lines=C.string_at(output).decode().splitlines()
    finally:lib.sp_aux_free_string(output)
    rank=int(lines[0]);pivots=list(map(int,lines[2:2+rank]));values=list(map(Q,lines[2+rank:]))
    if len(values)!=m*n or len(pivots)!=rank:raise ArithmeticError('native RREF output dimensions')
    work.tick(*values,count=int(lines[1]))
    return [values[i*n:(i+1)*n] for i in range(m)],pivots
