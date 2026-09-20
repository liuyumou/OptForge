// ADR-0022 diagnostic microbenchmark: per-launch cost of every research sparse
// kernel and of candidate formulations, on a CSR pattern exported by
// tools/lp_csr_export.py, optionally tiled block-diagonally. Includes the research
// source so the measured kernels are byte-for-byte the provisioned device functions.
// This is a diagnostic, never a solver, protocol or evidence path; run it only under
// the shared lease through tools/lp_research_budget.py so the time is charged.
#include "../lp_pdhg_research/lp_pdhg_research.cu"
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <vector>
#include <cmath>
#include <random>
#include <algorithm>

#define CK(x) do{cudaError_t e=(x); if(e!=cudaSuccess){fprintf(stderr,"%s:%d %s\n",__FILE__,__LINE__,cudaGetErrorString(e)); exit(1);} }while(0)

// ---- Reference: tuned FP64 warp-per-row (same arithmetic as spmv_warp32) ----
extern "C" __global__ void ref_fp64(const double* values,const unsigned* indices,const unsigned* offsets,const double* x,double* out,unsigned lines){
  unsigned line=(blockIdx.x*blockDim.x+threadIdx.x)/32, lane=threadIdx.x&31; if(line>=lines) return;
  double sum=0.0;
  for(unsigned i=offsets[line]+lane;i<offsets[line+1];i+=32) sum=__dadd_rn(sum,__dmul_rn(values[i],x[indices[i]]));
  for(unsigned k=16;k;k>>=1){double o=__shfl_down_sync(0xffffffffu,sum,k); if(lane<k) sum=__dadd_rn(sum,o);}
  if(lane==0) out[line]=sum;
}
// ---- Plain FP32 storage + FP32 x + FP32 FMA, FP32 accumulate (what cuOPT-class solvers would do) ----
extern "C" __global__ void plain_fp32(const float* values,const unsigned* indices,const unsigned* offsets,const float* x,float* out,unsigned lines){
  unsigned line=(blockIdx.x*blockDim.x+threadIdx.x)/32, lane=threadIdx.x&31; if(line>=lines) return;
  float sum=0.f;
  for(unsigned i=offsets[line]+lane;i<offsets[line+1];i+=32) sum=__fmaf_rn(values[i],x[indices[i]],sum);
  for(unsigned k=16;k;k>>=1){float o=__shfl_down_sync(0xffffffffu,sum,k); if(lane<k) sum+=o;}
  if(lane==0) out[line]=sum;
}
// ---- FP32 storage, FP64 gather/accumulate (GPUP-5 "storage-fp32" idea without guards) ----
extern "C" __global__ void store32_acc64(const float* values,const unsigned* indices,const unsigned* offsets,const double* x,double* out,unsigned lines){
  unsigned line=(blockIdx.x*blockDim.x+threadIdx.x)/32, lane=threadIdx.x&31; if(line>=lines) return;
  double sum=0.0;
  for(unsigned i=offsets[line]+lane;i<offsets[line+1];i+=32) sum=__dadd_rn(sum,__dmul_rn((double)values[i],x[indices[i]]));
  for(unsigned k=16;k;k>>=1){double o=__shfl_down_sync(0xffffffffu,sum,k); if(lane<k) sum=__dadd_rn(sum,o);}
  if(lane==0) out[line]=sum;
}
// ---- Candidate A: 3x3 FP32 cross products, but accumulate the 18 partials with plain DADD
//      (no per-term compensation). Same inputs as research_components3_cross. Vector split per nonzero.
extern "C" __global__ void cross3_plain_dadd(const Parts3* values,const unsigned* indices,const unsigned* offsets,const double* x,double* out,unsigned lines){
  unsigned line=(blockIdx.x*blockDim.x+threadIdx.x)/32, lane=threadIdx.x&31; if(line>=lines) return;
  double sum=0.0; unsigned g=0;
  for(unsigned i=offsets[line]+lane;i<offsets[line+1];i+=32){
    Parts3 a=values[i]; Parts3 b=split_operand(x[indices[i]],g);
    double s=0.0;
    #pragma unroll
    for(int p=0;p<3;p++){
      #pragma unroll
      for(int q=0;q<3;q++){ float hi=__fmul_rn(a.part[p],b.part[q]); float lo=__fmaf_rn(a.part[p],b.part[q],-hi); s=__dadd_rn(s,(double)hi); s=__dadd_rn(s,(double)lo);}
    }
    sum=__dadd_rn(sum,ldexp(s,a.exponent+b.exponent));
  }
  for(unsigned k=16;k;k>>=1){double o=__shfl_down_sync(0xffffffffu,sum,k); if(lane<k) sum=__dadd_rn(sum,o);}
  if(lane==0) out[line]=sum;
}
// ---- Candidate B: pre-split x once per SpMV (Parts3 vector), so the inner loop has no frexp/F2F on x.
//      Cross products in FP32, partials summed in FP64 with plain DADD. Only the 6 terms with
//      p+q<=2 are kept (magnitude of dropped terms <= 2^-72 relative): "triangular" truncation.
extern "C" __global__ void split_vector(const double* x,Parts3* out,unsigned n){
  unsigned j=blockIdx.x*blockDim.x+threadIdx.x; if(j>=n) return; unsigned g=0; out[j]=split_operand(x[j],g);
}
extern "C" __global__ void cross3_tri_presplit(const Parts3* values,const unsigned* indices,const unsigned* offsets,const Parts3* xs,double* out,unsigned lines){
  unsigned line=(blockIdx.x*blockDim.x+threadIdx.x)/32, lane=threadIdx.x&31; if(line>=lines) return;
  double sum=0.0;
  for(unsigned i=offsets[line]+lane;i<offsets[line+1];i+=32){
    Parts3 a=values[i]; Parts3 b=xs[indices[i]];
    double s=0.0;
    #pragma unroll
    for(int p=0;p<3;p++){
      #pragma unroll
      for(int q=0;q<3;q++){ if(p+q>2) continue; float hi=__fmul_rn(a.part[p],b.part[q]); float lo=__fmaf_rn(a.part[p],b.part[q],-hi); s=__dadd_rn(s,(double)hi); if(p+q<2) s=__dadd_rn(s,(double)lo);}
    }
    sum=__dadd_rn(sum,ldexp(s,a.exponent+b.exponent));
  }
  for(unsigned k=16;k;k>>=1){double o=__shfl_down_sync(0xffffffffu,sum,k); if(lane<k) sum=__dadd_rn(sum,o);}
  if(lane==0) out[line]=sum;
}
// ---- Candidate C: double-float ("float2") arithmetic, zero FP64-pipe instructions in the loop.
//      Value = hi + lo with hi,lo FP32 (48-bit significand). x pre-split into float2 (hi,lo).
//      Product via Dekker/FMA, accumulate with TwoSum in FP32. Exponent handled by a shared
//      per-matrix scale (assumes |scaled entries| in FP32 normal range, which Ruiz scaling gives).
struct DF { float hi, lo; };
__device__ __forceinline__ DF cand_two_sum(float a,float b){ float s=a+b; float bb=s-a; float e=(a-(s-bb))+(b-bb); return DF{s,e}; }
__device__ __forceinline__ DF cand_quick_two_sum(float a,float b){ float s=a+b; float e=b-(s-a); return DF{s,e}; }
__device__ __forceinline__ DF cand_add(DF a,DF b){ DF s=cand_two_sum(a.hi,b.hi); DF t=cand_two_sum(a.lo,b.lo); s.lo+=t.hi; s=cand_quick_two_sum(s.hi,s.lo); s.lo+=t.lo; return cand_quick_two_sum(s.hi,s.lo); }
__device__ __forceinline__ DF cand_mul(DF a,DF b){ float p=a.hi*b.hi; float e=__fmaf_rn(a.hi,b.hi,-p); e=__fmaf_rn(a.hi,b.lo,e); e=__fmaf_rn(a.lo,b.hi,e); return cand_quick_two_sum(p,e); }
extern "C" __global__ void split_df(const double* x,float2* out,unsigned n){
  unsigned j=blockIdx.x*blockDim.x+threadIdx.x; if(j>=n) return; double v=x[j]; float h=(float)v; out[j]=make_float2(h,(float)(v-(double)h));
}
extern "C" __global__ void doublefloat(const float2* values,const unsigned* indices,const unsigned* offsets,const float2* x,double* out,unsigned lines){
  unsigned line=(blockIdx.x*blockDim.x+threadIdx.x)/32, lane=threadIdx.x&31; if(line>=lines) return;
  DF sum{0.f,0.f};
  for(unsigned i=offsets[line]+lane;i<offsets[line+1];i+=32){ float2 a=values[i]; float2 b=x[indices[i]]; sum=cand_add(sum, cand_mul(DF{a.x,a.y},DF{b.x,b.y})); }
  for(unsigned k=16;k;k>>=1){ float oh=__shfl_down_sync(0xffffffffu,sum.hi,k); float ol=__shfl_down_sync(0xffffffffu,sum.lo,k); if(lane<k) sum=cand_add(sum,DF{oh,ol}); }
  if(lane==0) out[line]=(double)sum.hi+(double)sum.lo;
}
// ---- Candidate D: FP64 warp-per-row but guards done on the integer pipe (no DSETP), single isfinite at end.
extern "C" __global__ void fp64_intguard(const double* values,const unsigned* indices,const unsigned* offsets,const double* x,double* out,unsigned* guards,unsigned lines){
  unsigned line=(blockIdx.x*blockDim.x+threadIdx.x)/32, lane=threadIdx.x&31; if(line>=lines) return;
  double sum=0.0; unsigned g=0;
  for(unsigned i=offsets[line]+lane;i<offsets[line+1];i+=32){
    double a=values[i], b=x[indices[i]]; double p=__dmul_rn(a,b);
    // product-loss guard on the integer pipe: nonzero operands, zero product
    unsigned ah=__double2hiint(a)&0x7fffffffu, al=__double2loint(a); unsigned bh=__double2hiint(b)&0x7fffffffu, bl=__double2loint(b);
    unsigned ph=__double2hiint(p)&0x7fffffffu, pl=__double2loint(p);
    g|=(((ah|al)!=0u)&((bh|bl)!=0u)&((ph|pl)==0u))<<2;
    sum=__dadd_rn(sum,p);
  }
  for(unsigned k=16;k;k>>=1){double o=__shfl_down_sync(0xffffffffu,sum,k); unsigned og=__shfl_down_sync(0xffffffffu,g,k); if(lane<k){sum=__dadd_rn(sum,o); g|=og;}}
  if(lane==0){ unsigned sh=__double2hiint(sum)&0x7ff00000u; g|=(sh==0x7ff00000u); out[line]=sum; guards[line]|=g; }
}

struct CSR { unsigned m,n,nnz; std::vector<unsigned> off,idx; std::vector<double> val; };
static CSR load(const char* path){ FILE* f=fopen(path,"rb"); CSR c; fread(&c.m,4,1,f); fread(&c.n,4,1,f); fread(&c.nnz,4,1,f); c.off.resize(c.m+1); c.idx.resize(c.nnz); c.val.resize(c.nnz); fread(c.off.data(),4,c.m+1,f); fread(c.idx.data(),4,c.nnz,f); fread(c.val.data(),8,c.nnz,f); fclose(f); return c; }
static CSR tile(const CSR& a,unsigned k){ CSR c; c.m=a.m*k; c.n=a.n*k; c.nnz=a.nnz*k; c.off.resize(c.m+1); c.off[0]=0; for(unsigned t=0;t<k;t++) for(unsigned r=0;r<a.m;r++){ unsigned R=t*a.m+r; c.off[R+1]=c.off[R]+(a.off[r+1]-a.off[r]); for(unsigned j=a.off[r];j<a.off[r+1];j++){ c.idx.push_back(t*a.n+a.idx[j]); c.val.push_back(a.val[j]); } } return c; }

template<class F> static float timeit(F f,int reps,cudaStream_t s){ cudaEvent_t a,b; CK(cudaEventCreate(&a)); CK(cudaEventCreate(&b)); for(int i=0;i<5;i++) f(); CK(cudaStreamSynchronize(s)); CK(cudaEventRecord(a,s)); for(int i=0;i<reps;i++) f(); CK(cudaEventRecord(b,s)); CK(cudaEventSynchronize(b)); float ms; CK(cudaEventElapsedTime(&ms,a,b)); return ms*1000.f/reps; }

int main(int argc,char** argv){
  const char* path=argv[1]; unsigned k=argc>2?atoi(argv[2]):1; int reps=argc>3?atoi(argv[3]):200;
  CSR base=load(path); CSR c= k>1? tile(base,k): base;
  // Ruiz-like scaling stand-in: multiply by pseudo-random non-dyadic scales so values are not exactly FP32.
  std::mt19937_64 rng(17); std::uniform_real_distribution<double> u(0.3,1.7);
  std::vector<double> rs(c.m), cs(c.n); for(auto& v:rs) v=u(rng); for(auto& v:cs) v=u(rng);
  for(unsigned r=0;r<c.m;r++) for(unsigned j=c.off[r];j<c.off[r+1];j++) c.val[j]*=rs[r]*cs[c.idx[j]];
  std::vector<double> x(c.n); for(auto& v:x) v=u(rng)-1.0;
  // Host splits
  std::vector<Parts3> vp3(c.nnz); std::vector<Parts2> vp2(c.nnz); std::vector<float> v32(c.nnz), x32(c.n); std::vector<float2> vdf(c.nnz), xdf(c.n);
  for(unsigned j=0;j<c.nnz;j++){ double v=c.val[j]; int e; double m=frexp(v,&e); Parts3 p; p.part[0]=(float)m; double r=m-(double)p.part[0]; p.part[1]=(float)r; p.part[2]=(float)(r-(double)p.part[1]); p.exponent=e; vp3[j]=p; vp2[j]=Parts2{{p.part[0],p.part[1]},p.exponent}; v32[j]=(float)v; float h=(float)v; vdf[j]=make_float2(h,(float)(v-(double)h)); }
  for(unsigned j=0;j<c.n;j++){ x32[j]=(float)x[j]; float h=(float)x[j]; xdf[j]=make_float2(h,(float)(x[j]-(double)h)); }
  // Device
  double *dval,*dx,*dout; float *dval32,*dx32,*dout32; unsigned *didx,*doff,*dg; Parts3 *dvp3,*dxp3; Parts2 *dvp2; float2 *dvdf,*dxdf; double *dzero,*dnext,*dwide_lo,*dwide_hi;
  CK(cudaMalloc(&dval,8*c.nnz)); CK(cudaMalloc(&dx,8*c.n)); CK(cudaMalloc(&dout,8*c.m)); CK(cudaMalloc(&dval32,4*c.nnz)); CK(cudaMalloc(&dx32,4*c.n)); CK(cudaMalloc(&dout32,4*c.m));
  CK(cudaMalloc(&didx,4*c.nnz)); CK(cudaMalloc(&doff,4*(c.m+1))); CK(cudaMalloc(&dg,4*c.m)); CK(cudaMalloc(&dvp3,sizeof(Parts3)*c.nnz)); CK(cudaMalloc(&dvp2,sizeof(Parts2)*c.nnz)); CK(cudaMemcpy(dvp2,vp2.data(),sizeof(Parts2)*c.nnz,cudaMemcpyHostToDevice)); CK(cudaMalloc(&dxp3,sizeof(Parts3)*c.n)); CK(cudaMalloc(&dvdf,8*c.nnz)); CK(cudaMalloc(&dxdf,8*c.n)); CK(cudaMalloc(&dzero,8*std::max(c.n,c.m)));
  CK(cudaMemcpy(dval,c.val.data(),8*c.nnz,cudaMemcpyHostToDevice)); CK(cudaMemcpy(dx,x.data(),8*c.n,cudaMemcpyHostToDevice)); CK(cudaMemcpy(dval32,v32.data(),4*c.nnz,cudaMemcpyHostToDevice)); CK(cudaMemcpy(dx32,x32.data(),4*c.n,cudaMemcpyHostToDevice));
  CK(cudaMemcpy(didx,c.idx.data(),4*c.nnz,cudaMemcpyHostToDevice)); CK(cudaMemcpy(doff,c.off.data(),4*(c.m+1),cudaMemcpyHostToDevice)); CK(cudaMemset(dg,0,4*c.m)); CK(cudaMemcpy(dvp3,vp3.data(),sizeof(Parts3)*c.nnz,cudaMemcpyHostToDevice)); CK(cudaMemcpy(dvdf,vdf.data(),8*c.nnz,cudaMemcpyHostToDevice)); CK(cudaMemcpy(dxdf,xdf.data(),8*c.n,cudaMemcpyHostToDevice)); CK(cudaMemset(dzero,0,8*std::max(c.n,c.m)));
  CK(cudaMalloc(&dnext,8*std::max(c.n,c.m))); CK(cudaMalloc(&dwide_lo,8*std::max(c.n,c.m))); CK(cudaMalloc(&dwide_hi,8*std::max(c.n,c.m)));
  // Equality rows at zero: the dual projection clamps raw/step to 0, so the fused
  // dual kernels store exactly -dot (step 1, toward 1, back 0, anchor 0).
  CK(cudaMemset(dwide_lo,0,8*std::max(c.n,c.m))); CK(cudaMemset(dwide_hi,0,8*std::max(c.n,c.m)));
  cudaStream_t s; CK(cudaStreamCreate(&s));
  unsigned grid=(c.m+7)/8, vgrid=(c.n+255)/256; // same launch geometry as the executor: 256 threads = 8 rows
  // Reference result
  std::vector<double> ref(c.m,0.0); for(unsigned r=0;r<c.m;r++){ long double sacc=0; for(unsigned j=c.off[r];j<c.off[r+1];j++) sacc+=(long double)c.val[j]*x[c.idx[j]]; ref[r]=(double)sacc; }
  auto check=[&](const char* name,bool f32){ std::vector<double> h(c.m); bool negated=strstr(name,"fused")!=nullptr; if(f32){ std::vector<float> hf(c.m); CK(cudaMemcpy(hf.data(),dout32,4*c.m,cudaMemcpyDeviceToHost)); for(unsigned i=0;i<c.m;i++) h[i]=hf[i]; } else CK(cudaMemcpy(h.data(),dout,8*c.m,cudaMemcpyDeviceToHost)); double mx=0; for(unsigned i=0;i<c.m;i++){ double v=negated?-h[i]:h[i]; double d=fabs(v-ref[i])/std::max(1e-300,fabs(ref[i])); mx=std::max(mx,d);} return mx; };
  printf("matrix %s x%u: m=%u n=%u nnz=%u  grid=%u blocks of 256\n",path,k,c.m,c.n,c.nnz,grid);
  printf("%-34s %10s %12s\n","kernel","us/launch","max rel err");
  #define RUN(name,f32,launch) { float us=timeit([&]{launch;},reps,s); double e=check(name,f32); printf("%-34s %10.3f %12.3e\n",name,us,e); }
  RUN("ref_fp64 (tuned-style)",false,(ref_fp64<<<grid,256,0,s>>>(dval,didx,doff,dx,dout,c.m)));
  RUN("research_native64",false,(research_native64<<<grid,256,0,s>>>(dval,didx,doff,dx,dout,dg,c.m,0,0,0,0,dzero,dzero)));
  RUN("research_native32",false,(research_native32<<<grid,256,0,s>>>(dval32,didx,doff,dx,dout,dg,c.m,0,0,0,0,dzero,dzero)));
  RUN("research_components3_native",false,(research_components3_native<<<grid,256,0,s>>>(dvp3,didx,doff,dx,dout,dg,c.m,0,0,0,0,dzero,dzero)));
  RUN("research_components3_cross",false,(research_components3_cross<<<grid,256,0,s>>>(dvp3,didx,doff,dx,dout,dg,c.m,0,0,0,0,dzero,dzero)));
  RUN("research_components2_cross",false,(research_components2_cross<<<grid,256,0,s>>>(dvp2,didx,doff,dx,dout,dg,c.m,0,0,0,0,dzero,dzero)));
  RUN("A cross3 + plain DADD",false,(cross3_plain_dadd<<<grid,256,0,s>>>(dvp3,didx,doff,dx,dout,c.m)));
  RUN("B cross3 tri, presplit x (incl)",false,(split_vector<<<vgrid,256,0,s>>>(dx,dxp3,c.n), cross3_tri_presplit<<<grid,256,0,s>>>(dvp3,didx,doff,dxp3,dout,c.m)));
  RUN("C double-float, presplit (incl)",false,(split_df<<<vgrid,256,0,s>>>(dx,dxdf,c.n), doublefloat<<<grid,256,0,s>>>(dvdf,didx,doff,dxdf,dout,c.m)));
  RUN("D fp64 + integer-pipe guards",false,(fp64_intguard<<<grid,256,0,s>>>(dval,didx,doff,dx,dout,dg,c.m)));
  RUN("research_intguard64 (ADR-0022)",false,(research_intguard64<<<grid,256,0,s>>>(dval,didx,doff,dx,dout,dg,c.m,0,0,0,0,dzero,dzero)));
  // Fused kernels also perform the vector update (the memset is charged inside).
  RUN("research_fused_dual_64 (ADR-0022)",false,(cudaMemsetAsync(dout,0,8*c.m,s), research_fused_dual_64<<<grid,256,0,s>>>(dval,didx,doff,dx,dout,dwide_lo,dwide_hi,dzero,dnext,dg,dg,dg,1.0,1.0,0.0,c.m)));
  RUN("research_fused_dual_df (ADR-0022, incl. no split)",false,(cudaMemsetAsync(dout,0,8*c.m,s), research_fused_dual_df<<<grid,256,0,s>>>((const float2*)dvdf,didx,doff,(const float2*)dxdf,dout,(float2*)dxp3,dwide_lo,dwide_hi,dzero,dnext,dg,dg,dg,1.0,1.0,0.0,c.m)));
  RUN("store32 gather64 acc64",false,(store32_acc64<<<grid,256,0,s>>>(dval32,didx,doff,dx,dout,c.m)));
  RUN("plain_fp32 (all FP32)",true,(plain_fp32<<<grid,256,0,s>>>(dval32,didx,doff,dx32,dout32,c.m)));
  // Launch-overhead floor: empty-ish kernel
  RUN("ref_fp64 lines=8 (launch floor)",false,(ref_fp64<<<1,256,0,s>>>(dval,didx,doff,dx,dout,8)));
  return 0;
}
