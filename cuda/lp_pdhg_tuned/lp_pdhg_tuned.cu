// ADR-0017 experimental FP64 execution. Legacy source/object stay unchanged.
// Including the original exports provides the exact separate-kernel control.
#include "../lp_pdhg/lp_pdhg.cu"

// Every live warp has all 32 lanes, even for empty/short lines. No active-mask
// arithmetic or atomic accumulation. Separate intrinsics prevent contraction.
__device__ double warp_dot(const double *values, const unsigned int *indices,
                          const unsigned int *offsets, const double *x,
                          unsigned int line) {
  unsigned int lane = threadIdx.x & 31;
  double sum = 0.0;
  for (unsigned int i = offsets[line] + lane; i < offsets[line + 1]; i += 32) {
    sum = __dadd_rn(sum, __dmul_rn(values[i], x[indices[i]]));
  }
  for (unsigned int offset = 16; offset; offset >>= 1) {
    double other = __shfl_down_sync(0xffffffffu, sum, offset);
    if (lane < offset) sum = __dadd_rn(sum, other);
  }
  return sum;
}

__device__ double legacy_dot(const double *values, const unsigned int *indices,
                            const unsigned int *offsets, const double *x,
                            unsigned int line, unsigned int max_line) {
  extern __shared__ double tuned_shared[];
  unsigned int start = offsets[line], count = offsets[line + 1] - start;
  for (unsigned int i = threadIdx.x; i < count; i += blockDim.x)
    tuned_shared[i] = values[start + i] * x[indices[start + i]];
  __syncthreads();
  return reduce_fixed(tuned_shared, count, tuned_shared + max_line, tuned_shared + max_line + SEGMENT);
}

extern "C" __global__ void spmv_warp32(const double *values,
    const unsigned int *indices, const unsigned int *offsets, const double *x,
    double *out, unsigned int lines, unsigned int /*max_line*/) {
  unsigned int line = (blockIdx.x * blockDim.x + threadIdx.x) / 32;
  if (line >= lines) return; // whole-warp exit, never a partial participation mask
  double total = warp_dot(values, indices, offsets, x, line);
  if ((threadIdx.x & 31) == 0) out[line] = total;
}

template<bool Warp>
__device__ void fused_primal(const double *values, const unsigned int *indices,
    const unsigned int *offsets, const double *y, double *x,
    const double *objective, const double *lower, const double *upper,
    const double *anchor, double *extrapolated, double step, double toward,
    double back, unsigned int count, unsigned int max_line) {
  unsigned int line = Warp ? (blockIdx.x * blockDim.x + threadIdx.x) / 32 : blockIdx.x;
  if (line >= count) return;
  double total = Warp ? warp_dot(values, indices, offsets, y, line)
                      : legacy_dot(values, indices, offsets, y, line, max_line);
  if (Warp ? ((threadIdx.x & 31) == 0) : (threadIdx.x == 0)) {
    double old = x[line];
    double gradient = objective[line] - total;
    double clamped = old - step * gradient;
    if (clamped < lower[line]) clamped = lower[line];
    if (clamped > upper[line]) clamped = upper[line];
    extrapolated[line] = 2.0 * clamped - old;
    x[line] = toward * clamped + back * anchor[line];
  }
}

template<bool Warp>
__device__ void fused_dual(const double *values, const unsigned int *indices,
    const unsigned int *offsets, const double *extrapolated, double *y,
    const double *lower, const double *upper, const double *anchor,
    double step, double toward, double back, unsigned int count, unsigned int max_line) {
  unsigned int line = Warp ? (blockIdx.x * blockDim.x + threadIdx.x) / 32 : blockIdx.x;
  if (line >= count) return;
  double total = Warp ? warp_dot(values, indices, offsets, extrapolated, line)
                      : legacy_dot(values, indices, offsets, extrapolated, line, max_line);
  if (Warp ? ((threadIdx.x & 31) == 0) : (threadIdx.x == 0)) {
    double raw = y[line] - step * total;
    double clamped = raw / step;
    double low = -upper[line], high = -lower[line];
    if (clamped < low) clamped = low;
    if (clamped > high) clamped = high;
    double next = raw - step * clamped;
    y[line] = toward * next + back * anchor[line];
  }
}

#define PRIMAL(name, warp) \
extern "C" __global__ void name(const double *v, const unsigned int *i, \
 const unsigned int *o, const double *y, double *x, const double *c, \
 const double *l, const double *u, const double *a, double *bar, \
 double s, double t, double b, unsigned int n, unsigned int m) { \
 fused_primal<warp>(v,i,o,y,x,c,l,u,a,bar,s,t,b,n,m); }
#define DUAL(name, warp) \
extern "C" __global__ void name(const double *v, const unsigned int *i, \
 const unsigned int *o, const double *bar, double *y, const double *l, \
 const double *u, const double *a, double s, double t, double b, \
 unsigned int n, unsigned int m) { fused_dual<warp>(v,i,o,bar,y,l,u,a,s,t,b,n,m); }
PRIMAL(fused_primal_legacy, false)
PRIMAL(fused_primal_warp32, true)
DUAL(fused_dual_legacy, false)
DUAL(fused_dual_warp32, true)
