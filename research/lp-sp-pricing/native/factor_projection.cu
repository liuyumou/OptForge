// Resident FP64 factorized ADMM proposals. No kernel makes a certificate decision.
#include <cuda_runtime.h>
#include <cublas_v2.h>
#include <cusolverDn.h>
#include <cmath>
#include <cstdint>
#include <new>

namespace {
void ck(cudaError_t c) { if(c != cudaSuccess) throw 10; }
void cb(cublasStatus_t c) { if(c != CUBLAS_STATUS_SUCCESS) throw 11; }
void cs(cusolverStatus_t c) { if(c != CUSOLVER_STATUS_SUCCESS) throw 12; }
template<class T> void alloc(T*&p, size_t n) { ck(cudaMalloc((void**)&p,n*sizeof(T))); }
struct State {
 int m=0,n=0; double rho=0.; cublasHandle_t blas=nullptr; cusolverDnHandle_t solver=nullptr;
 double *a=nullptr,*g=nullptr,*b=nullptr,*c=nullptr,*x=nullptr,*u=nullptr,*s=nullptr,*v=nullptr,*ax=nullptr,*work=nullptr;
 int *info=nullptr;
 ~State() {
  cudaDeviceSynchronize();
  cudaFree(work);cudaFree(info);cudaFree(ax);cudaFree(v);cudaFree(s);cudaFree(u);
  cudaFree(x);cudaFree(c);cudaFree(b);cudaFree(g);cudaFree(a);
  if(solver)cusolverDnDestroy(solver);if(blas)cublasDestroy(blas);
 }
};
__global__ void init_s(int m,const double*b,double*s) { int i=blockIdx.x*blockDim.x+threadIdx.x;if(i<m)s[i]=fmax(b[i],0.); }
__global__ void prepare(int m,const double*b,const double*s,const double*u,double*v) {
 int i=blockIdx.x*blockDim.x+threadIdx.x;if(i<m)v[i]=b[i]-s[i]-u[i];
}
__global__ void objective(int n,const double*c,double rho,double*x) {
 int j=blockIdx.x*blockDim.x+threadIdx.x;if(j<n)x[j]+=c[j]/rho;
}
__global__ void project(int m,const double*b,const double*ax,double*s,double*u) {
 int i=blockIdx.x*blockDim.x+threadIdx.x;
 if(i<m){double relaxed=1.6*ax[i]+.6*(s[i]-b[i]);double z=u[i]+relaxed-b[i];s[i]=fmax(-z,0.);u[i]=fmax(z,0.);}
}
__global__ void identity(int n,double*r) {
 size_t k=size_t(blockIdx.x)*blockDim.x+threadIdx.x;if(k<size_t(n)*n)r[k]=(k/n==k%n)?1.:0.;
}
bool finite(const double*p,size_t n){if(!p)return false;for(size_t k=0;k<n;++k)if(!std::isfinite(p[k]))return false;return true;}
}

extern "C" int sp_factor_create(int m,int n,const double*a,const double*b,const double*c,double rho,void**out) {
 if(!out)return 4;*out=nullptr;
 if(n<1||m<n||n>4096||uint64_t(m)*n>(1ULL<<27)||!std::isfinite(rho)||rho<=0
  ||!finite(a,size_t(m)*n)||!finite(b,m)||!finite(c,n))return 4;
 State*z=new(std::nothrow)State();if(!z)return 7;
 try {
  z->m=m;z->n=n;z->rho=rho;cb(cublasCreate(&z->blas));cs(cusolverDnCreate(&z->solver));
  cb(cublasSetMathMode(z->blas,CUBLAS_DEFAULT_MATH));cb(cublasSetAtomicsMode(z->blas,CUBLAS_ATOMICS_NOT_ALLOWED));
  alloc(z->a,size_t(m)*n);alloc(z->g,size_t(n)*n);alloc(z->b,m);alloc(z->c,n);alloc(z->x,n);
  alloc(z->u,m);alloc(z->s,m);alloc(z->v,m);alloc(z->ax,m);alloc(z->info,1);
  ck(cudaMemcpy(z->a,a,size_t(m)*n*sizeof(double),cudaMemcpyHostToDevice));
  ck(cudaMemcpy(z->b,b,m*sizeof(double),cudaMemcpyHostToDevice));ck(cudaMemcpy(z->c,c,n*sizeof(double),cudaMemcpyHostToDevice));
  ck(cudaMemset(z->u,0,m*sizeof(double)));ck(cudaMemset(z->x,0,n*sizeof(double)));
  // cuSOLVER's blocked potrf reads a complete tile, including the unused
  // triangle. Initialize it even though DSYRK writes only the lower triangle.
  ck(cudaMemset(z->g,0,size_t(n)*n*sizeof(double)));
  init_s<<<(m+255)/256,256>>>(m,z->b,z->s);ck(cudaGetLastError());
  const double one=1.,zero=0.;
  cb(cublasDsyrk(z->blas,CUBLAS_FILL_MODE_LOWER,CUBLAS_OP_T,n,m,&one,z->a,m,&zero,z->g,n));
  int size=0,hinfo=0;cs(cusolverDnDpotrf_bufferSize(z->solver,CUBLAS_FILL_MODE_LOWER,n,z->g,n,&size));
  alloc(z->work,size);cs(cusolverDnDpotrf(z->solver,CUBLAS_FILL_MODE_LOWER,n,z->g,n,z->work,size,z->info));
  ck(cudaMemcpy(&hinfo,z->info,sizeof(int),cudaMemcpyDeviceToHost));if(hinfo)throw 20;
  *out=z;return 0;
 }catch(int code){delete z;return code;}catch(...){delete z;return 7;}
}

extern "C" int sp_factor_advance(void*handle,int steps,double*x,double*y) {
 auto*z=static_cast<State*>(handle);if(!z||!x||!y||steps<1||steps>10000)return 4;
 try {
  const double one=1.,zero=0.;int m=z->m,n=z->n;
  for(int k=0;k<steps;++k){
   prepare<<<(m+255)/256,256>>>(m,z->b,z->s,z->u,z->v);
   cb(cublasDgemv(z->blas,CUBLAS_OP_T,m,n,&one,z->a,m,z->v,1,&zero,z->x,1));
   objective<<<(n+255)/256,256>>>(n,z->c,z->rho,z->x);
   cb(cublasDtrsv(z->blas,CUBLAS_FILL_MODE_LOWER,CUBLAS_OP_N,CUBLAS_DIAG_NON_UNIT,n,z->g,n,z->x,1));
   cb(cublasDtrsv(z->blas,CUBLAS_FILL_MODE_LOWER,CUBLAS_OP_T,CUBLAS_DIAG_NON_UNIT,n,z->g,n,z->x,1));
   cb(cublasDgemv(z->blas,CUBLAS_OP_N,m,n,&one,z->a,m,z->x,1,&zero,z->ax,1));
   project<<<(m+255)/256,256>>>(m,z->b,z->ax,z->s,z->u);
  }
  ck(cudaGetLastError());ck(cudaMemcpy(x,z->x,n*sizeof(double),cudaMemcpyDeviceToHost));
  ck(cudaMemcpy(y,z->u,m*sizeof(double),cudaMemcpyDeviceToHost));
  for(int i=0;i<m;++i)y[i]*=z->rho;
  return 0;
 }catch(int code){return code;}catch(...){return 7;}
}

extern "C" void sp_factor_destroy(void*handle){delete static_cast<State*>(handle);}

extern "C" int sp_factor_inverse(int n,const double*input,double*output) {
 if(n<1||n>4096||!output||!finite(input,size_t(n)*n))return 4;
 State*z=new(std::nothrow)State();if(!z)return 7;int*piv=nullptr;
 try{
  cs(cusolverDnCreate(&z->solver));alloc(z->a,size_t(n)*n);alloc(z->g,size_t(n)*n);alloc(z->info,1);alloc(piv,n);
  ck(cudaMemcpy(z->a,input,size_t(n)*n*sizeof(double),cudaMemcpyHostToDevice));
  int size=0,hinfo=0;cs(cusolverDnDgetrf_bufferSize(z->solver,n,n,z->a,n,&size));alloc(z->work,size);
  cs(cusolverDnDgetrf(z->solver,n,n,z->a,n,z->work,piv,z->info));
  ck(cudaMemcpy(&hinfo,z->info,sizeof(int),cudaMemcpyDeviceToHost));if(hinfo)throw 21;
  identity<<<(size_t(n)*n+255)/256,256>>>(n,z->g);ck(cudaGetLastError());
  cs(cusolverDnDgetrs(z->solver,CUBLAS_OP_N,n,n,z->a,n,piv,z->g,n,z->info));
  ck(cudaMemcpy(&hinfo,z->info,sizeof(int),cudaMemcpyDeviceToHost));if(hinfo)throw 22;
  ck(cudaMemcpy(output,z->g,size_t(n)*n*sizeof(double),cudaMemcpyDeviceToHost));cudaFree(piv);delete z;return 0;
 }catch(int code){cudaFree(piv);delete z;return code;}catch(...){cudaFree(piv);delete z;return 7;}
}
