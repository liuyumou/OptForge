// Reuse the admitted allocation, validation and inverse-proposal boundaries.
// Only the numerical projection representation differs: precompute A G^-1.
#define sp_factor_create sp_base_create
#define sp_factor_advance sp_base_advance
#define sp_factor_destroy sp_base_destroy
#define sp_factor_inverse sp_base_inverse
#include "factor_projection.cu"
#undef sp_factor_create
#undef sp_factor_advance
#undef sp_factor_destroy
#undef sp_factor_inverse

extern "C" int sp_factor_create(int m,int n,const double*a,const double*b,const double*c,double rho,void**out) {
 int code=sp_base_create(m,n,a,b,c,rho,out);if(code)return code;
 auto*z=static_cast<State*>(*out);
 try {
  ck(cudaFree(z->work));z->work=nullptr;alloc(z->work,size_t(m)*n);
  ck(cudaMemcpy(z->work,z->a,size_t(m)*n*sizeof(double),cudaMemcpyDeviceToDevice));
  const double one=1.;
  // G=L L^T, so T=A L^-T L^-1 and T^T=G^-1 A^T.
  cb(cublasDtrsm(z->blas,CUBLAS_SIDE_RIGHT,CUBLAS_FILL_MODE_LOWER,CUBLAS_OP_T,CUBLAS_DIAG_NON_UNIT,m,n,&one,z->g,n,z->work,m));
  cb(cublasDtrsm(z->blas,CUBLAS_SIDE_RIGHT,CUBLAS_FILL_MODE_LOWER,CUBLAS_OP_N,CUBLAS_DIAG_NON_UNIT,m,n,&one,z->g,n,z->work,m));
  cb(cublasDtrsv(z->blas,CUBLAS_FILL_MODE_LOWER,CUBLAS_OP_N,CUBLAS_DIAG_NON_UNIT,n,z->g,n,z->c,1));
  cb(cublasDtrsv(z->blas,CUBLAS_FILL_MODE_LOWER,CUBLAS_OP_T,CUBLAS_DIAG_NON_UNIT,n,z->g,n,z->c,1));
  ck(cudaDeviceSynchronize());return 0;
 }catch(int error){delete z;*out=nullptr;return error;}catch(...){delete z;*out=nullptr;return 7;}
}

extern "C" int sp_factor_advance(void*handle,int steps,double*x,double*y) {
 auto*z=static_cast<State*>(handle);if(!z||!x||!y||steps<1||steps>10000)return 4;
 try {
  const double one=1.,zero=0.;int m=z->m,n=z->n;
  for(int k=0;k<steps;++k){
   prepare<<<(m+255)/256,256>>>(m,z->b,z->s,z->u,z->v);
   cb(cublasDgemv(z->blas,CUBLAS_OP_T,m,n,&one,z->work,m,z->v,1,&zero,z->x,1));
   objective<<<(n+255)/256,256>>>(n,z->c,z->rho,z->x);
   cb(cublasDgemv(z->blas,CUBLAS_OP_N,m,n,&one,z->a,m,z->x,1,&zero,z->ax,1));
   project<<<(m+255)/256,256>>>(m,z->b,z->ax,z->s,z->u);
  }
  ck(cudaGetLastError());ck(cudaMemcpy(x,z->x,n*sizeof(double),cudaMemcpyDeviceToHost));
  ck(cudaMemcpy(y,z->u,m*sizeof(double),cudaMemcpyDeviceToHost));
  for(int i=0;i<m;++i)y[i]*=z->rho;
  return 0;
 }catch(int error){return error;}catch(...){return 7;}
}
extern "C" void sp_factor_destroy(void*handle){sp_base_destroy(handle);}
extern "C" int sp_factor_inverse(int n,const double*input,double*output){return sp_base_inverse(n,input,output);}
