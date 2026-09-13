// First-order linear programming kernels for compute capability 12.0, under
// SPEC-0011 and ADR-0010.
//
// Everything here is `double`, which requirement 5 fixes and which is worth
// defending because this hardware runs FP64 at one sixty-fourth of FP32. The
// defence is that a sparse matrix-vector product moves roughly twelve bytes per
// nonzero for two floating-point operations, an arithmetic intensity near 0.17
// operations per byte, against a peak-FP64-to-peak-bandwidth ratio near 0.91 here.
// The product is therefore bandwidth-bound with roughly fivefold headroom before
// the FP64 rate could bind. Factorization and dense interior-point steps have the
// opposite intensity, which is why SPEC-0011 excludes them rather than preferring
// something else.
//
// # Determinism is engineered here, not inherited
//
// The integer evaluator in SPEC-0010 gets bitwise reproducibility for free, because
// integer max and add are associative and commutative. Nothing here is. Floating
// point addition is not associative, so the value of every sum depends on the order
// it was accumulated in, and requirement 8 makes reproducibility a contract.
//
// So the reduction order is fixed by construction and mirrors
// `optimizer-lp/src/reduce.rs` exactly: segments of SEGMENT elements at fixed
// offsets, each padded with +0.0 and reduced by a fixed halving tree, then the
// partials reduced by the same rule. SEGMENT is asserted against the Rust constant
// by a device test rather than trusted to stay in step.
//
// Forbidden in this file, and checked for by tools/check.sh:
//
//   - atomicAdd on a double, which makes the result depend on scheduling;
//   - warp shuffle reductions whose participation depends on the active mask;
//   - cooperative-groups grid reductions;
//   - any warp-synchronous reduction without __syncthreads.
//
// Each of those is faster and each would silently cost the contract. None of them
// is used, and a launch shape change must not be able to alter a single bit.
//
// # What these kernels are not allowed to decide
//
// Nothing. They compute iterates. Every claim attached to those iterates --
// objective, feasibility, bound, termination -- is produced on the host from the
// original model, and the bound in particular comes from a certification that does
// not assume anything here was computed correctly. A wrong kernel produces a
// recorded refusal or a weak bound, never a wrong answer.

// Elements per reduction segment. Must equal optimizer_lp::reduce::SEGMENT; the
// device suite asserts it rather than assuming it.
#define SEGMENT 1024

// Threads per block. Equal to SEGMENT / 4 so each thread stages four elements into
// the segment buffer, which keeps the buffer at one segment regardless of how many
// threads the launch actually resides.
#define BLOCK 256

extern "C" {

// Reduce one padded segment held in shared memory by the fixed halving tree.
//
// `buffer` must hold SEGMENT doubles with the unused tail already +0.0. The tree is
// written out rather than delegated to a library precisely so the order is visible
// and cannot change under a compiler or occupancy decision.
__device__ double reduce_segment(double *buffer) {
  for (unsigned int stride = SEGMENT / 2; stride >= 1; stride >>= 1) {
    for (unsigned int i = threadIdx.x; i < stride; i += blockDim.x) {
      buffer[i] += buffer[i + stride];
    }
    __syncthreads();
    if (stride == 1) {
      break;
    }
  }
  return buffer[0];
}

// Reduce `count` values from `source` in the project's fixed order.
//
// Two levels, which is the same recursion `tree_sum` performs on the host: each
// SEGMENT-sized piece is reduced by the padded halving tree, and the resulting
// partials are then reduced by that same tree rather than accumulated left to
// right. Accumulating them would be a different order and would break bitwise
// agreement on any line with more than SEGMENT entries -- a defect invisible on
// small models and guaranteed on large ones.
//
// Two levels bound a line at SEGMENT * SEGMENT entries. The host refuses a model
// whose widest line exceeds that, before any allocation, so this kernel is never
// launched on one.
__device__ double reduce_fixed(const double *source, unsigned int count,
                               double *buffer, double *partials) {
  unsigned int segments = (count + SEGMENT - 1) / SEGMENT;
  if (segments == 0) {
    segments = 1;
  }
  for (unsigned int segment = 0; segment < segments; ++segment) {
    unsigned int base = segment * SEGMENT;
    unsigned int chunk = (count > base) ? (count - base) : 0;
    if (chunk > SEGMENT) {
      chunk = SEGMENT;
    }
    for (unsigned int i = threadIdx.x; i < SEGMENT; i += blockDim.x) {
      buffer[i] = (i < chunk) ? source[base + i] : 0.0;
    }
    __syncthreads();
    double value = reduce_segment(buffer);
    if (threadIdx.x == 0) {
      partials[segment] = value;
    }
    __syncthreads();
  }
  if (segments == 1) {
    return partials[0];
  }
  for (unsigned int i = threadIdx.x; i < SEGMENT; i += blockDim.x) {
    buffer[i] = (i < segments) ? partials[i] : 0.0;
  }
  __syncthreads();
  return reduce_segment(buffer);
}

// y = A x, one row per block, read from the row-major form.
//
// One block owns one row, so the row's output element is accumulated by exactly one
// reduction and no atomic is needed. That is requirement 6 expressed in the launch
// shape rather than only in the storage.
__global__ void spmv_row(const double *__restrict__ values,
                         const unsigned int *__restrict__ indices,
                         const unsigned int *__restrict__ offsets,
                         const double *__restrict__ x,
                         double *__restrict__ out, unsigned int rows,
                         unsigned int max_line) {
  // Shared layout: the line's products, the reduction buffer, then the
  // per-segment partials. The host sizes the allocation from the widest line.
  extern __shared__ double shared[];
  double *products = shared;
  double *buffer = products + max_line;
  double *partials = buffer + SEGMENT;
  (void)products;
  (void)buffer;
  (void)partials;

  for (unsigned int row = blockIdx.x; row < rows; row += gridDim.x) {
    unsigned int start = offsets[row];
    unsigned int end = offsets[row + 1];
    unsigned int count = end - start;

#ifdef AI_OPTIMIZER_ATOMIC_REDUCTION
    // A deliberately nondeterministic reduction, built only into a separate code
    // object that no production path loads. It exists so the bitwise assertion can
    // be shown to be able to fail: without a build that breaks it, "the result is
    // bitwise reproducible" would be consistent with an implementation whose order
    // merely happens to be stable. SPEC-0011's acceptance section asks for exactly
    // this substitution.
    if (threadIdx.x == 0) {
      out[row] = 0.0;
    }
    __syncthreads();
    for (unsigned int i = threadIdx.x; i < count; i += blockDim.x) {
      atomicAdd(&out[row], values[start + i] * x[indices[start + i]]);
    }
    __syncthreads();
#else
    for (unsigned int i = threadIdx.x; i < count; i += blockDim.x) {
      products[i] = values[start + i] * x[indices[start + i]];
    }
    __syncthreads();
    double total = reduce_fixed(products, count, buffer, partials);
    if (threadIdx.x == 0) {
      out[row] = total;
    }
    __syncthreads();
#endif
  }
}

// x = A^T y, one column per block, read from the column-major form.
//
// The transposed product reads its own orientation rather than striding the
// row-major one, which is why the program carries both: neither direction needs an
// atomic, and the pair is what requirement 6 asks for.
__global__ void spmv_column(const double *__restrict__ values,
                            const unsigned int *__restrict__ indices,
                            const unsigned int *__restrict__ offsets,
                            const double *__restrict__ y,
                            double *__restrict__ out, unsigned int columns,
                            unsigned int max_line) {
  // Shared layout: the line's products, the reduction buffer, then the
  // per-segment partials. The host sizes the allocation from the widest line.
  extern __shared__ double shared[];
  double *products = shared;
  double *buffer = products + max_line;
  double *partials = buffer + SEGMENT;

  for (unsigned int column = blockIdx.x; column < columns; column += gridDim.x) {
    unsigned int start = offsets[column];
    unsigned int end = offsets[column + 1];
    unsigned int count = end - start;

    for (unsigned int i = threadIdx.x; i < count; i += blockDim.x) {
      products[i] = values[start + i] * y[indices[start + i]];
    }
    __syncthreads();
    double total = reduce_fixed(products, count, buffer, partials);
    if (threadIdx.x == 0) {
      out[column] = total;
    }
    __syncthreads();
  }
}

// The primal half of one step, elementwise.
//
//   x+ = clamp(x - tau * (c - A^T y), lower, upper)
//   extrapolated = 2 x+ - x
//
// The gradient is `c - A^T y` because this project takes the saddle function
// c'x - y'Ax + h(y), which makes the reduced cost `c - A^T y` -- the ordinary
// linear-programming convention and the one the host's certification recomputes
// from the original model. The opposite convention negates every multiplier, which
// leaves certification valid (it is valid for any vector) while making every bound
// uselessly weak. That is a much harder defect to see than a wrong answer.
__global__ void primal_step(const double *__restrict__ x,
                            const double *__restrict__ transposed,
                            const double *__restrict__ objective,
                            const double *__restrict__ lower,
                            const double *__restrict__ upper,
                            double *__restrict__ next_x,
                            double *__restrict__ extrapolated, double primal_step,
                            unsigned int columns) {
  unsigned int index = blockIdx.x * blockDim.x + threadIdx.x;
  if (index >= columns) {
    return;
  }
  double gradient = objective[index] - transposed[index];
  double moved = x[index] - primal_step * gradient;
  double clamped = moved;
  if (clamped < lower[index]) {
    clamped = lower[index];
  }
  if (clamped > upper[index]) {
    clamped = upper[index];
  }
  next_x[index] = clamped;
  extrapolated[index] = 2.0 * clamped - x[index];
}

// The dual half of one step, elementwise.
//
//   raw = y - s * (A x_bar)
//   y+  = raw - s * clamp(raw / s, -row_upper, -row_lower)
//
// That is the proximal operator of the support function of the negated row range,
// by Moreau decomposition. One expression covers equality, ranged, one-sided and
// free rows with no branch on row shape, and it lands the multiplier inside the
// same cone the host's certification projects onto -- so the two agree by
// construction rather than by coincidence.
__global__ void dual_step(const double *__restrict__ y,
                          const double *__restrict__ activity,
                          const double *__restrict__ row_lower,
                          const double *__restrict__ row_upper,
                          double *__restrict__ next_y, double dual_step,
                          unsigned int rows) {
  unsigned int index = blockIdx.x * blockDim.x + threadIdx.x;
  if (index >= rows) {
    return;
  }
  double raw = y[index] - dual_step * activity[index];
  double scaled = raw / dual_step;
  double low = -row_upper[index];
  double high = -row_lower[index];
  double clamped = scaled;
  if (clamped < low) {
    clamped = low;
  }
  if (clamped > high) {
    clamped = high;
  }
  next_y[index] = raw - dual_step * clamped;
}

// The Halpern pull, elementwise, on either vector.
//
//   value = toward * stepped + back * anchor
//
// Both coefficients are pure functions of an integer and are computed on the host,
// so both engines derive the same numbers rather than one sending them to the
// other. They arrive as `double` kernel arguments.
__global__ void halpern(const double *__restrict__ stepped,
                        const double *__restrict__ anchor,
                        double *__restrict__ out, double toward, double back,
                        unsigned int count) {
  unsigned int index = blockIdx.x * blockDim.x + threadIdx.x;
  if (index >= count) {
    return;
  }
  out[index] = toward * stepped[index] + back * anchor[index];
}


}  // extern "C"
