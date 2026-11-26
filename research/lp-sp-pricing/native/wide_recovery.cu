// Numerical row-space proposals only. Independent exact CPU proofs decide acceptance.
#include <cuda_runtime.h>
#include <cublas_v2.h>
#include <cusolverDn.h>
#include <cmath>
#include <cstdint>
namespace {
void ck(cudaError_t c){if(c!=cudaSuccess)throw 10;}
void cb(cublasStatus_t c){if(c!=CUBLAS_STATUS_SUCCESS)throw 11;}
void cs(cusolverStatus_t c){if(c!=CUSOLVER_STATUS_SUCCESS)throw 12;}
template<class T>void alloc(T*&p,size_t n){ck(cudaMalloc((void**)&p,n*sizeof(T)));}
bool finite(const double*p,size_t n){if(!p)return false;for(size_t i=0;i<n;++i)if(!std::isfinite(p[i]))return false;return true;}
struct Buffers {
 cublasHandle_t blas=nullptr;cusolverDnHandle_t solver=nullptr;
 double *a=nullptr,*g=nullptr,*rhs=nullptr,*c=nullptr,*x=nullptr,*work=nullptr;int*info=nullptr;
 ~Buffers(){cudaDeviceSynchronize();cudaFree(work);cudaFree(info);cudaFree(x);cudaFree(c);cudaFree(rhs);cudaFree(g);cudaFree(a);if(solver)cusolverDnDestroy(solver);if(blas)cublasDestroy(blas);}
};
}
extern "C" int sp_wide_proposal(int m,int n,const double*a,const double*b,const double*c,double*x,double*y){
 if(m<1||n<=m||m>4096||uint64_t(m)*n>(1ULL<<27)||!x||!y||!finite(a,size_t(m)*n)||!finite(b,m)||!finite(c,n))return 4;
 Buffers z;
 try{
  cb(cublasCreate(&z.blas));cs(cusolverDnCreate(&z.solver));
  cb(cublasSetMathMode(z.blas,CUBLAS_DEFAULT_MATH));cb(cublasSetAtomicsMode(z.blas,CUBLAS_ATOMICS_NOT_ALLOWED));
  alloc(z.a,size_t(m)*n);alloc(z.g,size_t(m)*m);alloc(z.rhs,size_t(m)*2);alloc(z.c,n);alloc(z.x,n);alloc(z.info,1);
  ck(cudaMemcpy(z.a,a,size_t(m)*n*sizeof(double),cudaMemcpyHostToDevice));ck(cudaMemcpy(z.rhs,b,m*sizeof(double),cudaMemcpyHostToDevice));
  ck(cudaMemcpy(z.c,c,n*sizeof(double),cudaMemcpyHostToDevice));ck(cudaMemset(z.g,0,size_t(m)*m*sizeof(double)));
  const double one=1.,zero=0.;
  cb(cublasDsyrk(z.blas,CUBLAS_FILL_MODE_LOWER,CUBLAS_OP_N,m,n,&one,z.a,m,&zero,z.g,m));
  cb(cublasDgemv(z.blas,CUBLAS_OP_N,m,n,&one,z.a,m,z.c,1,&zero,z.rhs+m,1));
  int worksize=0,info=0;cs(cusolverDnDpotrf_bufferSize(z.solver,CUBLAS_FILL_MODE_LOWER,m,z.g,m,&worksize));alloc(z.work,worksize);
  cs(cusolverDnDpotrf(z.solver,CUBLAS_FILL_MODE_LOWER,m,z.g,m,z.work,worksize,z.info));
  ck(cudaMemcpy(&info,z.info,sizeof(int),cudaMemcpyDeviceToHost));if(info)return 20;
  cs(cusolverDnDpotrs(z.solver,CUBLAS_FILL_MODE_LOWER,m,2,z.g,m,z.rhs,m,z.info));
  ck(cudaMemcpy(&info,z.info,sizeof(int),cudaMemcpyDeviceToHost));if(info)return 21;
  cb(cublasDgemv(z.blas,CUBLAS_OP_T,m,n,&one,z.a,m,z.rhs,1,&zero,z.x,1));
  ck(cudaMemcpy(x,z.x,n*sizeof(double),cudaMemcpyDeviceToHost));ck(cudaMemcpy(y,z.rhs+m,m*sizeof(double),cudaMemcpyDeviceToHost));
  return finite(x,n)&&finite(y,m)?0:22;
 }catch(int code){return code;}catch(...){return 7;}
}
