// ADR-0021 isolated code object. Existing source and provisioned objects are immutable.
#include "../lp_pdhg_precision/lp_pdhg_precision.cu"
struct Parts2 { float part[2]; int exponent; };
struct Parts3 { float part[3]; int exponent; };
__device__ Parts3 split_operand(double x, unsigned int &g) {
 Parts3 v; int e=0; checked(x,g); double m=frexp(x,&e);
 v.part[0]=__double2float_rn(m); double r=m-(double)v.part[0];
 v.part[1]=__double2float_rn(r); v.part[2]=__double2float_rn(r-(double)v.part[1]); v.exponent=e;return v;
}
__device__ void compensated(double v,double &s,double &c) {
 double t=__dadd_rn(s,v), z=t-s;
 c=__dadd_rn(c,(s-(t-z))+(v-z));s=t;
}
template<int K> __device__ Parts3 read_parts(const void* v,unsigned int i) {
 Parts3 p;
 if constexpr(K==2) {const Parts2 &a=((const Parts2*)v)[i];p.part[0]=a.part[0];p.part[1]=a.part[1];p.part[2]=0;p.exponent=a.exponent;}
 else p=((const Parts3*)v)[i];return p;
}
template<int K,bool Cross> __device__ double component_multiply(Parts3 a,Parts3 b,unsigned int &g){
 double p;
 if constexpr(Cross) {
  double sum=0.0,error=0.0;
  #pragma unroll
  for(int i=0;i<K;i++) {
   #pragma unroll
   for(int j=0;j<K;j++) {
    float high=__fmul_rn(a.part[i],b.part[j]);
    float low=__fmaf_rn(a.part[i],b.part[j],-high);
    compensated((double)high,sum,error);compensated((double)low,sum,error);
   }
  }
  p=ldexp(sum+error,a.exponent+b.exponent);
 } else {
  double av=0,bv=0;
  #pragma unroll
  for(int i=0;i<K;i++){av=__dadd_rn(av,(double)a.part[i]);bv=__dadd_rn(bv,(double)b.part[i]);}
  av=checked(ldexp(av,a.exponent),g);bv=checked(ldexp(bv,b.exponent),g);
  p=__dmul_rn(av,bv);
 }
 checked(p,g);if(a.part[0]!=0.0f && b.part[0]!=0.0f && p==0.0)g|=4;return p;
}
template<bool Storage32,bool Factored,int K,bool Cross>
__device__ void sparse(const void* values,const unsigned int* indices,const unsigned int* offsets,
 const double* x,double* out,unsigned int* guards,unsigned int lines,const double* outer,const double* inner){
 unsigned int line=(blockIdx.x*blockDim.x+threadIdx.x)/32,lane=threadIdx.x&31;
 if(line>=lines)return;double sum=0;unsigned int g=0,tail=0;
 for(unsigned int i=offsets[line]+lane;i<offsets[line+1];i+=32){
  double v=checked(x[indices[i]],g), p;
  if constexpr(K>0) {
   Parts3 operand=split_operand(v,g);
   if constexpr(K==2) {if(isfinite(v))tail=max(tail,__double2uint_rn(fabs((double)operand.part[2])*9007199254740992.0));}
   p=component_multiply<K,Cross>(read_parts<K>(values,i),operand,g);
  }
  else {
   if constexpr(Factored) v=multiply(inner[indices[i]],v,0,g);
   double a=Storage32?(double)((const float*)values)[i]:((const double*)values)[i];
   p=multiply(a,v,0,g);
  }
  sum=checked(__dadd_rn(sum,p),g);
 }
 for(unsigned int k=16;k;k>>=1){
  double other=__shfl_down_sync(0xffffffffu,sum,k);
  unsigned int og=__shfl_down_sync(0xffffffffu,g,k);
  unsigned int ot=__shfl_down_sync(0xffffffffu,tail,k);
  if(lane<k){sum=checked(__dadd_rn(sum,other),g);g|=og;tail=max(tail,ot);}
 }
 if(lane==0){if constexpr(Factored)sum=multiply(outer[line],sum,0,g);out[line]=sum;unsigned int old=guards[line];guards[line]=(old&255u)|g|(max(old>>8,tail)<<8);}
}
#define ENTRY(Name,S,F,K,C) extern "C" __global__ void Name(const void* v,const unsigned int* i,const unsigned int* o,const double* x,double* y,unsigned int* g,unsigned int n,unsigned int,unsigned int,unsigned int,unsigned int,const double* outer,const double* inner){sparse<S,F,K,C>(v,i,o,x,y,g,n,outer,inner);}
ENTRY(research_native64,false,false,0,false)
ENTRY(research_native32,true,false,0,false)
ENTRY(research_factored64,false,true,0,false)
ENTRY(research_factored32,true,true,0,false)
ENTRY(research_components2_native,false,false,2,false)
ENTRY(research_components3_native,false,false,3,false)
ENTRY(research_components2_cross,false,false,2,true)
ENTRY(research_components3_cross,false,false,3,true)

// ---- ADR-0022: integer-pipe guards, fused schedules and FP32 pair arithmetic ----
// The vector-update helpers duplicate precision_primal/dual/store operation for
// operation so optimizer_lp::research::step remains the bitwise oracle. The
// existing nine entry points above are unchanged.
__device__ __forceinline__ unsigned int hi_bits(double v){return (unsigned int)__double2hiint(v)&0x7fffffffu;}
__device__ __forceinline__ unsigned int lo_bits(double v){return (unsigned int)__double2loint(v);}
__device__ __forceinline__ bool is_zero_bits(double v){return (hi_bits(v)|lo_bits(v))==0u;}
__device__ __forceinline__ bool nonfinite_bits(double v){return (hi_bits(v)&0x7ff00000u)==0x7ff00000u;}
__device__ __forceinline__ bool nonfinite_bits(float v){return (__float_as_uint(v)&0x7f800000u)==0x7f800000u;}
__device__ __forceinline__ bool is_zero_bits(float v){return (__float_as_uint(v)&0x7fffffffu)==0u;}

__device__ __forceinline__ void primal_update(unsigned int j,const double* x,double dot,const double* c,
 const double* lower,const double* upper,double* next,double* bar,unsigned int* guards,double step){
 unsigned int g=0;double old=x[j];double diff=checked(c[j]-dot,g);
 double raw=checked(old-multiply(step,diff,0,g),g);
 double clamped=raw;if(clamped<lower[j])clamped=lower[j];if(clamped>upper[j])clamped=upper[j];
 next[j]=clamped;bar[j]=checked(multiply(2.0,clamped,0,g)-old,g);guards[j]|=g;
}
__device__ __forceinline__ void dual_update(unsigned int j,const double* y,double dot,const double* lower,
 const double* upper,double* next,unsigned int* guards,double step){
 unsigned int g=0;double raw=checked(y[j]-multiply(step,dot,0,g),g);
 double scaled=checked(raw/step,g);if(scaled< -upper[j])scaled= -upper[j];if(scaled> -lower[j])scaled= -lower[j];
 next[j]=checked(raw-multiply(step,scaled,0,g),g);guards[j]|=g;
}
__device__ __forceinline__ double store_update(unsigned int j,double next,const double* anchor,
 unsigned int* guards,double toward,double back){
 unsigned int g=0;double v=checked(multiply(toward,next,0,g)+multiply(back,anchor[j],0,g),g);guards[j]|=g;return v;
}

// FP64 warp-per-line dot product with guards on the integer pipe: bit 4 for a
// nonzero product rounding to zero, bit 1 once per line for a nonfinite sum.
__device__ __forceinline__ double intguard_dot(const double* values,const unsigned int* indices,
 const unsigned int* offsets,const double* x,unsigned int line,unsigned int lane,unsigned int &g){
 double sum=0.0;unsigned int lost=0u;
 for(unsigned int i=offsets[line]+lane;i<offsets[line+1];i+=32){
  double a=values[i],b=x[indices[i]],p=__dmul_rn(a,b);
  lost|=(unsigned int)((!is_zero_bits(a))&(!is_zero_bits(b))&is_zero_bits(p));
  sum=__dadd_rn(sum,p);
 }
 for(unsigned int k=16;k;k>>=1){
  double other=__shfl_down_sync(0xffffffffu,sum,k);
  unsigned int ol=__shfl_down_sync(0xffffffffu,lost,k);
  if(lane<k){sum=__dadd_rn(sum,other);lost|=ol;}
 }
 g|=(lost<<2)|(unsigned int)nonfinite_bits(sum);
 return sum;
}
extern "C" __global__ void research_intguard64(const void* v,const unsigned int* i,const unsigned int* o,
 const double* x,double* y,unsigned int* g,unsigned int n,unsigned int,unsigned int,unsigned int,unsigned int,
 const double*,const double*){
 unsigned int line=(blockIdx.x*blockDim.x+threadIdx.x)/32,lane=threadIdx.x&31;
 if(line>=n)return;unsigned int gb=0;
 double sum=intguard_dot((const double*)v,i,o,x,line,lane,gb);
 if(lane==0){y[line]=sum;g[line]|=gb;}
}
// Fused schedules: one launch per orientation, eight lines per 256-thread block.
// Each warp computes its line's dot product; after a barrier one warp performs
// the eight vector updates with one lane per line. The FP64 pipe issues per warp,
// so this costs one warp-instruction per update instead of eight, which is what
// keeps the fused tail from dominating on wide instances.
extern "C" __global__ void research_fused_primal_64(const double* values,const unsigned int* indices,
 const unsigned int* offsets,const double* y,double* x,const double* c,const double* lower,const double* upper,
 const double* anchor,double* bar,double* next,unsigned int* gs,unsigned int* gu,unsigned int* gt,
 double step,double toward,double back,unsigned int n){
 __shared__ double dots[8];__shared__ unsigned int flags[8];
 unsigned int warp=threadIdx.x>>5,lane=threadIdx.x&31,line=blockIdx.x*8+warp;
 if(line<n){unsigned int gb=0;double dot=intguard_dot(values,indices,offsets,y,line,lane,gb);if(lane==0){dots[warp]=dot;flags[warp]=gb;}}
 __syncthreads();
 if(threadIdx.x<8){
  unsigned int j=blockIdx.x*8+threadIdx.x;
  if(j<n){
   gs[j]|=flags[threadIdx.x];
   primal_update(j,x,dots[threadIdx.x],c,lower,upper,next,bar,gu,step);
   x[j]=store_update(j,next[j],anchor,gt,toward,back);
  }
 }
}
extern "C" __global__ void research_fused_dual_64(const double* values,const unsigned int* indices,
 const unsigned int* offsets,const double* bar,double* y,const double* lower,const double* upper,
 const double* anchor,double* next,unsigned int* gs,unsigned int* gu,unsigned int* gt,
 double step,double toward,double back,unsigned int m){
 __shared__ double dots[8];__shared__ unsigned int flags[8];
 unsigned int warp=threadIdx.x>>5,lane=threadIdx.x&31,line=blockIdx.x*8+warp;
 if(line<m){unsigned int gb=0;double dot=intguard_dot(values,indices,offsets,bar,line,lane,gb);if(lane==0){dots[warp]=dot;flags[warp]=gb;}}
 __syncthreads();
 if(threadIdx.x<8){
  unsigned int j=blockIdx.x*8+threadIdx.x;
  if(j<m){
   gs[j]|=flags[threadIdx.x];
   dual_update(j,y,dots[threadIdx.x],lower,upper,next,gu,step);
   y[j]=store_update(j,next[j],anchor,gt,toward,back);
  }
 }
}
// Unevaluated FP32 pairs. Contraction is disabled for the whole object (-fmad=false),
// and every operation is an explicit intrinsic, so the CPU oracle's f32 arithmetic
// (which never contracts) reproduces these results bit for bit.
__device__ __forceinline__ float2 df_two_sum(float a,float b){
 float s=__fadd_rn(a,b);float bb=__fsub_rn(s,a);
 return make_float2(s,__fadd_rn(__fsub_rn(a,__fsub_rn(s,bb)),__fsub_rn(b,bb)));
}
__device__ __forceinline__ float2 df_quick_two_sum(float a,float b){
 float s=__fadd_rn(a,b);return make_float2(s,__fsub_rn(b,__fsub_rn(s,a)));
}
__device__ __forceinline__ float2 df_add(float2 a,float2 b){
 float2 s=df_two_sum(a.x,b.x);float2 t=df_two_sum(a.y,b.y);
 s=df_quick_two_sum(s.x,__fadd_rn(s.y,t.x));
 return df_quick_two_sum(s.x,__fadd_rn(s.y,t.y));
}
__device__ __forceinline__ float2 df_mul(float2 a,float2 b){
 float p=__fmul_rn(a.x,b.x);float e=__fmaf_rn(a.x,b.x,-p);
 e=__fmaf_rn(a.x,b.y,e);e=__fmaf_rn(a.y,b.x,e);
 return df_quick_two_sum(p,e);
}
__device__ __forceinline__ float2 df_split(double v,unsigned int &g){
 float hi=__double2float_rn(v);float lo=__double2float_rn(__dadd_rn(v,-(double)hi));
 if(!is_zero_bits(v)&&is_zero_bits(hi))g|=2u;
 return make_float2(hi,lo);
}
__device__ __forceinline__ double df_dot(const float2* values,const unsigned int* indices,
 const unsigned int* offsets,const float2* x,unsigned int line,unsigned int lane,unsigned int &g){
 float2 sum=make_float2(0.f,0.f);unsigned int flags=0u;
 for(unsigned int i=offsets[line]+lane;i<offsets[line+1];i+=32){
  float2 a=values[i],b=x[indices[i]],p=df_mul(a,b);
  flags|=(unsigned int)nonfinite_bits(p.x);
  flags|=((unsigned int)((!is_zero_bits(a.x))&(!is_zero_bits(b.x))&is_zero_bits(p.x)))<<2;
  sum=df_add(sum,p);
 }
 for(unsigned int k=16;k;k>>=1){
  float oh=__shfl_down_sync(0xffffffffu,sum.x,k);float ol=__shfl_down_sync(0xffffffffu,sum.y,k);
  unsigned int of=__shfl_down_sync(0xffffffffu,flags,k);
  if(lane<k){sum=df_add(sum,make_float2(oh,ol));flags|=of;}
 }
 flags|=(unsigned int)nonfinite_bits(sum.x);
 g|=flags;
 return __dadd_rn((double)sum.x,(double)sum.y);
}
extern "C" __global__ void research_fused_primal_df(const float2* values,const unsigned int* indices,
 const unsigned int* offsets,const float2* ydf,double* x,const double* c,const double* lower,const double* upper,
 const double* anchor,double* bar,float2* bardf,double* next,unsigned int* gs,unsigned int* gu,unsigned int* gt,
 double step,double toward,double back,unsigned int n){
 __shared__ double dots[8];__shared__ unsigned int flags[8];
 unsigned int warp=threadIdx.x>>5,lane=threadIdx.x&31,line=blockIdx.x*8+warp;
 if(line<n){unsigned int gb=0;double dot=df_dot(values,indices,offsets,ydf,line,lane,gb);if(lane==0){dots[warp]=dot;flags[warp]=gb;}}
 __syncthreads();
 if(threadIdx.x<8){
  unsigned int j=blockIdx.x*8+threadIdx.x;
  if(j<n){
   unsigned int gb=flags[threadIdx.x];
   primal_update(j,x,dots[threadIdx.x],c,lower,upper,next,bar,gu,step);
   bardf[j]=df_split(bar[j],gb);
   gs[j]|=gb;
   x[j]=store_update(j,next[j],anchor,gt,toward,back);
  }
 }
}
extern "C" __global__ void research_fused_dual_df(const float2* values,const unsigned int* indices,
 const unsigned int* offsets,const float2* bardf,double* y,float2* ydf,const double* lower,const double* upper,
 const double* anchor,double* next,unsigned int* gs,unsigned int* gu,unsigned int* gt,
 double step,double toward,double back,unsigned int m){
 __shared__ double dots[8];__shared__ unsigned int flags[8];
 unsigned int warp=threadIdx.x>>5,lane=threadIdx.x&31,line=blockIdx.x*8+warp;
 if(line<m){unsigned int gb=0;double dot=df_dot(values,indices,offsets,bardf,line,lane,gb);if(lane==0){dots[warp]=dot;flags[warp]=gb;}}
 __syncthreads();
 if(threadIdx.x<8){
  unsigned int j=blockIdx.x*8+threadIdx.x;
  if(j<m){
   unsigned int gb=flags[threadIdx.x];
   dual_update(j,y,dots[threadIdx.x],lower,upper,next,gu,step);
   double stored=store_update(j,next[j],anchor,gt,toward,back);
   y[j]=stored;ydf[j]=df_split(stored,gb);gs[j]|=gb;
  }
 }
}
