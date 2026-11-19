// Exact-order FP64 proposal preparation. Original-model certificates stay on CPU.
#include <cuda_runtime.h>
#include <stdint.h>
#include <math.h>

template<int R, int Mode>
__device__ double line_tree(uint32_t begin, uint32_t end, uint32_t major,
    const uint32_t* indices, const double* values, const double* row_scale,
    const double* column_scale, const double* input, uint32_t transpose,
    uint32_t* flags) {
    const uint32_t lane=threadIdx.x&31, count=end-begin;
    double v[R];
    #pragma unroll
    for(int j=0;j<R;++j) {
        const uint32_t k=begin+lane+32*j;
        double term=0.;
        if(k<end) {
            if constexpr(Mode==2) term=__dmul_rn(values[k],input[indices[k]]);
            else {
                const uint32_t r=transpose?indices[k]:major;
                const uint32_t c=transpose?major:indices[k];
                term=fabs(__dmul_rn(__dmul_rn(row_scale[r],values[k]),column_scale[c]));
            }
            if(!isfinite(term)) atomicExch(flags,1u);
        }
        // Omitted upper levels of the original 1024-leaf tree add +0 once.
        if constexpr(Mode!=0) if(count<=512) term=__dadd_rn(term,0.);
        v[j]=term;
    }
    #pragma unroll
    for(int stride=R/2;stride>0;stride/=2) {
        #pragma unroll
        for(int j=0;j<stride;++j) {
            if constexpr(Mode==0) v[j]=fmax(v[j],v[j+stride]);
            else v[j]=__dadd_rn(v[j],v[j+stride]);
        }
    }
    uint32_t p=1;
    while(p<count && p<32) p*=2;
    double result=v[0];
    for(uint32_t stride=p/2;stride>0;stride/=2) {
        const double other=__shfl_down_sync(0xffffffffu,result,stride);
        if(lane<stride) {
            if constexpr(Mode==0) result=fmax(result,other);
            else result=__dadd_rn(result,other);
        }
    }
    return result;
}

template<int Mode>
__device__ void lines(const uint32_t* offsets, const uint32_t* indices,
    const double* values, const double* row_scale, const double* column_scale,
    const double* input, double* output, uint32_t n, uint32_t transpose,
    uint32_t* flags) {
    // The flattened launch can exceed 2^32 threads for a wide billion-NNZ LP.
    const uint64_t major=uint64_t(blockIdx.x)*(blockDim.x/32)+threadIdx.x/32;
    if(major>=n || (Mode==2 && !flags[1])) return;
    const uint32_t begin=offsets[major],end=offsets[major+1],count=end-begin;
    double result;
    #define TREE(R) line_tree<R,Mode>(begin,end,uint32_t(major),indices,values,row_scale,column_scale,input,transpose,flags)
    if(count<=32) result=TREE(1);
    else if(count<=64) result=TREE(2);
    else if(count<=128) result=TREE(4);
    else if(count<=256) result=TREE(8);
    else if(count<=512) result=TREE(16);
    else result=TREE(32);
    #undef TREE
    if((threadIdx.x&31)==0) output[major]=result;
}

#define LINE_KERNEL(NAME,MODE) \
extern "C" __global__ void NAME(const uint32_t* o,const uint32_t* i,const double* a, \
 const double* r,const double* c,const double* x,double* y,uint32_t n,uint32_t t,uint32_t* f) \
 { lines<MODE>(o,i,a,r,c,x,y,n,t,f); }
LINE_KERNEL(prep_max,0)
LINE_KERNEL(prep_sum,1)
LINE_KERNEL(prep_product,2)

extern "C" __global__ void prep_fill(double* a,uint32_t n,double value) {
    const uint64_t i=uint64_t(blockIdx.x)*blockDim.x+threadIdx.x;
    if(i<n) a[i]=value;
}

extern "C" __global__ void prep_update(double* r,double* c,const double* rm,
    const double* cm,uint32_t m,uint32_t n,uint32_t* flags) {
    const uint64_t i=uint64_t(blockIdx.x)*blockDim.x+threadIdx.x;
    if(i<m && rm[i]>0.) {
        r[i]=__ddiv_rn(r[i],__dsqrt_rn(rm[i]));
        if(!isfinite(r[i]) || r[i]<=0.) atomicExch(flags,1u);
    }
    if(i<n && cm[i]>0.) {
        c[i]=__ddiv_rn(c[i],__dsqrt_rn(cm[i]));
        if(!isfinite(c[i]) || c[i]<=0.) atomicExch(flags,1u);
    }
}

extern "C" __global__ void prep_scale(const uint32_t* offsets,const uint32_t* indices,
    double* values,const double* r,const double* c,uint32_t n,uint32_t transpose,uint32_t* flags) {
    const uint64_t major=uint64_t(blockIdx.x)*(blockDim.x/32)+threadIdx.x/32;
    if(major>=n) return;
    for(uint32_t k=offsets[major]+(threadIdx.x&31);k<offsets[major+1];k+=32) {
        const uint32_t row=transpose?indices[k]:uint32_t(major);
        const uint32_t col=transpose?uint32_t(major):indices[k];
        const double v=__dmul_rn(__dmul_rn(r[row],values[k]),c[col]);
        if(!isfinite(v)) atomicExch(flags,1u);
        values[k]=v;
    }
}

extern "C" __global__ void prep_reduce(const double* input,double* output,
    uint32_t n,uint32_t square,uint32_t* flags) {
    if(!flags[1]) return;
    __shared__ double values[1024];
    #pragma unroll
    for(uint32_t j=threadIdx.x;j<1024;j+=256) {
        const uint64_t i=uint64_t(blockIdx.x)*1024+j;
        double v=i<n?input[i]:0.;
        if(square) v=__dmul_rn(v,v);
        if(!isfinite(v)) atomicExch(flags,1u);
        values[j]=v;
    }
    __syncthreads();
    for(uint32_t stride=512;stride>0;stride/=2) {
        for(uint32_t j=threadIdx.x;j<stride;j+=256) values[j]=__dadd_rn(values[j],values[j+stride]);
        __syncthreads();
    }
    if(threadIdx.x==0) output[blockIdx.x]=values[0];
}

extern "C" __global__ void prep_norm(const double* sum,double* state,uint32_t* flags) {
    if(!flags[1]) return;
    const double magnitude=__dsqrt_rn(sum[0]);
    if(!isfinite(magnitude)) { atomicExch(flags,1u); flags[1]=0; return; }
    state[0]=magnitude;
    if(magnitude<=0.) { state[1]=0.;state[2]=1.;flags[1]=0;return; }
    state[1]=__dsqrt_rn(magnitude);
    state[2]=__ddiv_rn(0.9,state[1]);
    if(!isfinite(state[2]) || state[2]<=0.) atomicExch(flags,1u);
}

extern "C" __global__ void prep_normalize(const double* input,double* output,
    uint32_t n,const double* state,const uint32_t* flags) {
    if(!flags[1]) return;
    const uint64_t i=uint64_t(blockIdx.x)*blockDim.x+threadIdx.x;
    if(i<n) output[i]=__ddiv_rn(input[i],state[0]);
}
