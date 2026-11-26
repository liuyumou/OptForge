"""Reject negative numerical corrections before solving for every inverse column."""
import math
import time
import numpy as np
from scipy import linalg
from .dual_recovery_fast import primal


def build(a,b,c,x,y,encoded=None):
    start=time.perf_counter_ns();point,detail=primal(a,b,c,x,encoded)
    if point is None:return None,detail
    xp,active,px=point;n=a.shape[1]
    if not np.isfinite(y).all():return None,dict(reason='nonfinite_dual',**detail)
    maximum=float(np.max(np.maximum(y,0.),initial=0))
    if maximum>2**52:return None,dict(reason='dual_base_range',**detail)
    py=max(0,min(48,52-math.frexp(maximum)[1] if maximum else 48));rounded=np.rint(np.ldexp(np.maximum(y,0.),py))
    if np.max(rounded,initial=0)>2**52:return None,dict(reason='dual_base_range',**detail)
    y0=np.ldexp(rounded,-py);y0[~active]=0.;available=np.flatnonzero(active&(y0>0))
    if len(available)<n:return None,dict(reason='insufficient_positive_active_rows',**detail)
    attempts=[]
    for selected in (available[np.argsort(-y0[available],kind='stable')[:n]],available[np.linspace(0,len(available)-1,n,dtype=int)]):
        begin=time.perf_counter_ns()
        try:
            factor=linalg.lu_factor(a[selected].toarray().T,check_finite=True);refined=y0.copy();steps=0
            for _ in range(2):
                residual=c-np.asarray(a.T@refined).ravel();q=np.rint(np.ldexp(refined[selected]+linalg.lu_solve(factor,residual,check_finite=False),py))
                if not np.isfinite(q).all() or np.min(q,initial=0)<0 or np.max(q,initial=0)>2**52:break
                refined[selected]=np.ldexp(q,-py);steps+=1
            screen_ns=time.perf_counter_ns()-begin
            if steps<2:
                attempts.append(dict(reason='negative_or_nonfinite_proposed_correction',screen_ns=screen_ns,inverse_constructed=False));continue
            begin=time.perf_counter_ns();inverse=linalg.lu_solve(factor,np.eye(n),check_finite=False)
            if not np.isfinite(inverse).all():raise ArithmeticError('nonfinite inverse')
        except (ArithmeticError,ValueError,np.linalg.LinAlgError) as error:attempts.append(dict(reason=str(error)));continue
        return dict(x=xp,y0=refined,basis=selected.astype(np.uint32),inverse=inverse),dict(method='positivity_screened_implicit_dual',primal_exponent=px,dual_base_exponent=py,
            factor_and_screen_ns=screen_ns,inverse_ns=time.perf_counter_ns()-begin,numerical_dual_refinement_steps=steps,builder_inverse_bound_omitted=True,
            active_rows=int(active.sum()),inverse_entries=n*n,attempts=attempts,elapsed_ns=time.perf_counter_ns()-start,**detail)
    return None,dict(reason='no_positive_correction_proposal',attempts=attempts,elapsed_ns=time.perf_counter_ns()-start,**detail)
