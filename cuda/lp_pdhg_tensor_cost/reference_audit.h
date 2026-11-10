// ADR-0044: native FP64 host-oracle order, without contraction/reassociation.
// These products are audit work and never count as useful Tensor work.
__device__ double tc_finite(double x, unsigned *bad) {
  if (!isfinite(x)) atomicOr(bad, 1u);
  return x;
}
__device__ double tc_mul(double a, double b, unsigned *bad) {
  double x = __dmul_rn(a, b);
  if (!isfinite(x) || (a != 0.0 && b != 0.0 && x == 0.0)) atomicOr(bad, 1u);
  return x;
}
extern "C" __global__ void tc_ref_product(
    const double *values, const unsigned *indices, const unsigned *offsets,
    const double *input, double *output, unsigned *bad, unsigned lines,
    unsigned offset_start, unsigned value_start) {
  unsigned j = blockIdx.x * blockDim.x + threadIdx.x;
  if (j >= lines) return;
  double sum = 0.0;
  for (unsigned k = offsets[offset_start+j]; k < offsets[offset_start+j+1]; ++k) {
    double term = tc_mul(values[value_start+k], input[indices[value_start+k]], bad);
    sum = tc_finite(__dadd_rn(sum, term), bad);
  }
  output[j] = sum;
}
extern "C" __global__ void tc_ref_primal(
    const double *before, const double *aty, const double *objective,
    const double *lower, const double *upper, const double *anchor,
    double *next, double *bar, unsigned *bad, unsigned n,
    double step, double toward, double back) {
  unsigned j = blockIdx.x * blockDim.x + threadIdx.x;
  if (j >= n) return;
  double diff = tc_finite(__dsub_rn(objective[j], aty[j]), bad);
  double raw = tc_finite(__dsub_rn(before[j],tc_mul(step,diff,bad)),bad);
  double projected = fmin(fmax(raw,lower[j]),upper[j]);
  bar[j] = tc_finite(__dsub_rn(tc_mul(2.0,projected,bad),before[j]),bad);
  next[j] = tc_finite(__dadd_rn(tc_mul(toward,projected,bad),tc_mul(back,anchor[j],bad)),bad);
}
extern "C" __global__ void tc_ref_dual(
    const double *before, double *ax, const double *lower, const double *upper,
    const double *anchor, unsigned *bad, unsigned m,
    double step, double toward, double back) {
  unsigned j = blockIdx.x * blockDim.x + threadIdx.x;
  if (j >= m) return;
  double raw = tc_finite(__dsub_rn(before[j],tc_mul(step,ax[j],bad)),bad);
  double scaled = fmin(fmax(tc_finite(__ddiv_rn(raw,step),bad),-upper[j]),-lower[j]);
  double projected = tc_finite(__dsub_rn(raw,tc_mul(step,scaled,bad)),bad);
  ax[j] = tc_finite(__dadd_rn(tc_mul(toward,projected,bad),tc_mul(back,anchor[j],bad)),bad);
}
