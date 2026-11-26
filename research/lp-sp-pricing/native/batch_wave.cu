// Solve-scoped arena and synchronized multi-RHS PDHG. No acceptance on device.
#include <cuda_runtime.h>
#include <algorithm>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <cstring>
#include <vector>

namespace {
struct Matrix {int rows=0,cols=0;double* v=nullptr;int* offsets=nullptr;int* indices=nullptr;};
struct Wave {
    int r=0,s=0,width=0;double h=0,eps=0;Matrix b,bt;
    void* arena=nullptr;size_t capacity=0;
    double *x=nullptr,*u=nullptr,*bar=nullptr,*objectives=nullptr,*tau=nullptr,*sigma=nullptr;
    int* active=nullptr;int* count=nullptr;
    cudaStream_t stream=nullptr;cudaEvent_t start=nullptr,end=nullptr;
    cudaGraph_t graph=nullptr;cudaGraphExec_t replay=nullptr;
    std::vector<double> host_x,host_u;
};
int fail(cudaError_t e){return e==cudaSuccess?0:1000+int(e);}
#define CUDA(call) do{cudaError_t status=(call);if(status!=cudaSuccess)return fail(status);}while(0)
void graphs(Wave* w){
    if(w->replay)cudaGraphExecDestroy(w->replay);w->replay=nullptr;
    if(w->graph)cudaGraphDestroy(w->graph);w->graph=nullptr;
}
void destroy(Wave* w){
    if(!w)return;if(w->stream)cudaStreamSynchronize(w->stream);graphs(w);
    if(w->arena)cudaFree(w->arena);
    if(w->start)cudaEventDestroy(w->start);if(w->end)cudaEventDestroy(w->end);
    if(w->stream)cudaStreamDestroy(w->stream);delete w;
}
struct Packed {
    std::vector<unsigned char> data;
    template<class T> size_t append(const std::vector<T>& values){
        size_t at=(data.size()+15)&~size_t(15);data.resize(at+sizeof(T)*values.size());
        if(!values.empty())std::memcpy(data.data()+at,values.data(),sizeof(T)*values.size());return at;
    }
};
struct MatrixOffsets {size_t values,offsets=0,indices=0;};
MatrixOffsets pack_matrix(Packed& p,const std::vector<double>& a,int rows,int cols,bool sparse){
    if(!sparse)return {p.append(a),0,0};
    std::vector<double> values;std::vector<int> offsets{0},indices;
    for(int i=0;i<rows;++i){for(int j=0;j<cols;++j)if(a[size_t(i)*cols+j]!=0){
        values.push_back(a[size_t(i)*cols+j]);indices.push_back(j);}
        offsets.push_back(int(values.size()));}
    return {p.append(values),p.append(offsets),p.append(indices)};
}
template<class T> T* address(Wave* w,size_t offset){return reinterpret_cast<T*>(static_cast<char*>(w->arena)+offset);}
__device__ double reduce(double v){for(int delta=16;delta;delta/=2)v+=__shfl_down_sync(0xffffffff,v,delta);return v;}

// One warp computes one matrix row for four searches. Its matrix entry and CSR
// index are fetched once and reused for all four right-hand sides.
template<bool PRIMAL> __global__ void wave_step(Matrix a,const double* input,const double* objectives,
    const double* steps,const int* active,const int* count,double h,double eps,double* output,double* bar){
    int row=blockIdx.x*4+threadIdx.x/32,lane=threadIdx.x&31;
    if(row>=a.rows)return;
    int first_query=blockIdx.y*4,live=*count;
    if(first_query>=live)return;
    int ids[4];double sums[4]={0,0,0,0};
    #pragma unroll
    for(int k=0;k<4;++k)ids[k]=first_query+k<live?active[first_query+k]:-1;
    int first=a.offsets?a.offsets[row]:row*a.cols;
    int end=a.offsets?a.offsets[row+1]:first+a.cols;
    for(int k=first+lane;k<end;k+=32){
        double coefficient=a.v[k];int column=a.indices?a.indices[k]:k-first;
        #pragma unroll
        for(int t=0;t<4;++t)if(ids[t]>=0)sums[t]+=coefficient*input[size_t(ids[t])*a.cols+column];
    }
    #pragma unroll
    for(int t=0;t<4;++t){
        double sum=reduce(sums[t]);
        if(!lane&&ids[t]>=0){
            size_t k=size_t(ids[t])*a.rows+row;double old=output[k],step=steps[row];
            if(PRIMAL){double next=fmax(-h,fmin(h,old+step*(objectives[k]-sum)));
                output[k]=next;bar[k]=2*next-old;
            }else{double v=old+step*sum;output[k]=fmax(0.0,v-2*step)+fmin(0.0,v+eps*step);}
        }
    }
}
__device__ double dot(Matrix a,int row,const double* v){
    int lane=threadIdx.x&31,first=a.offsets?a.offsets[row]:row*a.cols;
    int end=a.offsets?a.offsets[row+1]:first+a.cols;double sum=0;
    for(int k=first+lane;k<end;k+=32)sum+=a.v[k]*v[a.indices?a.indices[k]:k-first];
    return reduce(sum);
}
__global__ void small_wave(Matrix b,Matrix bt,double* all_x,double* all_u,const double* objectives,
    const double* tau,const double* sigma,const int* active,const int* count,double h,double eps,int iterations){
    if(blockIdx.x>=*count)return;int q=active[blockIdx.x],tid=threadIdx.x,warp=tid/32,lane=tid&31;
    extern __shared__ double shared[];double* x=shared;double* bar=x+b.rows;double* u=bar+b.rows;
    for(int i=tid;i<b.rows;i+=blockDim.x)x[i]=all_x[size_t(q)*b.rows+i];
    for(int j=tid;j<b.cols;j+=blockDim.x)u[j]=all_u[size_t(q)*b.cols+j];
    __syncthreads();
    for(int iteration=0;iteration<iterations;++iteration){
        for(int i=warp;i<b.rows;i+=blockDim.x/32){double g=dot(b,i,u);
            if(!lane){double old=x[i],v=fmax(-h,fmin(h,old+tau[i]*(objectives[size_t(q)*b.rows+i]-g)));
                x[i]=v;bar[i]=2*v-old;}}
        __syncthreads();
        for(int j=warp;j<b.cols;j+=blockDim.x/32){double g=dot(bt,j,bar);
            if(!lane){double step=sigma[j],v=u[j]+step*g;u[j]=fmax(0.0,v-2*step)+fmin(0.0,v+eps*step);}}
        __syncthreads();
    }
    for(int i=tid;i<b.rows;i+=blockDim.x)all_x[size_t(q)*b.rows+i]=x[i];
    for(int j=tid;j<b.cols;j+=blockDim.x)all_u[size_t(q)*b.cols+j]=u[j];
}
void step(Wave* w){
    wave_step<true><<<dim3((w->r+3)/4,(w->width+3)/4),128,0,w->stream>>>(w->b,w->u,w->objectives,w->tau,
        w->active,w->count,w->h,w->eps,w->x,w->bar);
    wave_step<false><<<dim3((w->s+3)/4,(w->width+3)/4),128,0,w->stream>>>(w->bt,w->bar,nullptr,w->sigma,
        w->active,w->count,w->h,w->eps,w->u,nullptr);
}
}

extern "C" int sp_wave_create(void** output){
    if(!output)return -1;*output=nullptr;Wave* w=nullptr;
    try{
        w=new Wave;auto e=cudaStreamCreateWithFlags(&w->stream,cudaStreamNonBlocking);
        if(e==cudaSuccess)e=cudaEventCreate(&w->start);
        if(e==cudaSuccess)e=cudaEventCreate(&w->end);
        if(e!=cudaSuccess){destroy(w);return fail(e);}*output=w;return 0;
    }catch(...){destroy(w);return -4;}
}
extern "C" int sp_wave_load(void* handle,int r,int s,int sparse,const double* matrix,
    int width,const int* slots,double h,double eps,double* profile){
    if(!handle||!matrix||!slots||!profile||r<1||s<2||s%2||int64_t(r)*s>1000000||
       3LL*r+s>6144||width<1||width>4096||int64_t(width)*(3LL*r+s)>16000000||
       (sparse!=0&&sparse!=1)||!std::isfinite(h)||h<=0||!std::isfinite(eps)||eps<=0||eps>=.25)return -1;
    auto* w=static_cast<Wave*>(handle);
    for(int q=0;q<width;++q)if(slots[q]<0||slots[q]>=s)return -5;
    using Clock=std::chrono::steady_clock;auto start=Clock::now();
    try{
        CUDA(cudaStreamSynchronize(w->stream));graphs(w);
        std::vector<double> a(matrix,matrix+size_t(r)*s),t(a.size()),tau(r,0),sigma(s,0),objectives(size_t(width)*r);
        for(int i=0;i<r;++i)for(int j=0;j<s;++j){double v=a[size_t(i)*s+j];if(!std::isfinite(v))return -3;
            t[size_t(j)*r+i]=v;tau[i]+=std::abs(v);sigma[j]+=std::abs(v);}
        for(auto& v:tau){v=v>0?.9/v:1;if(!std::isfinite(v)||v<=0)return -3;}
        for(auto& v:sigma){v=v>0?.9/v:1;if(!std::isfinite(v)||v<=0)return -3;}
        for(int q=0;q<width;++q)for(int i=0;i<r;++i)objectives[size_t(q)*r+i]=a[size_t(i)*s+slots[q]];
        Packed packed;auto b=pack_matrix(packed,a,r,s,sparse),bt=pack_matrix(packed,t,s,r,sparse);
        size_t ta=packed.append(tau),si=packed.append(sigma),ob=packed.append(objectives);
        std::vector<int> active(width);for(int q=0;q<width;++q)active[q]=q;
        size_t ac=packed.append(active),co=packed.append(std::vector<int>{width});
        size_t x=(packed.data.size()+15)&~size_t(15),u=x+size_t(width)*r*8,bar=u+size_t(width)*s*8;
        size_t bytes=bar+size_t(width)*r*8;
        auto packed_at=Clock::now();
        if(bytes>w->capacity){
            void* next=nullptr;size_t capacity=std::max(bytes,w->capacity*2);
            CUDA(cudaMalloc(&next,capacity));if(w->arena)cudaFree(w->arena);w->arena=next;w->capacity=capacity;
        }
        auto allocated_at=Clock::now();
        CUDA(cudaMemcpyAsync(w->arena,packed.data.data(),packed.data.size(),cudaMemcpyHostToDevice,w->stream));
        CUDA(cudaMemsetAsync(address<unsigned char>(w,x),0,bytes-x,w->stream));
        CUDA(cudaStreamSynchronize(w->stream));
        w->r=r;w->s=s;w->width=width;w->h=h;w->eps=eps;
        w->b={r,s,address<double>(w,b.values),sparse?address<int>(w,b.offsets):nullptr,sparse?address<int>(w,b.indices):nullptr};
        w->bt={s,r,address<double>(w,bt.values),sparse?address<int>(w,bt.offsets):nullptr,sparse?address<int>(w,bt.indices):nullptr};
        w->tau=address<double>(w,ta);w->sigma=address<double>(w,si);w->objectives=address<double>(w,ob);
        w->active=address<int>(w,ac);w->count=address<int>(w,co);
        w->x=address<double>(w,x);w->u=address<double>(w,u);w->bar=address<double>(w,bar);
        w->host_x.resize(size_t(width)*r);w->host_u.resize(size_t(width)*s);
        auto end=Clock::now();
        profile[0]=std::chrono::duration<double>(packed_at-start).count();
        profile[1]=std::chrono::duration<double>(allocated_at-packed_at).count();
        profile[2]=std::chrono::duration<double>(end-allocated_at).count();profile[3]=double(w->capacity);
        return 0;
    }catch(...){return -4;}
}
extern "C" int sp_wave_advance(void* handle,int iterations,int live,const int* active,double* milliseconds){
    if(!handle||!active||!milliseconds||iterations<1||iterations>10000)return -1;
    auto* w=static_cast<Wave*>(handle);if(!w->width||live<0||live>w->width)return -1;
    std::vector<bool> seen(w->width,false);
    for(int i=0;i<live;++i){if(active[i]<0||active[i]>=w->width||seen[active[i]])return -5;seen[active[i]]=true;}
    if(live)CUDA(cudaMemcpyAsync(w->active,active,live*sizeof(int),cudaMemcpyHostToDevice,w->stream));
    CUDA(cudaMemcpyAsync(w->count,&live,sizeof(int),cudaMemcpyHostToDevice,w->stream));
    // Finish pageable control uploads before capture. No global-device barrier.
    CUDA(cudaStreamSynchronize(w->stream));
    if(w->r>=32&&!w->replay&&live){
        CUDA(cudaStreamBeginCapture(w->stream,cudaStreamCaptureModeThreadLocal));
        for(int i=0;i<32;++i)step(w);
        auto launched=cudaGetLastError();auto ended=cudaStreamEndCapture(w->stream,&w->graph);
        if(launched!=cudaSuccess)return fail(launched);if(ended!=cudaSuccess)return fail(ended);
        CUDA(cudaGraphInstantiate(&w->replay,w->graph,nullptr,nullptr,0));
    }
    CUDA(cudaEventRecord(w->start,w->stream));
    if(live&&w->r<32)small_wave<<<live,256,size_t(2*w->r+w->s)*8,w->stream>>>(w->b,w->bt,w->x,w->u,
        w->objectives,w->tau,w->sigma,w->active,w->count,w->h,w->eps,iterations);
    else if(live){for(int i=0;i<iterations/32;++i)CUDA(cudaGraphLaunch(w->replay,w->stream));
        for(int i=0;i<iterations%32;++i)step(w);}
    CUDA(cudaGetLastError());CUDA(cudaEventRecord(w->end,w->stream));
    CUDA(cudaMemcpyAsync(w->host_x.data(),w->x,w->host_x.size()*8,cudaMemcpyDeviceToHost,w->stream));
    CUDA(cudaMemcpyAsync(w->host_u.data(),w->u,w->host_u.size()*8,cudaMemcpyDeviceToHost,w->stream));
    CUDA(cudaStreamSynchronize(w->stream));float elapsed;CUDA(cudaEventElapsedTime(&elapsed,w->start,w->end));
    *milliseconds=elapsed;return 0;
}
extern "C" int sp_wave_view(void* handle,double** x,double** u){
    if(!handle||!x||!u)return -1;auto* w=static_cast<Wave*>(handle);if(!w->width)return -1;
    *x=w->host_x.data();*u=w->host_u.data();return 0;
}
extern "C" int sp_wave_destroy(void* handle){destroy(static_cast<Wave*>(handle));return 0;}
