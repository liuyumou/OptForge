// CPU-prepared v3 shared-state synchronization correction; v2 stays frozen.
// CPU-prepared v2 packing correction; v1 frozen failure remains exact.
// SPEC-0027. One warp owns one independent 32x32 block and a SINGLE RHS.
// Nibble storage is expanded only into local MMA byte fragments.
#include <cuda_fp16.h>
#include <cuda_fp8.h>
#include <stdint.h>
#include <math.h>
struct Pair { float h, l; };
__device__ Pair add(Pair a, Pair b) {
    float s=__fadd_rn(a.h,b.h), v=__fsub_rn(s,a.h);
    float e=__fadd_rn(__fsub_rn(a.h,__fsub_rn(s,v)),__fsub_rn(b.h,v));
    e=__fadd_rn(e,__fadd_rn(a.l,b.l));
    float h=__fadd_rn(s,e); return {h,__fadd_rn(__fsub_rn(s,h),e)};
}
__device__ Pair neg(Pair x) { return {-x.h,-x.l}; }
__device__ Pair power(Pair x,int e) { return {ldexpf(x.h,e),ldexpf(x.l,e)}; }
__device__ bool less(Pair a,Pair b) { Pair d=add(a,neg(b));return d.h<0 || (d.h==0 && d.l<0); }
__device__ Pair project(Pair x) { if(less(x,{-1,0}))return {-1,0}; if(less({1,0},x))return {1,0};return x; }
__device__ unsigned get(const unsigned* data,int index,int bits) {
    return (data[index/(32/bits)] >> ((index%(32/bits))*bits)) & ((1u<<bits)-1);
}
template<int F> __device__ float decode(unsigned c) {
    if constexpr(F==4) { const float v[8]={0,.5,1,1.5,2,3,4,6};return (c&8)?-v[c&7]:v[c&7]; }
    if constexpr(F==8) { __nv_fp8_e4m3 x;x.__x=c;return float(x); }
    if constexpr(F==16) { return __half2float(__ushort_as_half(c)); }
    return 0;
}
template<int F> __device__ unsigned quant(Pair a) {
    if constexpr(F==4) {
        bool negative=less(a,{0,0});if(negative)a=neg(a);
        const float mid[7]={.25,.75,1.25,1.75,2.5,3.5,5};unsigned code=0;
        for(int j=0;j<7;j++) {
            Pair d=add(a,{-mid[j],0});
            if(d.h>0 || (d.h==0 && (d.l>0 || (d.l==0 && (j&1)))))code=j+1;
        }
        return code | ((negative && code)?8:0);
    }
    if constexpr(F==8) { __nv_fp8_e4m3 v(__fadd_rn(a.h,a.l));return v.__x==128?0:v.__x; }
    if constexpr(F==16) { unsigned v=__half_as_ushort(__float2half_rn(__fadd_rn(a.h,a.l)));return v==32768?0:v; }
    return 0;
}
template<int F,int K> __device__ Pair unpack(const unsigned* c,const int* e,int i) {
    Pair v={0,0};for(int k=0;k<K;k++)v=add(v,{ldexpf(decode<F>(get(c+k*F,i,F)),e[k]),0});return v;
}
template<int F,int K> __device__ void encode(Pair value,unsigned* c,int* ex,unsigned* status) {
    const int t=threadIdx.x, width=32/F;
    __syncwarp(); // Finish all reads of aliased shared state before re-encoding.
    for(int k=0;k<K;k++) {
        float largest=__fadd_rn(fabsf(value.h),fabsf(value.l));
        for(int d=16;d;d>>=1)largest=fmaxf(largest,__shfl_xor_sync(0xffffffff,largest,d));
        if(__any_sync(0xffffffff,!isfinite(value.h)||!isfinite(value.l))) { if(t==0)*status=1;return; }
        int e=-48;const float maximum=F==4?6.f:(F==8?448.f:65504.f);
        while(e<48 && largest>ldexpf(maximum,e))++e;
        if(largest>ldexpf(maximum,e)) {if(t==0)*status=2;return;}
        unsigned code=quant<F>(power(value,-e));
        unsigned word=0;
        // All lanes execute every shuffle, including lanes that do not store.
        for(int j=0;j<width;j++)word|=__shfl_sync(0xffffffff,code,(t%F)*width+j)<<(j*F);
        if(t<F)c[k*F+t]=word;
        if(t==0)ex[k]=e;
        value=add(value,{-ldexpf(decode<F>(code),e),0});
        __syncwarp();
    }
}
#define MMA_ARGS(d,a,b) "=f"(d[0]),"=f"(d[1]),"=f"(d[2]),"=f"(d[3]) : "r"(a[0]),"r"(a[1]),"r"(a[2]),"r"(a[3]),"r"(b[0]),"r"(b[1]),"f"(d[0]),"f"(d[1]),"f"(d[2]),"f"(d[3])
template<int F> __device__ void mma(float* d,unsigned* a,unsigned* b) {
    if constexpr(F==4)asm volatile("mma.sync.aligned.m16n8k32.row.col.kind::f8f6f4.f32.e2m1.e2m1.f32 {%0,%1,%2,%3},{%4,%5,%6,%7},{%8,%9},{%10,%11,%12,%13};" : MMA_ARGS(d,a,b));
    if constexpr(F==8)asm volatile("mma.sync.aligned.m16n8k32.row.col.kind::f8f6f4.f32.e4m3.e4m3.f32 {%0,%1,%2,%3},{%4,%5,%6,%7},{%8,%9},{%10,%11,%12,%13};" : MMA_ARGS(d,a,b));
    if constexpr(F==16)asm volatile("mma.sync.aligned.m16n8k16.row.col.f32.f16.f16.f32 {%0,%1,%2,%3},{%4,%5,%6,%7},{%8,%9},{%10,%11,%12,%13};" : MMA_ARGS(d,a,b));
}
