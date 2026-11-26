// Exact arithmetic over F_65521. A full column rank result is a deterministic
// rational-rank proof when all original denominators are invertible modulo p.
#include <cuda_runtime.h>
#include <chrono>
#include <cstdint>
namespace {
__device__ __forceinline__ uint32_t mul(uint32_t a,uint32_t b){uint32_t x=a*b;
 x=(x&65535)+15*(x>>16);x=(x&65535)+15*(x>>16);return x>=65521?x-65521:x;}
__global__ void pivot(uint32_t*a,int m,int n,int k,int*chosen,uint32_t*inverse,int*rank){
 if(threadIdx.x||blockIdx.x||*rank!=k)return;int row=k;while(row<m&&!a[size_t(row)*n+k])++row;
 *chosen=row;if(row==m)return;uint32_t v=a[size_t(row)*n+k],r=1;
 for(unsigned p=65519;p;p>>=1,v=mul(v,v))if(p&1)r=mul(r,v);*inverse=r;*rank=k+1;
}
__global__ void prepare(uint32_t*a,int n,int k,const int*chosen,const uint32_t*inverse,const int*rank){
 int j=blockIdx.x*blockDim.x+threadIdx.x;if(j>=n||*rank!=k+1)return;
 int p=*chosen;uint32_t v=a[size_t(p)*n+j],old=a[size_t(k)*n+j];
 if(p!=k)a[size_t(p)*n+j]=old;a[size_t(k)*n+j]=mul(v,*inverse);
}
__global__ void factors(uint32_t*a,int m,int n,int k,uint32_t*f,const int*rank){
 int i=blockIdx.x*blockDim.x+threadIdx.x;if(i<m&&*rank==k+1){f[i]=a[size_t(i)*n+k];if(i>k)a[size_t(i)*n+k]=0;}
}
__global__ void eliminate(uint32_t*a,int m,int n,int k,const uint32_t*f,const int*rank){
 int i=k+1+blockIdx.y*blockDim.y+threadIdx.y,j=k+1+blockIdx.x*blockDim.x+threadIdx.x;
 if(i>=m||j>=n||*rank!=k+1||!f[i])return;size_t t=size_t(i)*n+j;
 uint32_t v=mul(f[i],a[size_t(k)*n+j]),old=a[t];a[t]=old>=v?old-v:old+65521-v;
}
}
extern "C" int sp_geometry_rank_gpu(int m,int n,const uint32_t*input,uint64_t ns,int*out){
 if(!input||!out||n<1||m<n||uint64_t(m)*n>(1ULL<<28)||!ns)return 4;*out=0;
 for(size_t i=0;i<size_t(m)*n;++i)if(input[i]>=65521)return 4;
 uint32_t *a=nullptr,*f=nullptr,*inv=nullptr;int*state=nullptr;cudaStream_t stream=nullptr;int code=0;
 auto begin=std::chrono::steady_clock::now();
 #define CHECK(x) do{auto e=(x);if(e!=cudaSuccess){code=1000+int(e);goto done;}}while(0)
 CHECK(cudaStreamCreateWithFlags(&stream,cudaStreamNonBlocking));CHECK(cudaMalloc(&a,size_t(m)*n*4));
 CHECK(cudaMalloc(&f,size_t(m)*4));CHECK(cudaMalloc(&inv,4));CHECK(cudaMalloc(&state,8));
 CHECK(cudaMemsetAsync(state,0,8,stream));CHECK(cudaMemcpyAsync(a,input,size_t(m)*n*4,cudaMemcpyHostToDevice,stream));
 for(int k=0;k<n;++k){
  pivot<<<1,1,0,stream>>>(a,m,n,k,state,inv,state+1);
  prepare<<<(n+255)/256,256,0,stream>>>(a,n,k,state,inv,state+1);
  factors<<<(m+255)/256,256,0,stream>>>(a,m,n,k,f,state+1);
  if(k+1<n&&k+1<m)eliminate<<<dim3((n-k-1+31)/32,(m-k-1+7)/8),dim3(32,8),0,stream>>>(a,m,n,k,f,state+1);
  if(k%16==15||k==n-1){CHECK(cudaMemcpyAsync(out,state+1,4,cudaMemcpyDeviceToHost,stream));CHECK(cudaStreamSynchronize(stream));
   if(*out!=k+1)break;
   if(std::chrono::duration_cast<std::chrono::nanoseconds>(std::chrono::steady_clock::now()-begin).count()>ns){code=1;break;}}
 }
 CHECK(cudaGetLastError());
 done:
 if(stream)cudaStreamSynchronize(stream);if(a)cudaFree(a);if(f)cudaFree(f);if(inv)cudaFree(inv);if(state)cudaFree(state);if(stream)cudaStreamDestroy(stream);
 return code;
}
