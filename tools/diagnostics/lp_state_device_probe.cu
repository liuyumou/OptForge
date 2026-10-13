// Isolated ADR-0036 primitive experiments. Never a solver/runtime code object.
#include "lp_state_compact_probe.cu"

template<int P> __device__ __forceinline__ void state_benchmark(
    const Value* input,Value* output,U* guards,W* cycles,U count,U iterations) {
    U index=blockIdx.x*blockDim.x+threadIdx.x;if(index>=count)return;
    Value value=input[3*index],multiplier=input[3*index+1],addend=input[3*index+2];
    U guard=0;
    W started=clock64();
    // Runtime inputs and iteration count; every iteration depends on its result.
    // Host validation checks odd/even chains and independent exact endpoints.
    for(U k=0;k<iterations;k++)value=compact_fma<P>(value,multiplier,addend,guard);
    W elapsed=clock64()-started;
    guards[index]=guard;cycles[index]=elapsed;if(!guard)output[index]=value;
}
extern "C" __global__ void state_bench_p48(const Value* a,Value* b,U* g,W* c,U n,U k){state_benchmark<48>(a,b,g,c,n,k);}
extern "C" __global__ void state_bench_p64(const Value* a,Value* b,U* g,W* c,U n,U k){state_benchmark<64>(a,b,g,c,n,k);}
