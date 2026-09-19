// ADR-0022 diagnostic: launch-overhead microbenchmark.
// Diagnostic only; run under the shared lease through tools/lp_research_budget.py.
// the research executor issues 6 launches per PDHG
// iteration and syncs every 64. Compare per-iteration cost of (a) 6 stream launches,
// (b) one CUDA graph containing 64 iterations x 6 kernels, (c) one persistent
// cooperative kernel doing 64 iterations with grid.sync, all on irregular-2048-sized vectors.
#include <cstdio>
#include <cstdlib>
#include <cooperative_groups.h>
namespace cg = cooperative_groups;
#define CK(x) do{cudaError_t e=(x); if(e!=cudaSuccess){fprintf(stderr,"%s:%d %s\n",__FILE__,__LINE__,cudaGetErrorString(e)); exit(1);} }while(0)

__global__ void vec(double* a,const double* b,unsigned n,double s){ unsigned j=blockIdx.x*blockDim.x+threadIdx.x; if(j<n) a[j]=__dadd_rn(__dmul_rn(s,b[j]),a[j]); }
__global__ void persistent(double* a,double* b,unsigned n,double s,int iters){
  cg::grid_group g=cg::this_grid();
  for(int t=0;t<iters;t++){
    for(int k=0;k<6;k++){ // stand-in for sparse/primal/sparse/dual/store/store phases
      for(unsigned j=blockIdx.x*blockDim.x+threadIdx.x;j<n;j+=gridDim.x*blockDim.x) a[j]=__dadd_rn(__dmul_rn(s,b[j]),a[j]);
      g.sync();
    }
  }
}
int main(){
  unsigned n=2048; double *a,*b; CK(cudaMalloc(&a,8*n)); CK(cudaMalloc(&b,8*n)); CK(cudaMemset(a,0,8*n)); CK(cudaMemset(b,0,8*n));
  cudaStream_t s; CK(cudaStreamCreate(&s)); cudaEvent_t e0,e1; CK(cudaEventCreate(&e0)); CK(cudaEventCreate(&e1));
  const int iters=64, reps=50; unsigned grid=(n+255)/256; float ms;
  // (a) stream launches, sync per 64-iteration chunk (executor pattern)
  for(int w=0;w<3;w++){ for(int t=0;t<iters;t++) for(int k=0;k<6;k++) vec<<<grid,256,0,s>>>(a,b,n,1e-3); CK(cudaStreamSynchronize(s)); }
  CK(cudaEventRecord(e0,s)); for(int r=0;r<reps;r++){ for(int t=0;t<iters;t++) for(int k=0;k<6;k++) vec<<<grid,256,0,s>>>(a,b,n,1e-3); CK(cudaStreamSynchronize(s)); } CK(cudaEventRecord(e1,s)); CK(cudaEventSynchronize(e1)); CK(cudaEventElapsedTime(&ms,e0,e1));
  printf("(a) 6 stream launches/iter + sync per 64:   %8.3f us/iteration  (%.2f us/launch)\n",ms*1000/(reps*iters),ms*1000/(reps*iters*6));
  // (b) CUDA graph of 64 iterations
  cudaGraph_t graph; cudaGraphExec_t exec;
  CK(cudaStreamBeginCapture(s,cudaStreamCaptureModeGlobal)); for(int t=0;t<iters;t++) for(int k=0;k<6;k++) vec<<<grid,256,0,s>>>(a,b,n,1e-3); CK(cudaStreamEndCapture(s,&graph)); CK(cudaGraphInstantiate(&exec,graph,0));
  for(int w=0;w<3;w++){ CK(cudaGraphLaunch(exec,s)); CK(cudaStreamSynchronize(s)); }
  CK(cudaEventRecord(e0,s)); for(int r=0;r<reps;r++){ CK(cudaGraphLaunch(exec,s)); CK(cudaStreamSynchronize(s)); } CK(cudaEventRecord(e1,s)); CK(cudaEventSynchronize(e1)); CK(cudaEventElapsedTime(&ms,e0,e1));
  printf("(b) CUDA graph, 384 nodes, sync per 64:     %8.3f us/iteration  (%.2f us/node)\n",ms*1000/(reps*iters),ms*1000/(reps*iters*6));
  // (c) persistent cooperative kernel
  int dev=0; cudaDeviceProp p; CK(cudaGetDeviceProperties(&p,dev)); int per; CK(cudaOccupancyMaxActiveBlocksPerMultiprocessor(&per,persistent,256,0));
  unsigned cgrid=grid; double sc=1e-3; int it=iters; void* args[]={&a,&b,&n,&sc,&it};
  for(int w=0;w<3;w++){ CK(cudaLaunchCooperativeKernel((void*)persistent,cgrid,256,args,0,s)); CK(cudaStreamSynchronize(s)); }
  CK(cudaEventRecord(e0,s)); for(int r=0;r<reps;r++){ CK(cudaLaunchCooperativeKernel((void*)persistent,cgrid,256,args,0,s)); CK(cudaStreamSynchronize(s)); } CK(cudaEventRecord(e1,s)); CK(cudaEventSynchronize(e1)); CK(cudaEventElapsedTime(&ms,e0,e1));
  printf("(c) persistent kernel, %u blocks, 6 grid.sync/iter: %8.3f us/iteration  (%.2f us/grid.sync)\n",cgrid,ms*1000/(reps*iters),ms*1000/(reps*iters*6));
  // (c') persistent with a wider grid (one block per SM) to see grid.sync scaling
  cgrid=p.multiProcessorCount;
  for(int w=0;w<3;w++){ CK(cudaLaunchCooperativeKernel((void*)persistent,cgrid,256,args,0,s)); CK(cudaStreamSynchronize(s)); }
  CK(cudaEventRecord(e0,s)); for(int r=0;r<reps;r++){ CK(cudaLaunchCooperativeKernel((void*)persistent,cgrid,256,args,0,s)); CK(cudaStreamSynchronize(s)); } CK(cudaEventRecord(e1,s)); CK(cudaEventSynchronize(e1)); CK(cudaEventElapsedTime(&ms,e0,e1));
  printf("(c') persistent kernel, %u blocks, 6 grid.sync/iter: %8.3f us/iteration  (%.2f us/grid.sync)\n",cgrid,ms*1000/(reps*iters),ms*1000/(reps*iters*6));
  return 0;
}
