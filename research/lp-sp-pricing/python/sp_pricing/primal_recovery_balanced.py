"""Balanced sparse-wide correction bases; original kernels/checker unchanged."""
from unittest.mock import patch
import numpy as np
from . import primal_recovery as original
from .implicit_certificate import inverse_bound

def build(a,b,c,x,y,gpu_inverse=False):
    m,n=a.shape
    if not (0<m<n and a.nnz/(m*n)<=.2):return original.build(a,b,c,x,y,gpu_inverse)
    attempts=[]
    selections=[np.linspace(0,n-1,m,dtype=np.int64),np.floor((np.arange(m)+.5)*n/m).astype(np.int64)]
    for index,columns in enumerate(selections):
        with patch.object(original.sparse.csgraph,'maximum_bipartite_matching',lambda *args,**kwargs:columns):
            certificate,detail=original.build(a,b,c,x,y,gpu_inverse)
        if certificate:
            bound=inverse_bound(a[:,columns].toarray(),certificate['inverse']);attempts.append(bound)
            if bound['accepted']:
                detail.update(column_selection='evenly_distributed_'+str(index),proposal_inverse_checks=attempts)
                return certificate,detail
        else:attempts.append(detail)
    certificate,detail=original.build(a,b,c,x,y,gpu_inverse)
    if certificate:
        bound=inverse_bound(a[:,certificate['columns']].toarray(),certificate['inverse']);attempts.append(bound)
        if bound['accepted']:
            detail.update(column_selection='structural_matching_fallback',proposal_inverse_checks=attempts)
            return certificate,detail
    return None,dict(reason='no_verified_sparse_wide_basis',attempts=attempts)
