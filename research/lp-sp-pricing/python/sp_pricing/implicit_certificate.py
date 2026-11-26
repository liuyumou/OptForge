"""Deterministic inverse-error bounds for an implicit exact dual correction.

For active basis B, define delta exactly by B.T delta = c-A.T y0.
If ||I-R B.T||_inf < 1, Banach's lemma bounds delta without forming
rational inverse entries. Primal/support arithmetic is checked independently.
"""
import math
import numpy as np
from scipy import linalg

U = 2.0**-53
TINY = np.finfo(np.float64).tiny


def up(x): return math.nextafter(float(x), math.inf)
def down(x): return math.nextafter(float(x), -math.inf)


def gamma(k):
    value = up(k*U)
    if value >= .5:
        raise ValueError('roundoff bound dimension')
    return up(value/down(1-value))


def norm_upper(matrix):
    matrix = np.asarray(matrix, dtype=np.float64)
    if matrix.ndim != 2 or not np.isfinite(matrix).all():
        raise ValueError('finite matrix required')
    n = matrix.shape[1]
    value = float(np.max(np.sum(np.abs(matrix), axis=1), initial=0))
    return up(up(value/down(1-gamma(n)))+up(2*n*TINY))


def inverse_bound(basis_transpose, inverse):
    b = np.asarray(basis_transpose, dtype=np.float64); r = np.asarray(inverse, dtype=np.float64)
    if b.ndim != 2 or b.shape[0] != b.shape[1] or r.shape != b.shape or not np.isfinite(b).all() or not np.isfinite(r).all():
        return dict(accepted=False, reason='inverse_dimensions_or_nonfinite')
    n = len(b)
    if not 1 <= n <= 4096:
        return dict(accepted=False, reason='inverse_dimension_limit')
    # Independent CPU FP64 product. Standard gamma_(2n+1) encloses all
    # multiply/add roundoff, with a conservative gradual/flush-underflow term.
    product = linalg.blas.dgemm(alpha=1., a=r, b=b)
    diagonal = np.diag(product)
    if not np.isfinite(product).all() or np.any(diagonal < .5) or np.any(diagonal > 2.):
        return dict(accepted=False, reason='inverse_residual_diagonal')
    product[np.diag_indices(n)] -= 1.  # exact subtraction by Sterbenz's lemma
    rn, bn = norm_upper(r), norm_upper(b)
    rounding = up(up(gamma(2*n+1)*up(rn*bn))+up(4*n*n*TINY))
    error = up(norm_upper(product)+rounding)
    if not math.isfinite(error) or error >= 1:
        return dict(accepted=False, reason='inverse_bound_inconclusive', error_upper=error)
    bound = up(rn/down(1-error))
    return dict(accepted=True, inverse_norm_upper=bound, error_upper=error,
                preconditioner_norm_upper=rn, matrix_norm_upper=bn, product_roundoff_upper=rounding)


def correction_bound(inverse_norm, residual_upper):
    if residual_upper == 0:
        return 0.
    value = up(max(up(inverse_norm)*up(residual_upper), TINY))
    if not math.isfinite(value):
        raise ValueError('nonfinite correction bound')
    return value
