"""Lazy single-inverse correction cache, with alternate basis only on construction failure."""
from contextlib import contextmanager
import ctypes
import math
from pathlib import Path
import time
import numpy as np
from .dual_recovery_fast import primal,dyadic_integers
from .factor_projection import inverse_proposal

@contextmanager
def blas_threads(count):
    """Scope installed OpenBLAS thread limits; unsupported libraries stay unchanged."""
    libraries=[]
    for path in sorted({line.split()[-1] for line in Path('/proc/self/maps').read_text().splitlines() if 'openblas' in line and line.split()[-1].startswith('/')}):
        lib=ctypes.CDLL(path)
        for prefix,suffix in (('scipy_','64_'),('scipy_',''),('','64_'),('','')):
            get=getattr(lib,prefix+'openblas_get_num_threads'+suffix,None);set_=getattr(lib,prefix+'openblas_set_num_threads'+suffix,None)
            if get is not None and set_ is not None:
                get.restype=ctypes.c_int;set_.argtypes=[ctypes.c_int];old=get();set_(count);libraries.append((lib,get,set_,old));break
    try:yield [dict(library=lib._name,threads=get()) for lib,get,_,_ in libraries]
    finally:
        for _,_,set_,old in reversed(libraries):set_(old)

class CachedCorrection:
    def __init__(self,a,b,c,gpu=False):
        self.a,self.b,self.c=a,b,c;self.gpu=gpu;self.encoded=None;self.cache=[];self.builds=0;self.hits=0
    def build(self,x,y):
        start=time.perf_counter_ns()
        if self.encoded is None:self.encoded=dyadic_integers([self.a.data,self.b,self.c])
        point,detail=primal(self.a,self.b,self.c,x,self.encoded)
        if point is None:return None,detail
        xp,active,px=point;n=self.a.shape[1]
        if not np.isfinite(y).all():return None,dict(reason='nonfinite_dual',**detail)
        maximum=float(np.max(np.maximum(y,0.),initial=0))
        if maximum>2**52:return None,dict(reason='dual_base_range',**detail)
        py=max(0,min(48,52-math.frexp(maximum)[1] if maximum else 48));q=np.rint(np.ldexp(np.maximum(y,0.),py))
        if np.max(q,initial=0)>2**52:return None,dict(reason='dual_base_range',**detail)
        y0=np.ldexp(q,-py);y0[~active]=0.;available=np.flatnonzero(active&(y0>0))
        if len(available)<n:return None,dict(reason='insufficient_positive_active_rows',**detail)
        # Matrix entries never change. Reuse only bases still exactly active and positive.
        usable=[item for item in self.cache if np.all(active[item[0]]) and np.all(y0[item[0]]>0)]
        records=[]
        if not usable:
            self.cache=[]
            choices=(available[np.argsort(-y0[available],kind='stable')[:n]],available[np.linspace(0,len(available)-1,n,dtype=int)])
            for selected in choices:
                if any(np.array_equal(selected,k) for k,_ in self.cache):continue
                begin=time.perf_counter_ns()
                try:
                    inverse=inverse_proposal(self.a[selected].toarray().T,gpu=self.gpu)
                    if not np.isfinite(inverse).all():raise ArithmeticError('nonfinite inverse')
                except (ArithmeticError,ValueError,np.linalg.LinAlgError) as error:records.append(dict(reason=str(error),inverse_ns=time.perf_counter_ns()-begin));continue
                self.cache.append((selected.copy(),inverse));self.builds+=1;records.append(dict(inverse_ns=time.perf_counter_ns()-begin,gpu=self.gpu));break
            usable=self.cache
        else:self.hits+=len(usable)
        for selected,inverse in usable:
            begin=time.perf_counter_ns();refined=y0.copy();steps=0
            for _ in range(2):
                residual=self.c-np.asarray(self.a.T@refined).ravel();q=np.rint(np.ldexp(refined[selected]+inverse@residual,py))
                if not np.isfinite(q).all() or np.min(q,initial=0)<0 or np.max(q,initial=0)>2**52:break
                refined[selected]=np.ldexp(q,-py);steps+=1
            records.append(dict(screen_ns=time.perf_counter_ns()-begin,refinement_steps=steps))
            if steps==2:
                return dict(x=xp,y0=refined,basis=selected.astype(np.uint32),inverse=inverse),dict(method='cached_active_basis_correction',primal_exponent=px,dual_base_exponent=py,records=records,cache_builds=self.builds,cache_hits=self.hits,resident_inverses=len(self.cache),gpu_inverse=self.gpu,elapsed_ns=time.perf_counter_ns()-start,**detail)
        return None,dict(reason='no_positive_cached_correction',records=records,cache_builds=self.builds,cache_hits=self.hits,resident_inverses=len(self.cache),elapsed_ns=time.perf_counter_ns()-start,**detail)
