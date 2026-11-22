// Exact-tree control diagnostics and original-order feasibility. CPU acceptance
// retains the original dual/gap proof and independently rechecks feasibility.
#include "prepare.cu"

__device__ double displacement(double a,double b) {
    const double d=fabs(__dsub_rn(a,b));
    return isfinite(d)?d:INFINITY;
}
extern "C" __global__ void control_primal(const double* x,double* product,
    const double* cost,const double* lower,const double* upper,double* extra,
    uint32_t n,double step) {
    const uint64_t j=uint64_t(blockIdx.x)*blockDim.x+threadIdx.x;
    if(j>=n) return;
    const double gradient=__dsub_rn(cost[j],product[j]);
    const double moved=__dsub_rn(x[j],__dmul_rn(step,gradient));
    const double next=fmin(fmax(moved,lower[j]),upper[j]);
    extra[j]=__dsub_rn(__dmul_rn(2.,next),x[j]);
    product[j]=displacement(next,x[j]);
}
extern "C" __global__ void control_dual(const double* y,double* product,
    const double* lower,const double* upper,uint32_t m,double step) {
    const uint64_t i=uint64_t(blockIdx.x)*blockDim.x+threadIdx.x;
    if(i>=m) return;
    const double raw=__dsub_rn(y[i],__dmul_rn(step,product[i]));
    const double projected=fmin(fmax(__ddiv_rn(raw,step),-upper[i]),-lower[i]);
    product[i]=displacement(__dsub_rn(raw,__dmul_rn(step,projected)),y[i]);
}
extern "C" __global__ void control_max(const double* input,double* output,uint32_t n) {
    __shared__ double values[256];
    double v=0.;
    for(uint32_t j=threadIdx.x;j<1024;j+=256) {
        const uint64_t k=uint64_t(blockIdx.x)*1024+j;
        if(k<n) v=fmax(v,input[k]);
    }
    values[threadIdx.x]=v;
    __syncthreads();
    for(uint32_t stride=128;stride>0;stride/=2) {
        if(threadIdx.x<stride) values[threadIdx.x]=fmax(values[threadIdx.x],values[threadIdx.x+stride]);
        __syncthreads();
    }
    if(threadIdx.x==0) output[blockIdx.x]=values[0];
}
extern "C" __global__ void control_movement(const double* x,const double* anchor,
    double* terms,uint32_t n) {
    const uint64_t i=uint64_t(blockIdx.x)*blockDim.x+threadIdx.x;
    if(i<n) {const double d=__dsub_rn(x[i],anchor[i]);terms[i]=__dmul_rn(d,d);}
}
extern "C" __global__ void control_scalar(const double* input,double* output,
    uint32_t index,uint32_t present) {
    output[index]=present?input[0]:0.;
}
__device__ double original_finite(double v,uint32_t* flags) {
    if(!isfinite(v)) atomicExch(flags,1u);
    return v==0.?0.:v;
}
__device__ bool original_bound(double b,bool lower,double v,double magnitude,
    double tolerance,uint32_t* flags) {
    if(!isfinite(b)) return true;
    double violation=0.;
    if(lower && v<b) violation=original_finite(__dsub_rn(b,v),flags);
    else if(!lower && v>b) violation=original_finite(__dsub_rn(v,b),flags);
    const double relative=original_finite(__dmul_rn(tolerance,fmax(fmax(fabs(v),fabs(b)),magnitude)),flags);
    return violation<=original_finite(__dadd_rn(tolerance,relative),flags);
}
extern "C" __global__ void control_feasible_columns(const double* x,
    const double* lower,const double* upper,uint32_t n,double tolerance,uint32_t* flags) {
    const uint64_t j=uint64_t(blockIdx.x)*blockDim.x+threadIdx.x;
    if(j>=n) return;
    const double v=original_finite(x[j],flags);
    const bool lo=original_bound(lower[j],true,v,fabs(v),tolerance,flags);
    const bool hi=original_bound(upper[j],false,v,fabs(v),tolerance,flags);
    if(!lo || !hi) atomicExch(flags+1,1u);
}
extern "C" __global__ void control_feasible_rows(const uint32_t* offsets,
    const uint32_t* indices,const double* values,const double* x,
    const double* lower,const double* upper,uint32_t m,double tolerance,uint32_t* flags) {
    const uint64_t i=uint64_t(blockIdx.x)*blockDim.x+threadIdx.x;
    if(i>=m) return;
    double sum=0.,magnitude=0.;
    for(uint32_t k=offsets[i];k<offsets[i+1];++k) {
        const double v=original_finite(x[indices[k]],flags);
        const double p=original_finite(__dmul_rn(values[k],v),flags);
        sum=original_finite(__dadd_rn(sum,p),flags);
        magnitude=original_finite(__dadd_rn(magnitude,fabs(p)),flags);
    }
    const bool lo=original_bound(lower[i],true,sum,magnitude,tolerance,flags);
    const bool hi=original_bound(upper[i],false,sum,magnitude,tolerance,flags);
    if(!lo || !hi) atomicExch(flags+1,1u);
}
