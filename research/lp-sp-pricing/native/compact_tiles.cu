// Bounded state, optional bounded tile cache, and two pinned upload slots.
#include <cuda_runtime.h>
#include <algorithm>
#include <cmath>
#include <cstdint>
#include <cstring>
#include <vector>

namespace {
struct Tile {int row,col,nr,nc;double *v,*tv;int *off,*idx,*toff,*tidx;};
struct Slot {char *host=nullptr,*device=nullptr;cudaStream_t copy=nullptr;cudaEvent_t ready=nullptr,done=nullptr;};
struct Engine {
    int r,s,capacity,width=0,phase=0,next=0;size_t cache_capacity=0,used=0,tile_bytes=0;
    double h=0,eps=0,*state=nullptr,*x,*u,*bar,*gx,*gu,*cost,*tau,*sigma;
    char* cache=nullptr;cudaStream_t compute=nullptr;cudaEvent_t start=nullptr,end=nullptr;
    cudaGraph_t graph=nullptr;cudaGraphExec_t replay=nullptr;
    Slot slots[2];std::vector<Tile> tiles;
};
int error(cudaError_t e){return e==cudaSuccess?0:1000+int(e);}
#define CUDA(x) do{auto status=(x);if(status!=cudaSuccess)return error(status);}while(0)
void drop_graph(Engine* e){if(e->replay)cudaGraphExecDestroy(e->replay);e->replay=nullptr;
    if(e->graph)cudaGraphDestroy(e->graph);e->graph=nullptr;}
void destroy(Engine* e){if(!e)return;if(e->compute)cudaStreamSynchronize(e->compute);drop_graph(e);
    for(auto& s:e->slots){if(s.copy)cudaStreamSynchronize(s.copy);if(s.host)cudaFreeHost(s.host);
        if(s.device)cudaFree(s.device);if(s.ready)cudaEventDestroy(s.ready);if(s.done)cudaEventDestroy(s.done);
        if(s.copy)cudaStreamDestroy(s.copy);}
    if(e->state)cudaFree(e->state);if(e->cache)cudaFree(e->cache);
    if(e->start)cudaEventDestroy(e->start);if(e->end)cudaEventDestroy(e->end);
    if(e->compute)cudaStreamDestroy(e->compute);delete e;}
size_t align(size_t x){return (x+15)&~size_t(15);}
template<class T> size_t append(std::vector<char>& p,const std::vector<T>& values){
    size_t offset=align(p.size());p.resize(offset+sizeof(T)*values.size());
    if(!values.empty())std::memcpy(p.data()+offset,values.data(),sizeof(T)*values.size());return offset;}
__device__ double sumwarp(double x){for(int d=16;d;d/=2)x+=__shfl_down_sync(0xffffffff,x,d);return x;}
__global__ void multiply(Tile t,int transpose,int width,int input_size,int output_size,
                         const double* input,double* output){
    int row=blockIdx.x*4+threadIdx.x/32,lane=threadIdx.x&31;
    int rows=transpose?t.nc:t.nr,cols=transpose?t.nr:t.nc;
    if(row>=rows)return;int firstq=blockIdx.y*4;
    int out0=transpose?t.col:t.row,in0=transpose?t.row:t.col;
    int* offsets=transpose?t.toff:t.off;int* indices=transpose?t.tidx:t.idx;
    double* values=transpose?t.tv:t.v;double accum[4]={0,0,0,0};
    int begin=offsets?offsets[row]:0,end=offsets?offsets[row+1]:cols;
    for(int k=begin+lane;k<end;k+=32){
        int column=offsets?indices[k]:k;
        double v=offsets?values[k]:t.v[transpose?size_t(column)*t.nc+row:size_t(row)*t.nc+column];
        #pragma unroll
        for(int q=0;q<4;++q)if(firstq+q<width)accum[q]+=v*input[size_t(firstq+q)*input_size+in0+column];
    }
    #pragma unroll
    for(int q=0;q<4;++q){double v=sumwarp(accum[q]);
        if(!lane&&firstq+q<width)output[size_t(firstq+q)*output_size+out0+row]+=v;}
}
__global__ void primal(int r,int width,double h,const double* tau,const double* cost,
                       const double* gradient,double* x,double* bar){
    size_t k=size_t(blockIdx.x)*blockDim.x+threadIdx.x;if(k>=size_t(r)*width)return;
    double old=x[k],next=fmax(-h,fmin(h,old+tau[k%r]*(cost[k]-gradient[k])));
    x[k]=next;bar[k]=2*next-old;}
__global__ void dual(int s,int width,double eps,const double* sigma,const double* gradient,double* u){
    size_t k=size_t(blockIdx.x)*blockDim.x+threadIdx.x;if(k>=size_t(s)*width)return;
    double step=sigma[k%s],v=u[k]+step*gradient[k];u[k]=fmax(0.,v-2*step)+fmin(0.,v+eps*step);}
void product(Engine* e,Tile t,int phase){
    int rows=phase?t.nc:t.nr;
    multiply<<<dim3((rows+3)/4,(e->width+3)/4),128,0,e->compute>>>(t,phase,e->width,
        phase?e->r:e->s,phase?e->s:e->r,phase?e->bar:e->u,phase?e->gu:e->gx);}
void finish(Engine* e,int phase){
    if(!phase)primal<<<(size_t(e->r)*e->width+255)/256,256,0,e->compute>>>(e->r,e->width,e->h,e->tau,e->cost,e->gx,e->x,e->bar);
    else dual<<<(size_t(e->s)*e->width+255)/256,256,0,e->compute>>>(e->s,e->width,e->eps,e->sigma,e->gu,e->u);}
void step(Engine* e){for(int phase=0;phase<2;++phase){
    cudaMemsetAsync(phase?e->gu:e->gx,0,size_t(e->width)*(phase?e->s:e->r)*8,e->compute);
    for(auto t:e->tiles)product(e,t,phase);finish(e,phase);}}
}

extern "C" int sp_compact_create(int r,int s,int width,int tr,int tc,uint64_t cache_bytes,void** out){
    if(!out)return -1;*out=nullptr;
    if(r<1||s<2||s%2||width<1||width>64||tr<1||tr>256||tc<1||tc>512||cache_bytes>(256ULL<<20))return -1;
    uint64_t count=uint64_t(width)*(4ULL*r+2ULL*s)+r+s;
    if(count*8>(256ULL<<20))return -2;
    Engine* e=new Engine;e->r=r;e->s=s;e->capacity=width;e->cache_capacity=cache_bytes;
    e->tile_bytes=align(size_t(tr)*tc*24+size_t(tr+tc+2)*4+128);
    auto init=[&]()->int{
        CUDA(cudaStreamCreateWithFlags(&e->compute,cudaStreamNonBlocking));
        CUDA(cudaEventCreate(&e->start));CUDA(cudaEventCreate(&e->end));
        CUDA(cudaMalloc(&e->state,count*8));
        e->x=e->state;e->bar=e->x+size_t(width)*r;e->gx=e->bar+size_t(width)*r;
        e->cost=e->gx+size_t(width)*r;e->u=e->cost+size_t(width)*r;e->gu=e->u+size_t(width)*s;
        e->tau=e->gu+size_t(width)*s;e->sigma=e->tau+r;
        if(cache_bytes)CUDA(cudaMalloc(&e->cache,cache_bytes));
        for(auto& slot:e->slots){CUDA(cudaStreamCreateWithFlags(&slot.copy,cudaStreamNonBlocking));
            CUDA(cudaEventCreateWithFlags(&slot.ready,cudaEventDisableTiming));
            CUDA(cudaEventCreateWithFlags(&slot.done,cudaEventDisableTiming));
            CUDA(cudaHostAlloc(&slot.host,e->tile_bytes,cudaHostAllocDefault));
            CUDA(cudaMalloc(&slot.device,e->tile_bytes));CUDA(cudaEventRecord(slot.done,e->compute));}
        return 0;};
    int code=init();if(code){destroy(e);return code;}*out=e;return 0;
}
extern "C" int sp_compact_push(void* handle,int row,int col,int nr,int nc,const double* a,int sparse){
    if(!handle||!a||nr<1||nc<1||(sparse!=0&&sparse!=1))return -1;auto* e=static_cast<Engine*>(handle);
    if(row<0||col<0||row+nr>e->r||col+nc>e->s||uint64_t(nr)*nc>131072)return -1;
    try{
        std::vector<char> packed;size_t v=0,tv=0,off=0,idx=0,toff=0,tidx=0;
        if(!sparse){std::vector<double> values(a,a+size_t(nr)*nc);
            for(double x:values)if(!std::isfinite(x))return -3;v=append(packed,values);
        }else{
            std::vector<double> values,transposed;std::vector<int> offsets{0},indices,counts(nc,0),tindices;
            for(int i=0;i<nr;++i){for(int j=0;j<nc;++j){double x=a[size_t(i)*nc+j];
                if(!std::isfinite(x))return -3;if(x){values.push_back(x);indices.push_back(j);++counts[j];}}
                offsets.push_back(int(values.size()));}
            std::vector<int> toffsets(nc+1,0);for(int j=0;j<nc;++j)toffsets[j+1]=toffsets[j]+counts[j];
            auto positions=toffsets;transposed.resize(values.size());tindices.resize(values.size());
            for(int i=0;i<nr;++i)for(int k=offsets[i];k<offsets[i+1];++k){int at=positions[indices[k]]++;
                transposed[at]=values[k];tindices[at]=i;}
            v=append(packed,values);idx=append(packed,indices);off=append(packed,offsets);
            tv=append(packed,transposed);tidx=append(packed,tindices);toff=append(packed,toffsets);
        }
        if(packed.size()>e->tile_bytes)return -2;
        auto& slot=e->slots[e->next++%2];CUDA(cudaEventSynchronize(slot.done));
        char* destination=slot.device;
        if(e->cache_capacity){size_t at=align(e->used);if(at+packed.size()>e->cache_capacity)return -2;
            destination=e->cache+at;e->used=at+packed.size();}
        std::memcpy(slot.host,packed.data(),packed.size());
        CUDA(cudaMemcpyAsync(destination,slot.host,packed.size(),cudaMemcpyHostToDevice,slot.copy));
        CUDA(cudaEventRecord(slot.ready,slot.copy));CUDA(cudaStreamWaitEvent(e->compute,slot.ready,0));
        Tile tile{row,col,nr,nc,reinterpret_cast<double*>(destination+v),reinterpret_cast<double*>(destination+tv),
            sparse?reinterpret_cast<int*>(destination+off):nullptr,sparse?reinterpret_cast<int*>(destination+idx):nullptr,
            sparse?reinterpret_cast<int*>(destination+toff):nullptr,sparse?reinterpret_cast<int*>(destination+tidx):nullptr};
        if(e->cache_capacity)e->tiles.push_back(tile);
        else {if(!e->width)return -1;product(e,tile,e->phase);}
        CUDA(cudaEventRecord(slot.done,e->compute));return error(cudaGetLastError());
    }catch(...){return -4;}
}
extern "C" int sp_compact_batch(void* handle,int width,double h,double eps,const double* tau,const double* sigma,const double* cost){
    if(!handle||!tau||!sigma||!cost||!std::isfinite(h)||h<=0||!std::isfinite(eps)||eps<=0||eps>=.25)return -1;
    auto* e=static_cast<Engine*>(handle);if(width<1||width>e->capacity)return -1;
    CUDA(cudaStreamSynchronize(e->compute));drop_graph(e);e->width=width;e->h=h;e->eps=eps;
    CUDA(cudaMemsetAsync(e->x,0,size_t(e->capacity)*e->r*4*8,e->compute));
    CUDA(cudaMemsetAsync(e->u,0,size_t(e->capacity)*e->s*2*8,e->compute));
    CUDA(cudaMemcpyAsync(e->tau,tau,e->r*8,cudaMemcpyHostToDevice,e->compute));
    CUDA(cudaMemcpyAsync(e->sigma,sigma,e->s*8,cudaMemcpyHostToDevice,e->compute));
    CUDA(cudaMemcpyAsync(e->cost,cost,size_t(width)*e->r*8,cudaMemcpyHostToDevice,e->compute));
    CUDA(cudaStreamSynchronize(e->compute));return 0;
}
extern "C" int sp_compact_phase(void* handle,int phase,int done){
    if(!handle||(phase!=0&&phase!=1)||(done!=0&&done!=1))return -1;auto* e=static_cast<Engine*>(handle);
    if(!e->width||e->cache_capacity)return -1;e->phase=phase;
    if(done)finish(e,phase);else CUDA(cudaMemsetAsync(phase?e->gu:e->gx,0,size_t(e->width)*(phase?e->s:e->r)*8,e->compute));
    return error(cudaGetLastError());
}
extern "C" int sp_compact_run(void* handle,int steps){
    if(!handle||steps<1||steps>10000)return -1;auto* e=static_cast<Engine*>(handle);
    if(!e->cache_capacity||!e->width)return -1;
    if(!e->replay){CUDA(cudaStreamBeginCapture(e->compute,cudaStreamCaptureModeThreadLocal));
        for(int i=0;i<16;++i)step(e);CUDA(cudaStreamEndCapture(e->compute,&e->graph));
        CUDA(cudaGraphInstantiate(&e->replay,e->graph,nullptr,nullptr,0));}
    for(int i=0;i<steps/16;++i)CUDA(cudaGraphLaunch(e->replay,e->compute));
    for(int i=0;i<steps%16;++i)step(e);return error(cudaGetLastError());
}
extern "C" int sp_compact_timer(void* handle,int end){if(!handle)return -1;auto* e=static_cast<Engine*>(handle);
    return error(cudaEventRecord(end?e->end:e->start,e->compute));}
extern "C" int sp_compact_result(void* handle,double* x,double* u,double* ms){
    if(!handle||!x||!u||!ms)return -1;auto* e=static_cast<Engine*>(handle);if(!e->width)return -1;
    CUDA(cudaMemcpyAsync(x,e->x,size_t(e->width)*e->r*8,cudaMemcpyDeviceToHost,e->compute));
    CUDA(cudaMemcpyAsync(u,e->u,size_t(e->width)*e->s*8,cudaMemcpyDeviceToHost,e->compute));
    CUDA(cudaStreamSynchronize(e->compute));float value;CUDA(cudaEventElapsedTime(&value,e->start,e->end));*ms=value;return 0;}
extern "C" void sp_compact_destroy(void* handle){destroy(static_cast<Engine*>(handle));}
