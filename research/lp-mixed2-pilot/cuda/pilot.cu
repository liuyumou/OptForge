// Retained image functions remain source-exact; new diagnostic functions follow.
#include "../../lp-fp4-accel/cuda/accel.cu"

__device__ __forceinline__ unsigned long long pilot_timer() {
    unsigned long long value;
    asm volatile("mov.u64 %0, %%globaltimer;" : "=l"(value) :: "memory");
    return value;
}
extern "C" __global__ void mixed2_native_profile(GRID_ARGS, unsigned long long* timing, unsigned slot) {
    int t=threadIdx.x&31,warp=threadIdx.x/32,i=blockIdx.x*32+t,p=blocks*32;
    unsigned long long begin=0,matrix_begin=0,matrix_end=0;
    if(threadIdx.x==0)begin=pilot_timer();
    if(grid_accel::stopped(flags,blocks))return;
    __shared__ double partial[grid_accel::WARPS*32];
    bool tr=op==1;double dot=0;
    if(threadIdx.x==0)matrix_begin=pilot_timer();
    for(int j=warp;j<p;j+=grid_accel::WARPS)dot+=exact[(tr?p*p:0)+j*p+i]*raw[(tr?1:2)*p+j];
    partial[threadIdx.x]=dot;__syncthreads();if(warp)return;dot=0;
    for(int h=0;h<grid_accel::WARPS;h++)dot+=partial[h*32+t];
    if(threadIdx.x==0)matrix_end=pilot_timer();
    double value;
    if(tr){double old=raw[i];value=i<n?fmin(cb[2*p+i],fmax(cb[p+i],old+ldexp(dot-cb[i],-shift))):0;raw[i]=value;raw[2*p+i]=2*value-old;}
    else {double v=raw[p+i]-ldexp(dot,-shift);value=i<m?v-fmin(-ldexp(cb[3*p+i],-shift),fmax(-ldexp(cb[4*p+i],-shift),v)):0;raw[p+i]=value;}
    if(threadIdx.x==0)pending[(tr?0:blocks)+blockIdx.x]=0;
    __syncwarp();if(__any_sync(0xffffffff,!isfinite(value)))if(threadIdx.x==0)pending[(tr?0:blocks)+blockIdx.x]=1;
    if(threadIdx.x==0){unsigned at=(slot*blocks+blockIdx.x)*4;timing[at]=begin;timing[at+1]=matrix_begin;timing[at+2]=matrix_end;timing[at+3]=pilot_timer();}
}
// Product probe uses explicit FP64 FMA in both storage modes and the same tree.
#define PRODUCT_ARGS const double* a64,const float* a32,const double* error,const double* x,double* out,unsigned p,unsigned tr
extern "C" __global__ void mixed2_product64(PRODUCT_ARGS) {
    int t=threadIdx.x&31,w=threadIdx.x/32,i=blockIdx.x*32+t;
    __shared__ double partial[256];double dot=0;
    for(unsigned j=w;j<p;j+=8)dot=__fma_rn(a64[(tr?p*p:0)+j*p+i],x[j],dot);
    partial[threadIdx.x]=dot;__syncthreads();if(w)return;dot=0;
    for(int h=0;h<8;h++)dot+=partial[h*32+t];out[i]=dot;
}
extern "C" __global__ void mixed2_product32(PRODUCT_ARGS) {
    int t=threadIdx.x&31,w=threadIdx.x/32,i=blockIdx.x*32+t;
    __shared__ double partial[256];double dot=0;
    for(unsigned j=w;j<p;j+=8)dot=__fma_rn(double(a32[(tr?p*p:0)+j*p+i]),x[j],dot);
    partial[threadIdx.x]=dot;__syncthreads();if(w)return;dot=0;
    for(int h=0;h<8;h++)dot+=partial[h*32+t];out[i]=dot;
}
extern "C" __global__ void mixed2_product_guard(PRODUCT_ARGS) {
    int t=threadIdx.x&31,w=threadIdx.x/32,i=blockIdx.x*32+t;
    __shared__ double quant[256],magnitude[256];double q=0,s=0;
    for(unsigned j=w;j<p;j+=8){unsigned at=(tr?p*p:0)+j*p+i;double v=fabs(x[j]);q=__dadd_ru(q,__dmul_ru(error[at],v));s=__dadd_ru(s,__dmul_ru(fabs(double(a32[at])),v));}
    quant[threadIdx.x]=q;magnitude[threadIdx.x]=s;__syncthreads();if(w)return;q=0;s=0;
    for(int h=0;h<8;h++){q=__dadd_ru(q,quant[h*32+t]);s=__dadd_ru(s,magnitude[h*32+t]);}
    double ku=double(p+8)*0x1p-53;
    double gamma=__ddiv_ru(ku,__dsub_rd(1.,ku));
    out[i]=__dadd_ru(q,__dadd_ru(__dmul_ru(gamma,s),__dmul_ru(double(p+8),0x0.0000000000001p-1022)));
}
extern "C" __global__ void mixed2_timer_probe(unsigned long long* stamps) {
    if(threadIdx.x==0)for(int i=0;i<64;i++)stamps[i]=pilot_timer();
}
