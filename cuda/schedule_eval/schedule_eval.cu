// Batched flow-shop evaluation for compute capability 12.0, under SPEC-0010.
//
// Two kernels, both pure INT32. That is not incidental. This compute capability
// runs FP64 at one sixty-fourth of FP32 and issues integer and floating-point
// instructions on one shared pipeline, so a max-plus recurrence in `unsigned int`
// runs at the full lane rate and is the best-matched primitive the hardware has.
// It also makes agreement with the CPU recurrence an exact identity rather than a
// tolerance, which is SPEC-0010 requirement 14.
//
// Arithmetic width is `unsigned int` throughout and the host refuses dispatch when
// an instance's own makespan bound exceeds it (requirement 13), so nothing here can
// overflow. That check belongs on the host because it is a property of the
// instance, and a kernel that checked it would be checking after the fact.
//
// Two capability-12.0 limits shape the code. A thread block may address at most
// 99 KB of shared memory, which is why the head and tail tables are 32-bit: at 500
// jobs and 20 machines they are 80 KB, and 64-bit tables would be 160 KB and would
// not fit. And thread block clusters are accepted by the assembler here while
// `cluster.sync` degenerates to a no-op, so nothing below uses them; that is a
// silent-failure mode rather than a missing feature, which is why it is stated.

#define MAX_MACHINES 20

// Threads per block for `insertion_neighborhood`. Fixed rather than caller-supplied
// because the reduction arrays below are sized by it, and a mismatch between the two
// is the kind of defect that shows up as a wrong answer rather than a crash.
#define NEIGHBORHOOD_BLOCK 256

extern "C" {

// Makespan of each permutation in a batch. One thread per permutation.
//
// The machine row lives in registers: `MAX_MACHINES` is a compile-time bound and
// both machine loops are fully unrolled, so every index is a constant and the array
// never reaches local memory. ptxas reports 31 registers and zero spill, inside the
// 42 that 48 resident warps allow on this capability, so occupancy is limited by
// neither registers nor shared memory. That number is checked rather than assumed:
// `nvcc -Xptxas -v` prints it, and a change that spilled the row would show up
// there as a stack frame.
//
// `times` is machine-major, `times[m * jobs + job]`, matching the instance document
// and therefore needing no transpose on the host.
__global__ void makespan_batch(const unsigned int *__restrict__ times,
                               const unsigned short *__restrict__ sequences,
                               unsigned int *__restrict__ makespans,
                               unsigned int jobs, unsigned int machines,
                               unsigned int offset, unsigned int count) {
  extern __shared__ unsigned int shared_times[];
  // Stage the processing times once per block. Each thread reads a different job,
  // so the global accesses would otherwise be scattered across the matrix.
  for (unsigned int i = threadIdx.x; i < jobs * machines; i += blockDim.x) {
    shared_times[i] = times[i];
  }
  __syncthreads();

  // `offset` and `count` name one chunk of a larger batch. The host launches in
  // bounded chunks and checks for cancellation between them, so a cancelled run
  // waits for one chunk rather than for the whole batch; the kernel sees only which
  // chunk it is.
  unsigned int index = offset + blockIdx.x * blockDim.x + threadIdx.x;
  if (index >= offset + count) {
    return;
  }
  const unsigned short *sequence = sequences + (size_t)index * jobs;

  unsigned int row[MAX_MACHINES];
#pragma unroll
  for (int m = 0; m < MAX_MACHINES; ++m) {
    row[m] = 0u;
  }

  unsigned int last = 0u;
  for (unsigned int k = 0; k < jobs; ++k) {
    unsigned int job = (unsigned int)sequence[k];
    unsigned int previous = 0u;
#pragma unroll
    for (int m = 0; m < MAX_MACHINES; ++m) {
      if ((unsigned int)m < machines) {
        // C[k][m] = max(C[k-1][m], C[k][m-1]) + p[job][m], the same recurrence the
        // host module defines and the only definition of cost in the project.
        unsigned int start = previous > row[m] ? previous : row[m];
        unsigned int finish = start + shared_times[(unsigned int)m * jobs + job];
        row[m] = finish;
        previous = finish;
      }
    }
    last = previous;
  }
  makespans[index] = last;
}

// Best insertion move for one removed job, one block per job.
//
// The block removes `job` from the sequence, builds head and tail tables over what
// remains, and evaluates every reinsertion position. Head and tail are the same
// arrays the host heuristics use, so the two compute the same quantity by the same
// identity rather than by two definitions that happen to agree.
//
// The two tables are built by two threads running concurrently rather than by the
// whole block. The recurrence is sequential along positions, so parallelising it
// across machines needs a max-plus scan per step; that is the obvious next
// optimisation and is deliberately not done here, because the position evaluation
// that follows is already the parallel part and correctness comes first.
__launch_bounds__(NEIGHBORHOOD_BLOCK) __global__ void
insertion_neighborhood(const unsigned int *__restrict__ times,
                       const unsigned short *__restrict__ sequence,
                       unsigned int *__restrict__ best_cost,
                       unsigned int *__restrict__ best_position, unsigned int jobs,
                       unsigned int machines, unsigned int offset) {
  // `head` then `tail`, each (jobs) * machines entries: the remaining sequence has
  // jobs - 1 entries, so there are jobs prefixes and jobs suffixes.
  extern __shared__ unsigned int tables[];
  unsigned int *head = tables;
  unsigned int *tail = tables + jobs * machines;

  // One chunk of the job range, for the same reason as above.
  const unsigned int removed = offset + blockIdx.x;
  const unsigned int length = jobs - 1u;

  // The sequence without `removed`, addressed by index rather than materialised.
  // Every thread needs it, and jobs can be 500, so recomputing the skip is cheaper
  // than another shared array.
  __shared__ unsigned int removed_at;
  if (threadIdx.x == 0) {
    removed_at = 0u;
    for (unsigned int i = 0; i < jobs; ++i) {
      if ((unsigned int)sequence[i] == removed) {
        removed_at = i;
        break;
      }
    }
  }
  __syncthreads();

#define WITHOUT(i) ((unsigned int)sequence[(i) < removed_at ? (i) : (i) + 1u])

  if (threadIdx.x == 0) {
    // Forward: head[k] is the completion row after the first k remaining jobs.
    for (unsigned int m = 0; m < machines; ++m) {
      head[m] = 0u;
    }
    for (unsigned int k = 0; k < length; ++k) {
      unsigned int job = WITHOUT(k);
      unsigned int previous = 0u;
      for (unsigned int m = 0; m < machines; ++m) {
        unsigned int above = head[k * machines + m];
        unsigned int start = previous > above ? previous : above;
        unsigned int finish = start + times[m * jobs + job];
        head[(k + 1u) * machines + m] = finish;
        previous = finish;
      }
    }
  } else if (threadIdx.x == 1) {
    // Backward: tail[k] is the time from the start of the job at position k on each
    // machine to the end of the remaining sequence. tail[length] is zero, which is
    // what makes appending at the end fall out of the same formula.
    for (unsigned int m = 0; m < machines; ++m) {
      tail[length * machines + m] = 0u;
    }
    for (unsigned int k = length; k-- > 0;) {
      unsigned int job = WITHOUT(k);
      unsigned int next = 0u;
      for (unsigned int m = machines; m-- > 0;) {
        unsigned int after = tail[(k + 1u) * machines + m];
        unsigned int start = next > after ? next : after;
        unsigned int finish = start + times[m * jobs + job];
        tail[k * machines + m] = finish;
        next = finish;
      }
    }
  }
  __syncthreads();

#undef WITHOUT

  // Every reinsertion position, strided across the block.
  unsigned int local_cost = 0xffffffffu;
  unsigned int local_position = 0xffffffffu;
  for (unsigned int position = threadIdx.x; position <= length; position += blockDim.x) {
    unsigned int previous = 0u;
    unsigned int cost = 0u;
    for (unsigned int m = 0; m < machines; ++m) {
      unsigned int above = head[position * machines + m];
      unsigned int start = previous > above ? previous : above;
      unsigned int finish = start + times[m * jobs + removed];
      previous = finish;
      // Completing the inserted job on this machine at `finish` delays everything
      // the tail still has to do on it, and the schedule cannot end before the
      // worst of those.
      unsigned int through = finish + tail[position * machines + m];
      cost = cost > through ? cost : through;
    }
    // Strictly-less keeps the earliest position on a tie, matching the host rule
    // that SPEC-0008 requirement 17 fixes.
    if (cost < local_cost) {
      local_cost = cost;
      local_position = position;
    }
  }

  // Block reduction, ordered so the result does not depend on which thread won.
  __shared__ unsigned int reduce_cost[NEIGHBORHOOD_BLOCK];
  __shared__ unsigned int reduce_position[NEIGHBORHOOD_BLOCK];
  reduce_cost[threadIdx.x] = local_cost;
  reduce_position[threadIdx.x] = local_position;
  __syncthreads();
  for (unsigned int stride = NEIGHBORHOOD_BLOCK / 2u; stride > 0u; stride >>= 1) {
    if (threadIdx.x < stride) {
      unsigned int other = threadIdx.x + stride;
      // Lower cost wins; equal cost keeps the lower position. This is a total
      // order, so the reduction tree's shape cannot change the answer.
      if (reduce_cost[other] < reduce_cost[threadIdx.x] ||
          (reduce_cost[other] == reduce_cost[threadIdx.x] &&
           reduce_position[other] < reduce_position[threadIdx.x])) {
        reduce_cost[threadIdx.x] = reduce_cost[other];
        reduce_position[threadIdx.x] = reduce_position[other];
      }
    }
    __syncthreads();
  }

  if (threadIdx.x == 0) {
    best_cost[removed] = reduce_cost[0];
    best_position[removed] = reduce_position[0];
  }
}

}
