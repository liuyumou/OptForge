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
template<int F,int K> __device__ void product(const unsigned* matrix,const int* me,const unsigned* vector,const int* ve,bool trans,Pair* out) {
    int t=threadIdx.x,g=t/4,q=t%4;
    for(int half=0;half<2;half++) {
        Pair acc0={0,0},acc1={0,0};
        for(int p=0;p<K;p++)for(int s=0;s<K;s++) {
            float d[4]={0,0,0,0};
            for(int slice=0;slice<(F==16?2:1);slice++) {
                unsigned a[4]={0,0,0,0},b[2]={0,0};
                constexpr int pack=F==16?2:4, bits=F==16?16:8;
                for(int reg=0;reg<4;reg++)for(int j=0;j<pack;j++) {
                    int r=16*half+g+(reg%2)*8;
                    int col=q*pack+j+(reg/2)*(4*pack)+slice*16;
                    unsigned code=get(matrix+p*(32*F),trans?col*32+r:r*32+col,F);
                    a[reg]|=code<<(bits*j);
                }
                for(int reg=0;reg<2;reg++)for(int j=0;j<pack;j++) {
                    int r=q*pack+j+reg*(4*pack)+slice*16;
                    // Exactly one useful column; every other column is zero.
                    unsigned code=g==0?get(vector+s*F,r,F):0;
                    b[reg]|=code<<(bits*j);
                }
                mma<F>(d,a,b);
            }
            int exponent=me[p]+ve[s];
            acc0=add(acc0,{ldexpf(d[0],exponent),0});
            acc1=add(acc1,{ldexpf(d[2],exponent),0});
        }
        if(q==0) {out[16*half+g]=acc0;out[16*half+g+8]=acc1;}
    }
    __syncwarp();
}
// Operation: 0 encode input, 1 A^T y, 2 primal+bar, 3 A bar, 4 dual,
// 5 fused window, 6 export, 7 injected refusal. Scratch is only local FP32 pairs.
template<int F,int K> __device__ void run(const unsigned* matrix,const int* me,const double* original,const double* cb,unsigned* state,int* ex,double* raw,Pair* tmp,unsigned* flags,unsigned n,unsigned op,unsigned count) {
    int t=threadIdx.x,b=blockIdx.x;
    __shared__ unsigned sc[3*K*F];__shared__ int se[3*K];
    __shared__ Pair dot[32];__shared__ unsigned status;
    state+=b*3*K*F;ex+=b*3*K;matrix+=b*K*32*F;me+=b*K;
    raw+=b*96;tmp+=b*32;cb+=b*64;flags+=b*2;
    for(int i=t;i<3*K*F;i+=32)sc[i]=state[i];
    for(int i=t;i<3*K;i+=32)se[i]=ex[i];
    if(t==0)status=flags[0];__syncwarp();
    if(op==7) {if(t==0)flags[0]=4;return;}
    if(status)return;
    if(op==0)for(int v=0;v<3;v++) {
        double x=t<int(n)?raw[v*32+t]:0;float h=float(x);
        encode<F,K>({h,float(x-double(h))},sc+v*K*F,se+v*K,&status);
    }
    if(op==1 || op==3) {
        int v=op==1?1:2;product<F,K>(matrix,me,sc+v*K*F,se+v*K,op==1,dot);tmp[t]=dot[t];
    }
    if(op==2 || op==4)dot[t]=tmp[t];
    __syncwarp();
    for(unsigned step=0;step<(op==5?count:1);step++) {
        if(op==5)product<F,K>(matrix,me,sc+K*F,se+K,true,dot);
        if(op==2 || op==5) {
            Pair old=unpack<F,K>(sc,se,t);
            Pair x=project(add(old,power(add(dot[t],{-float(cb[t]),0}),-4)));
            if(t>=int(n))x={0,0};
            Pair bar=add(power(x,1),neg(old));
            encode<F,K>(x,sc,se,&status);
            encode<F,K>(bar,sc+2*K*F,se+2*K,&status);
        }
        if(op==5)product<F,K>(matrix,me,sc+2*K*F,se+2*K,false,dot);
        if(op==4 || op==5) {
            Pair y=add(unpack<F,K>(sc+K*F,se+K,t),power(add({float(cb[32+t]),0},neg(dot[t])),-4));
            if(t>=int(n))y={0,0};
            encode<F,K>(y,sc+K*F,se+K,&status);
            if(t==0)flags[1]++;
        }
        __syncwarp();if(status)break;
    }
    if(op==6)for(int v=0;v<3;v++){Pair x=unpack<F,K>(sc+v*K*F,se+v*K,t);raw[v*32+t]=double(x.h)+double(x.l);}
    for(int i=t;i<3*K*F;i+=32)state[i]=sc[i];
    for(int i=t;i<3*K;i+=32)ex[i]=se[i];
    if(t==0)flags[0]=status;
}
__device__ void native(const double* a,const double* cb,double* raw,double* tmp,unsigned* flags,unsigned n,unsigned op,unsigned count) {
    int t=threadIdx.x,b=blockIdx.x;a+=b*1024;cb+=b*64;raw+=b*96;tmp+=b*32;flags+=b*2;
    __shared__ double state[96],dot[32];
    for(int v=0;v<3;v++)state[v*32+t]=raw[v*32+t];__syncwarp();
    if(op==7){if(t==0)flags[0]=4;return;}if(flags[0])return;
    if(op==1||op==3){double sum=0;for(int j=0;j<32;j++)sum+=a[op==1?j*32+t:t*32+j]*state[(op==1?32:64)+j];tmp[t]=sum;}
    if(op==2||op==4)dot[t]=tmp[t];__syncwarp();
    for(unsigned step=0;step<(op==5?count:1);step++) {
        if(op==5){double sum=0;for(int j=0;j<32;j++)sum+=a[j*32+t]*state[32+j];dot[t]=sum;__syncwarp();}
        if(op==2||op==5){double old=state[t];double x=t<int(n)?fmin(1.,fmax(-1.,old-(cb[t]-dot[t])/16.)):0;state[t]=x;state[64+t]=2*x-old;__syncwarp();}
        if(op==5){double sum=0;for(int j=0;j<32;j++)sum+=a[t*32+j]*state[64+j];dot[t]=sum;__syncwarp();}
        if(op==4||op==5){state[32+t]=t<int(n)?state[32+t]+(cb[32+t]-dot[t])/16.:0;if(t==0)flags[1]++;__syncwarp();}
    }
    for(int v=0;v<3;v++)raw[v*32+t]=state[v*32+t];
    if(__any_sync(0xffffffff,!isfinite(state[t])||!isfinite(state[32+t])||!isfinite(state[64+t])))if(t==0)flags[0]=1;
}
#define PARAM const unsigned* a,const int* ae,const double* orig,const double* cb,unsigned* s,int* se,double* raw,Pair* tmp,unsigned* flags,unsigned n,unsigned op,unsigned count
#define ENTRY(F,K) extern "C" __global__ void pilot_##F##_##K(PARAM) {run<F,K>(a,ae,orig,cb,s,se,raw,tmp,flags,n,op,count);}
ENTRY(4,2) ENTRY(4,4) ENTRY(4,8) ENTRY(8,4) ENTRY(16,2)
extern "C" __global__ void pilot_64_1(PARAM) {native(orig,cb,raw,reinterpret_cast<double*>(tmp),flags,n,op,count);}
