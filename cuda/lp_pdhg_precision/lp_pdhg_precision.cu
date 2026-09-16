// ADR-0019: deterministic sparse mixed precision. No atomics or contraction.
#include <math.h>
__device__ double load(const void* p,unsigned int i,unsigned int f32) {
 return f32 ? (double)((const float*)p)[i] : ((const double*)p)[i];
}
__device__ double checked(double v,unsigned int &g) { if(!isfinite(v))g|=1;return v; }
__device__ float narrow(double v,unsigned int &g) {
 float f=__double2float_rn(v); if(!isfinite(v)||!isfinite(f))g|=1;
 if(v!=0.0 && f==0.0f)g|=2; return f;
}
__device__ double multiply(double a,double b,unsigned int fp32,unsigned int &g){
 double p;
 if(fp32){float af=narrow(a,g),bf=narrow(b,g);p=(double)__fmul_rn(af,bf);}
 else p=__dmul_rn(a,b);
 if(!isfinite(p))g|=1;if(a!=0.0&&b!=0.0&&p==0.0)g|=4;return p;
}
extern "C" __global__ void precision_spmv(const void* values,const unsigned int* indices,
 const unsigned int* offsets,const void* x,double* out,unsigned int* guards,
 unsigned int lines,unsigned int matrix32,unsigned int vector32,unsigned int product32,unsigned int acc32){
 unsigned int line=(blockIdx.x*blockDim.x+threadIdx.x)/32,lane=threadIdx.x&31;
 if(line>=lines)return;
 double sum=0.0;unsigned int g=0;
 for(unsigned int i=offsets[line]+lane;i<offsets[line+1];i+=32){
  double p=multiply(load(values,i,matrix32),load(x,indices[i],vector32),product32,g);
  sum=acc32?(double)__fadd_rn((float)sum,(float)p):__dadd_rn(sum,p);checked(sum,g);
 }
 for(unsigned int k=16;k;k>>=1){
  double other=__shfl_down_sync(0xffffffffu,sum,k);
  unsigned int og=__shfl_down_sync(0xffffffffu,g,k);
  if(lane<k){sum=acc32?(double)__fadd_rn((float)sum,(float)other):__dadd_rn(sum,other);g|=og;checked(sum,g);}
 }
 if(lane==0){out[line]=sum;guards[line]|=g;}
}
extern "C" __global__ void precision_primal(const void* x,const double* aty,const double* c,
 const double* lower,const double* upper,double* next,double* bar,unsigned int* guards,
 double step,unsigned int n,unsigned int state32){
 unsigned int j=blockIdx.x*blockDim.x+threadIdx.x;if(j>=n)return;unsigned int g=0;
 double old=load(x,j,state32);double diff=checked(c[j]-aty[j],g);
 double raw=checked(old-multiply(step,diff,0,g),g);
 double clamped=raw;if(clamped<lower[j])clamped=lower[j];if(clamped>upper[j])clamped=upper[j];
 next[j]=clamped;bar[j]=checked(multiply(2.0,clamped,0,g)-old,g);guards[j]|=g;
}
extern "C" __global__ void precision_dual(const void* y,const double* ax,const double* lower,
 const double* upper,double* next,unsigned int* guards,double step,unsigned int n,unsigned int state32){
 unsigned int j=blockIdx.x*blockDim.x+threadIdx.x;if(j>=n)return;unsigned int g=0;
 double raw=checked(load(y,j,state32)-multiply(step,ax[j],0,g),g);
 double scaled=checked(raw/step,g);if(scaled< -upper[j])scaled= -upper[j];if(scaled> -lower[j])scaled= -lower[j];
 next[j]=checked(raw-multiply(step,scaled,0,g),g);guards[j]|=g;
}
extern "C" __global__ void precision_store(void* out,const double* next,const void* anchor,
 unsigned int* guards,double toward,double back,unsigned int n,unsigned int state32){
 unsigned int j=blockIdx.x*blockDim.x+threadIdx.x;if(j>=n)return;unsigned int g=0;
 double v=checked(multiply(toward,next[j],0,g)+multiply(back,load(anchor,j,state32),0,g),g);
 if(state32)((float*)out)[j]=narrow(v,g);else ((double*)out)[j]=v;guards[j]|=g;
}
