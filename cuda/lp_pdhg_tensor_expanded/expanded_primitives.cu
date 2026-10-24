// Production building blocks for expanded within-window state. No host launcher.
// The build adapter extracts unchanged helpers without historical probe kernels.
#include "expanded_compact_helpers.h"
#include "expanded_fast.h"
#include "expanded_storage.h"

// Generic normalized primitive: add, subtract, multiply, or explicit fused FMA.
// Each thread writes private working storage; guard publication is separate from
// the host's atomic two-vector window commit and reference adoption.
extern "C" __global__ void xe_scalar(
    ExpandedConst a,ExpandedConst b,ExpandedConst c,ExpandedOut out,
    U *guards,U *fast_paths,U count,U operation) {
    U i=blockIdx.x*blockDim.x+threadIdx.x;
    if(i>=count)return;
    U guard=0,fast=0;
    Value av=expanded_load(a,i,guard),bv=expanded_load(b,i,guard),cv={0,0,0};
    bool product_nonzero=av.m&&bv.m;
    if(operation==3)cv=expanded_load(c,i,guard);
    else if(operation<=1) {
        cv=bv;if(operation==1)cv.sign^=1u;
        bv={1ull<<63,-63,0};
    } else if(operation==2)cv.sign=av.sign^bv.sign;
    else guard|=8u;
    Value result={0,0,0};
    if(!guard)result=expanded_fma(av,bv,cv,guard,fast);
    if(operation==2&&product_nonzero&&!result.m)guard|=4u;
    guards[i]=guard;fast_paths[i]=fast;
    if(!guard)expanded_store(out,i,result);
}

// Integer fallback is the SAME Expansion64 arithmetic, not native promotion.
extern "C" __global__ void xe_integer_fma(
    ExpandedConst a,ExpandedConst b,ExpandedConst c,ExpandedOut out,U *guards,U count) {
    U i=blockIdx.x*blockDim.x+threadIdx.x;if(i>=count)return;
    U guard=0;
    Value av=expanded_load(a,i,guard),bv=expanded_load(b,i,guard),cv=expanded_load(c,i,guard);
    Value result={0,0,0};
    if(!guard)result=compact_fma<64>(av,bv,cv,guard);
    guards[i]=guard;if(!guard)expanded_store(out,i,result);
}

// bounds_flags bit 0: finite lower; bit 1: finite upper. Infinities are symbolic.
extern "C" __global__ void xe_project(
    ExpandedConst x,ExpandedConst lower,ExpandedConst upper,const U *bounds_flags,
    ExpandedOut out,U *guards,U count) {
    U i=blockIdx.x*blockDim.x+threadIdx.x;if(i>=count)return;
    U guard=0,flags=bounds_flags[i];
    Value v=expanded_load(x,i,guard),lo={0,0,0},hi={0,0,0};
    if(flags&~3u)guard|=8u;
    if(flags&1u)lo=expanded_load(lower,i,guard);
    if(flags&2u)hi=expanded_load(upper,i,guard);
    if(flags==3u&&expanded_less(hi,lo))guard|=8u;
    if((flags&1u)&&expanded_less(v,lo))v=lo;
    if((flags&2u)&&expanded_less(hi,v))v=hi;
    guards[i]=guard;if(!guard)expanded_store(out,i,v);
}

extern "C" __global__ void xe_encode64(
    const W *input,ExpandedOut out,U *guards,U count) {
    U i=blockIdx.x*blockDim.x+threadIdx.x;if(i>=count)return;
    U guard=0;Value v=expanded_from_fp64(input[i],guard);
    guards[i]=guard;if(!guard)expanded_store(out,i,v);
}

// Output is a private staging buffer. Both vector guards must pass before the
// exact arrays can be bound to reference kernels or become externally visible.
extern "C" __global__ void xe_decode64(
    ExpandedConst input,W *staging,U *guards,U count) {
    U i=blockIdx.x*blockDim.x+threadIdx.x;if(i>=count)return;
    U guard=0;Value v=expanded_load(input,i,guard);
    W bits=guard?0:expanded_to_fp64(v,guard);
    guards[i]=guard;if(!guard)staging[i]=bits;
}
