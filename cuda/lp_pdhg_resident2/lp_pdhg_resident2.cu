// SPEC-0024 separate image; exact legacy control exports remain available.
#include "../lp_pdhg_tuned/lp_pdhg_tuned.cu"

// Each warp owns one coordinate/flag. Flags survive all updates in a window.
// A refusal keeps finite prior state; the host rejects the complete window.
extern "C" __global__ void resident2_primal(const double *v, const unsigned int *idx,
 const unsigned int *off, const double *y, double *x, const double *c,
 const double *lo, const double *hi, const double *anchor, double *bar,
 const double *coeff, unsigned int k, double step, unsigned int n,
 unsigned long long *flags) {
  unsigned int line = (blockIdx.x * blockDim.x + threadIdx.x) / 32;
  if (line >= n) return;
  // The flag is warp-uniform and was written by this warp's owner on this stream.
  if (flags[line]) return;
  double total = warp_dot(v, idx, off, y, line);
  if ((threadIdx.x & 31) == 0) {
    double old = x[line], gradient = c[line] - total;
    double raw = old - step * gradient, clamped = raw;
    if (clamped < lo[line]) clamped = lo[line];
    if (clamped > hi[line]) clamped = hi[line];
    double extrapolated = 2.0 * clamped - old;
    double next = coeff[2*k] * clamped + coeff[2*k+1] * anchor[line];
    if (!isfinite(total) || !isfinite(gradient) || !isfinite(raw) ||
        !isfinite(extrapolated) || !isfinite(next)) {
      flags[line] = 1; bar[line] = old; return;
    }
    bar[line] = extrapolated; x[line] = next;
  }
}
extern "C" __global__ void resident2_dual(const double *v, const unsigned int *idx,
 const unsigned int *off, const double *bar, double *y, const double *lo,
 const double *hi, const double *anchor, const double *coeff, unsigned int k,
 double step, unsigned int n, unsigned long long *flags) {
  unsigned int line = (blockIdx.x * blockDim.x + threadIdx.x) / 32;
  if (line >= n) return;
  if (flags[line]) return;
  double total = warp_dot(v, idx, off, bar, line);
  if ((threadIdx.x & 31) == 0) {
    double raw = y[line] - step * total, clamped = raw / step;
    double low = -hi[line], high = -lo[line];
    if (clamped < low) clamped = low;
    if (clamped > high) clamped = high;
    double next = raw - step * clamped;
    double value = coeff[2*k] * next + coeff[2*k+1] * anchor[line];
    if (!isfinite(total) || !isfinite(raw) || !isfinite(raw / step) ||
        !isfinite(next) || !isfinite(value)) { flags[line] = 1; return; }
    y[line] = value;
  }
}
