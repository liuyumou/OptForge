"""Native exact geometry and independently proved numerical factor proposals."""
import ctypes as C
from fractions import Fraction as Q
from pathlib import Path
import time
from unittest.mock import patch
import numpy as np
from scipy import sparse, linalg
from scipy.sparse.linalg import splu, lsmr
from .compact_basis import Rows, Storage
from .compact_solver import CompactSolver
from .exact import Limit, rational

ROOT=Path(__file__).resolve().parents[2]
LIBRARY=ROOT/'target/cpu/libsp_geometry_exact.so'
GPU_LIBRARY=ROOT/'target/release/libsp_geometry_rank.so'
U64=C.POINTER(C.c_uint64);I32=C.POINTER(C.c_int);I64=C.POINTER(C.c_int64)


def library():
    lib=C.CDLL(str(LIBRARY))
    lib.sp_geometry_rref.argtypes=[C.c_int]*3+[U64,I32,C.POINTER(C.c_char_p)]+[C.c_uint64]*6+[C.POINTER(C.c_void_p)]
    lib.sp_geometry_rref.restype=C.c_int;lib.sp_geometry_free.argtypes=[C.c_void_p]
    lib.sp_geometry_certificate.argtypes=[C.c_int]*2+[U64,I32,I64,C.c_uint64,I64,I64,I64,C.c_int,I64,C.c_int]
    lib.sp_geometry_certificate.restype=C.c_int
    return lib


def remaining(work):
    work.tick();return max(1,int((work.seconds-(time.monotonic()-work.started))*1e9))


def native_rref(rows,columns,work,storage,coefficient_columns=None):
    rows=list(rows)
    if not rows:return Rows([],columns),[]
    start=time.perf_counter_ns();offsets=[0];indices=[];values=[];cache={}
    for row in rows:
        for j,q in sorted(row.items()):
            q=rational(q)
            if not q:continue
            text=cache.get(q)
            if text is None:
                text=(str(q.numerator)+'/'+str(q.denominator)).encode()
                if len(cache)>=4096:cache.clear()
                cache[q]=text
            indices.append(j);values.append(text)
        offsets.append(len(indices));work.tick(count=len(row))
    off=np.asarray(offsets,dtype=np.uint64);idx=np.asarray(indices,dtype=np.int32)
    strings=(C.c_char_p*len(values))(*values);out=C.c_void_p();lib=library()
    code=lib.sp_geometry_rref(len(rows),columns,columns if coefficient_columns is None else coefficient_columns,
        off.ctypes.data_as(U64),idx.ctypes.data_as(I32),strings,len(values),work.max_bits,remaining(work),
        max(1,work.max_operations-work.operations),storage.entries,storage.bytes_limit,C.byref(out))
    if code:
        if code in (1,2,3,8):raise Limit({1:'deadline',2:'operation_limit',3:'arithmetic_bit_limit',8:'compact_exact_storage_limit'}[code])
        raise ArithmeticError('native_geometry_'+str(code))
    try:lines=C.string_at(out).decode().splitlines()
    finally:lib.sp_geometry_free(out)
    ops,bits,fill,count=map(int,lines[0].split());pivots=list(map(int,lines[1].split()));answer=[]
    for line in lines[2:]:
        parts=line.split();size=int(parts[0]);assert len(parts)==1+2*size
        answer.append({int(parts[1+2*k]):Q(parts[2+2*k]) for k in range(size)})
    if len(answer)!=count:raise ArithmeticError('native geometry output')
    work.peak_bits=max(work.peak_bits,bits);work.tick(count=ops);storage.peak_entries=max(storage.peak_entries,fill);storage.check(answer)
    return Rows(answer,columns),pivots


def rank_proof(rows,columns,work,gpu=False):
    """Only a full modular rank proves a rational conclusion; failure is unknown."""
    rows=list(rows);m=len(rows);p=65521
    if m<columns or m*columns>1<<28:return False,dict(reason='rank_shape')
    start=time.perf_counter_ns();offsets=[0];indices=[];values=[];cache={}
    for row in rows:
        for j,q in row.items():
            if not 0<=j<columns:raise ValueError('rank column')
            q=rational(q);v=cache.get(q)
            if v is None:
                if q.denominator%p==0:return False,dict(reason='noninvertible_denominator')
                v=(q.numerator%p)*pow(q.denominator,-1,p)%p
                if len(cache)>=4096:cache.clear()
                cache[q]=v
            indices.append(j);values.append(v)
        offsets.append(len(values));work.tick(count=len(row))
    data=sparse.csr_matrix((np.asarray(values,dtype=np.uint32),np.asarray(indices,dtype=np.int32),
        np.asarray(offsets,dtype=np.int64)),shape=(m,columns)).toarray()
    prepared=time.perf_counter_ns();lib=C.CDLL(str(GPU_LIBRARY if gpu else LIBRARY));fn=getattr(lib,'sp_geometry_rank_gpu' if gpu else 'sp_geometry_rank_cpu')
    fn.argtypes=[C.c_int,C.c_int,C.POINTER(C.c_uint32),C.c_uint64,C.POINTER(C.c_int)];fn.restype=C.c_int
    rank=C.c_int();code=fn(m,columns,data.ctypes.data_as(C.POINTER(C.c_uint32)),remaining(work),C.byref(rank))
    if code==1:raise Limit('modular_rank_deadline')
    if code:raise ArithmeticError('modular_rank_'+str(code))
    work.tick();return rank.value==columns,dict(prime=p,rank=rank.value,columns=columns,gpu=gpu,
        packing_ns=prepared-start,native_ns=time.perf_counter_ns()-prepared,allocated_matrix_bytes=data.nbytes,
        arithmetic='exact_uint32_field',full_rank_proved=rank.value==columns)


def dyadic_integers(arrays):
    if any(not np.isfinite(a).all() for a in arrays):return None
    for exponent in range(25):
        scaled=[np.ldexp(a,exponent) for a in arrays]
        if all((np.abs(a)<=2**40).all() and np.equal(a,np.rint(a)).all() for a in scaled):
            return exponent,[np.ascontiguousarray(a,dtype=np.int64) for a in scaled]
    return None


def exact_certificate(a,b,c,x,px,y,py,integer_model=None):
    a=a.tocsr(copy=False)
    if not a.has_canonical_format:raise ValueError('canonical CSR required')
    if (np.shape(b)!=(a.shape[0],) or np.shape(c)!=(a.shape[1],) or np.shape(x)!=(a.shape[1],)
            or np.shape(y)!=(a.shape[0],) or not 0<=px<=24 or not 0<=py<=24):raise ValueError('certificate dimensions')
    if any(np.asarray(v).dtype.kind not in 'iu' for v in (x,y)):raise ValueError('integer endpoint required')
    encoded=integer_model or dyadic_integers([a.data,b,c])
    if encoded is None:return False
    _,(av,bv,cv)=encoded
    arrays=[np.asarray(a.indptr,dtype=np.uint64),np.asarray(a.indices,dtype=np.int32),av,bv,cv,
            np.ascontiguousarray(x,dtype=np.int64),np.ascontiguousarray(y,dtype=np.int64)]
    off,idx,av,bv,cv,xv,yv=arrays
    code=library().sp_geometry_certificate(a.shape[0],a.shape[1],off.ctypes.data_as(U64),idx.ctypes.data_as(I32),
        av.ctypes.data_as(I64),a.nnz,bv.ctypes.data_as(I64),cv.ctypes.data_as(I64),xv.ctypes.data_as(I64),px,yv.ctypes.data_as(I64),py)
    if code not in (0,1,4):raise ArithmeticError('geometry_certificate_'+str(code))
    return code==0


def certified_factor_proposal(a,b,c,work):
    """Numerical solves propose only. Exact original inequalities and gap decide."""
    start=time.perf_counter_ns();a=a.tocsr(copy=False);m,n=a.shape;metadata=dict(method=None,accepted=False)
    if not a.has_canonical_format:raise ValueError('canonical CSR required')
    encoded=dyadic_integers([a.data,b,c])
    if encoded is None:return None,dict(reason='dyadic_fast_check_range',accepted=False)
    try:
        # Inherit the unchanged supervisor's one-thread BLAS environment.
        if m==n:
            if a.nnz>m*n//5 and n<=4096:
                factor=linalg.lu_factor(a.toarray(),check_finite=True);x=linalg.lu_solve(factor,b);y=linalg.lu_solve(factor,c,trans=1)
                metadata['method']='lapack_lu_two_sides'
            else:
                factor=splu(a.tocsc());x=factor.solve(b);y=factor.solve(c,trans='T');metadata['method']='sparse_lu_two_sides'
        else:
            x=lsmr(a,b,atol=1e-9,btol=1e-9,maxiter=128)[0]
            y=lsmr(a.T,c,atol=1e-9,btol=1e-9,maxiter=128)[0];metadata['method']='lsmr_two_sides_128'
    except (RuntimeError,ValueError,np.linalg.LinAlgError):
        return None,dict(method=metadata['method'],reason='numerical_factor_failed',accepted=False)
    work.tick();metadata['factor_ns']=time.perf_counter_ns()-start
    if not np.isfinite(x).all() or not np.isfinite(y).all():return None,dict(**metadata,reason='nonfinite_proposal')
    candidates=[]
    for vector,primal in ((x,True),(y,False)):
        choices=[];seen=set()
        for exponent in range(25):
            scaled=np.rint(np.ldexp(vector,exponent))
            if (np.abs(scaled)>2**40).any():break
            integer=np.ascontiguousarray(scaled,dtype=np.int64);point=np.ldexp(integer.astype(float),-exponent)
            key=point.tobytes()
            if key in seen:continue
            seen.add(key)
            if primal:
                if np.max(a@point-b,initial=0)>1e-9*(1+np.max(np.abs(b),initial=0)):continue
            elif (point<0).any() or np.max(np.abs(a.T@point-c),initial=0)>1e-9*(1+np.max(np.abs(c),initial=0)):continue
            choices.append((integer,exponent))
        candidates.append(choices)
    metadata['quantization_ns']=time.perf_counter_ns()-start-metadata['factor_ns'];checks=0
    for xv,px in candidates[0]:
        for yv,py in candidates[1]:
            checks+=1
            if exact_certificate(a,b,c,xv,px,yv,py,encoded):
                proof=dict(status='optimal',x=[Q(int(v),1<<px) for v in xv],y=[Q(int(v),1<<py) for v in yv])
                metadata.update(accepted=True,exact_checks=checks,complete_ns=time.perf_counter_ns()-start,
                    primal_exponent=px,dual_exponent=py,model_exponent=encoded[0])
                work.tick();return proof,metadata
            work.tick()
    metadata.update(exact_checks=checks,complete_ns=time.perf_counter_ns()-start)
    return None,metadata


class FastGeometrySolver(CompactSolver):
    def __init__(self,*args,rank_gpu=False,**kwargs):
        super().__init__(*args,**kwargs);self.rank_gpu=rank_gpu;self.geometry_diagnostics=[]

    def fast_rref(self,rows,columns,work,storage,coefficient_columns=None):
        rows=list(rows);start=time.perf_counter_ns();metadata=dict(rows=len(rows),columns=columns)
        if len(rows)>=columns and coefficient_columns in (None,columns) and (columns<=128 or self.rank_gpu):
            proved,detail=rank_proof(rows,columns,work,self.rank_gpu and columns>128);metadata['modular']=detail
            if proved:
                result=Rows([{i:Q(1)} for i in range(columns)],columns),list(range(columns))
                metadata.update(method='proved_full_space',complete_ns=time.perf_counter_ns()-start)
                self.geometry_diagnostics.append(metadata);storage.check(result[0].rows);return result
        try:return native_rref(rows,columns,work,storage,coefficient_columns)
        finally:
            metadata.update(method='native_sparse_gmp',complete_ns=time.perf_counter_ns()-start)
            self.geometry_diagnostics.append(metadata)

    def feasibility(self,*args,**kwargs):
        from . import compact_solver
        with patch.object(compact_solver,'sparse_rref',self.fast_rref):return super().feasibility(*args,**kwargs)
