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
