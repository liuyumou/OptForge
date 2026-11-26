// Lean FP64 proposal engine. One persistent block per independent target.
// Exact host certification, rather than numerical residuals, decides acceptance.
#include <cuda_runtime.h>
#include <algorithm>
#include <cmath>
#include <cstdint>
#include <new>
#include <vector>

namespace {
struct Matrix { int rows,cols;double* values=nullptr;int* offsets=nullptr;int* indices=nullptr; };
struct Context {
    int r,s,width=0,live_width=0,graph_width=0;double h=0,eps=0;Matrix b,bt;
    double *x=nullptr,*u=nullptr,*bar=nullptr,*obj=nullptr;int *targets=nullptr,*active=nullptr;
    double *tau=nullptr,*sigma=nullptr;
    cudaEvent_t start=nullptr,end=nullptr;
    cudaStream_t stream=nullptr;cudaGraph_t graph=nullptr;cudaGraphExec_t replay=nullptr;
};
int fail(cudaError_t e){return e==cudaSuccess?0:1000+int(e);}
template<class T> cudaError_t upload(T*& p,const std::vector<T>& v){
    if(v.empty())return cudaSuccess;
    auto e=cudaMalloc((void**)&p,v.size()*sizeof(T));
    return e==cudaSuccess?cudaMemcpy(p,v.data(),v.size()*sizeof(T),cudaMemcpyHostToDevice):e;
}
void release(Matrix& m){cudaFree(m.values);cudaFree(m.offsets);cudaFree(m.indices);}
void release(Context* c){
    if(!c)return;
    if(c->replay)cudaGraphExecDestroy(c->replay);if(c->graph)cudaGraphDestroy(c->graph);
    release(c->b);release(c->bt);cudaFree(c->x);cudaFree(c->u);cudaFree(c->bar);cudaFree(c->obj);
    cudaFree(c->tau);cudaFree(c->sigma);
    cudaFree(c->targets);cudaFree(c->active);
    if(c->start)cudaEventDestroy(c->start);if(c->end)cudaEventDestroy(c->end);
    if(c->stream)cudaStreamDestroy(c->stream);delete c;
}
cudaError_t matrix(Matrix& m,const std::vector<double>& a,int r,int s,bool sparse){
    m.rows=r;m.cols=s;if(!sparse)return upload(m.values,a);
    std::vector<double> v;std::vector<int> offsets{0},indices;
    for(int i=0;i<r;++i){for(int j=0;j<s;++j)if(a[size_t(i)*s+j]!=0){
        v.push_back(a[size_t(i)*s+j]);indices.push_back(j);}
        offsets.push_back(int(v.size()));}
    auto e=upload(m.values,v);if(e!=cudaSuccess)return e;
    e=upload(m.offsets,offsets);return e==cudaSuccess?upload(m.indices,indices):e;
}
__device__ double row_dot(Matrix a,int row,const double* x){
    int lane=threadIdx.x&31;double sum=0;
    int first=a.offsets?a.offsets[row]:row*a.cols;
    int end=a.offsets?a.offsets[row+1]:first+a.cols;
    for(int k=first+lane;k<end;k+=32){int j=a.indices?a.indices[k]:k-first;sum+=a.values[k]*x[j];}
    for(int d=16;d;d/=2)sum+=__shfl_down_sync(0xffffffff,sum,d);
    return sum;
}
__global__ void iterate(Matrix b,Matrix bt,double* all_x,double* all_u,const int* targets,
                        const int* active,double h,double eps,const double* tau,const double* sigma,int steps){
    int q=active[blockIdx.x];
    int tid=threadIdx.x,warp=tid/32,lane=tid&31,warps=blockDim.x/32;
    extern __shared__ double shared[];
    double* x=shared;double* bar=x+b.rows;double* u=bar+b.rows;double* obj=u+b.cols;
    for(int i=tid;i<b.rows;i+=blockDim.x){
        x[i]=all_x[size_t(q)*b.rows+i];double v=0;
        if(b.offsets){for(int k=b.offsets[i];k<b.offsets[i+1];++k)if(b.indices[k]==targets[q]){v=b.values[k];break;}}
        else v=b.values[size_t(i)*b.cols+targets[q]];
        obj[i]=v;
    }
    for(int j=tid;j<b.cols;j+=blockDim.x)u[j]=all_u[size_t(q)*b.cols+j];
    __syncthreads();
    for(int k=0;k<steps;++k){
        for(int i=warp;i<b.rows;i+=warps){
            double grad=row_dot(b,i,u);
            if(!lane){double old=x[i],value=fmax(-h,fmin(h,old+tau[i]*(obj[i]-grad)));
                x[i]=value;bar[i]=2*value-old;}
        }
        __syncthreads();
        for(int j=warp;j<b.cols;j+=warps){
            double value=row_dot(bt,j,bar);
            if(!lane){double step=sigma[j],v=u[j]+step*value;u[j]=fmax(0.0,v-2*step)+fmin(0.0,v+eps*step);}
        }
        __syncthreads();
    }
    for(int i=tid;i<b.rows;i+=blockDim.x)all_x[size_t(q)*b.rows+i]=x[i];
    for(int j=tid;j<b.cols;j+=blockDim.x)all_u[size_t(q)*b.cols+j]=u[j];
}
__global__ void objectives(Matrix b,const int* targets,double* obj,int width){
    int i=blockIdx.x*blockDim.x+threadIdx.x,q=blockIdx.y;if(i>=b.rows||q>=width)return;
    double value=0;
    if(b.offsets){for(int k=b.offsets[i];k<b.offsets[i+1];++k)if(b.indices[k]==targets[q]){value=b.values[k];break;}}
    else value=b.values[size_t(i)*b.cols+targets[q]];
    obj[size_t(q)*b.rows+i]=value;
}
__global__ void primal_grid(Matrix b,const double* u,const double* obj,const int* active,
    double h,const double* tau,double* x,double* bar){
    int i=blockIdx.x*4+threadIdx.x/32,q=active[blockIdx.y];if(i>=b.rows)return;
    double grad=row_dot(b,i,u+size_t(q)*b.cols);
    if(!(threadIdx.x&31)){size_t k=size_t(q)*b.rows+i;double old=x[k],v=fmax(-h,fmin(h,old+tau[i]*(obj[k]-grad)));
        x[k]=v;bar[k]=2*v-old;}
}
__global__ void dual_grid(Matrix bt,const double* bar,const int* active,double eps,const double* sigma,double* u){
    int j=blockIdx.x*4+threadIdx.x/32,q=active[blockIdx.y];if(j>=bt.rows)return;
    double value=row_dot(bt,j,bar+size_t(q)*bt.cols);
    if(!(threadIdx.x&31)){size_t k=size_t(q)*bt.rows+j;double step=sigma[j],v=u[k]+step*value;
        u[k]=fmax(0.0,v-2*step)+fmin(0.0,v+eps*step);}
}
void grid_step(Context* c){
    primal_grid<<<dim3((c->r+3)/4,c->live_width),128,0,c->stream>>>(c->b,c->u,c->obj,c->active,c->h,c->tau,c->x,c->bar);
    dual_grid<<<dim3((c->s+3)/4,c->live_width),128,0,c->stream>>>(c->bt,c->bar,c->active,c->eps,c->sigma,c->u);
}
bool width_ok(int width){return width==1||width==8||width==32||width==64;}
#define TRY(call) do{auto e=(call);if(e!=cudaSuccess)return fail(e);}while(0)
}

extern "C" int sp_create(int r,int s,int sparse,const double* b,void** out){
    if(!out)return -1;*out=nullptr;
    if(!b||r<1||s<2||s%2||int64_t(r)*s>1000000||3LL*r+s>6144||(sparse!=0&&sparse!=1))return -1;
    Context* c=nullptr;
    try{
        std::vector<double> a(b,b+size_t(r)*s),t(a.size()),tau(r,0),sigma(s,0);
        for(int i=0;i<r;++i)for(int j=0;j<s;++j){double v=a[size_t(i)*s+j];
            if(!std::isfinite(v))return -3;
            tau[i]+=std::abs(v);sigma[j]+=std::abs(v);t[size_t(j)*r+i]=v;}
        for(auto& v:tau){if(!std::isfinite(v))return -3;v=v>0?.9/v:1.0;}
        for(auto& v:sigma){if(!std::isfinite(v))return -3;v=v>0?.9/v:1.0;}
        c=new Context{};c->r=r;c->s=s;
        auto e=matrix(c->b,a,r,s,sparse!=0);
        if(e==cudaSuccess)e=matrix(c->bt,t,s,r,sparse!=0);
        if(e==cudaSuccess)e=upload(c->tau,tau);
        if(e==cudaSuccess)e=upload(c->sigma,sigma);
        if(e==cudaSuccess)e=cudaMalloc((void**)&c->x,size_t(64)*r*8);
        if(e==cudaSuccess)e=cudaMalloc((void**)&c->u,size_t(64)*s*8);
        if(e==cudaSuccess)e=cudaMalloc((void**)&c->bar,size_t(64)*r*8);
        if(e==cudaSuccess)e=cudaMalloc((void**)&c->obj,size_t(64)*r*8);
        if(e==cudaSuccess)e=cudaMalloc((void**)&c->targets,64*sizeof(int));
        if(e==cudaSuccess)e=cudaMalloc((void**)&c->active,64*sizeof(int));
        if(e==cudaSuccess)e=cudaEventCreate(&c->start);
        if(e==cudaSuccess)e=cudaEventCreate(&c->end);
        if(e==cudaSuccess)e=cudaDeviceSynchronize();
        if(e==cudaSuccess)e=cudaStreamCreateWithFlags(&c->stream,cudaStreamNonBlocking);
        if(e!=cudaSuccess){release(c);return fail(e);}
        *out=c;return 0;
    }catch(...){release(c);return -4;}
}
extern "C" int sp_begin(void* p,int width,const int* slots,double h,double eps){
    if(!p||!slots||!width_ok(width)||!std::isfinite(h)||h<=0||!std::isfinite(eps)||eps<=0||eps>=.25)return -1;
    auto* c=static_cast<Context*>(p);
    for(int q=0;q<width;++q)if(slots[q]<0||slots[q]>=c->s)return -5;
    std::vector<int> active(width);for(int i=0;i<width;++i)active[i]=i;
    if(c->width!=width||c->h!=h||c->eps!=eps){
        if(c->replay)TRY(cudaGraphExecDestroy(c->replay));c->replay=nullptr;
        if(c->graph)TRY(cudaGraphDestroy(c->graph));c->graph=nullptr;
    }
    TRY(cudaMemcpyAsync(c->targets,slots,width*sizeof(int),cudaMemcpyHostToDevice,c->stream));
    TRY(cudaMemcpyAsync(c->active,active.data(),width*sizeof(int),cudaMemcpyHostToDevice,c->stream));
    TRY(cudaMemsetAsync(c->x,0,size_t(width)*c->r*8,c->stream));
    TRY(cudaMemsetAsync(c->u,0,size_t(width)*c->s*8,c->stream));
    c->width=width;c->live_width=width;c->h=h;c->eps=eps;
    objectives<<<dim3((c->r+127)/128,width),128,0,c->stream>>>(c->b,c->targets,c->obj,width);
    TRY(cudaGetLastError());TRY(cudaStreamSynchronize(c->stream));return 0;
}
extern "C" int sp_active(void* p,const int* active){
    if(!p||!active)return -1;auto* c=static_cast<Context*>(p);if(!c->width)return -1;
    std::vector<int> live;
    for(int i=0;i<c->width;++i){if(active[i]!=0&&active[i]!=1)return -1;if(active[i])live.push_back(i);}
    if(!live.empty())TRY(cudaMemcpyAsync(c->active,live.data(),live.size()*sizeof(int),cudaMemcpyHostToDevice,c->stream));
    TRY(cudaStreamSynchronize(c->stream));c->live_width=int(live.size());return 0;
}
extern "C" int sp_advance(void* p,int steps,double* x,double* u,double* ms){
    if(!p||!x||!u||!ms||steps<1||steps>10000)return -1;
    auto* c=static_cast<Context*>(p);if(!c->width)return -1;
    bool grid=c->r>=32;
    if(grid&&c->graph_width!=c->live_width){
        if(c->replay)TRY(cudaGraphExecDestroy(c->replay));c->replay=nullptr;
        if(c->graph)TRY(cudaGraphDestroy(c->graph));c->graph=nullptr;
    }
    if(grid&&c->live_width&&!c->replay){
        TRY(cudaStreamBeginCapture(c->stream,cudaStreamCaptureModeThreadLocal));
        for(int k=0;k<32;++k)grid_step(c);
        auto launch=cudaGetLastError();auto finish=cudaStreamEndCapture(c->stream,&c->graph);
        if(launch!=cudaSuccess)return fail(launch);if(finish!=cudaSuccess)return fail(finish);
        TRY(cudaGraphInstantiate(&c->replay,c->graph,nullptr,nullptr,0));
        c->graph_width=c->live_width;
    }
    TRY(cudaEventRecord(c->start,c->stream));
    if(grid&&c->live_width){for(int k=0;k<steps/32;++k)TRY(cudaGraphLaunch(c->replay,c->stream));
        for(int k=0;k<steps%32;++k)grid_step(c);
    }else if(c->live_width)iterate<<<c->live_width,256,size_t(3*c->r+c->s)*8,c->stream>>>(c->b,c->bt,c->x,c->u,c->targets,c->active,c->h,c->eps,c->tau,c->sigma,steps);
    TRY(cudaGetLastError());TRY(cudaEventRecord(c->end,c->stream));TRY(cudaEventSynchronize(c->end));
    float elapsed;TRY(cudaEventElapsedTime(&elapsed,c->start,c->end));*ms=elapsed;
    TRY(cudaMemcpyAsync(x,c->x,size_t(c->width)*c->r*8,cudaMemcpyDeviceToHost,c->stream));
    TRY(cudaMemcpyAsync(u,c->u,size_t(c->width)*c->s*8,cudaMemcpyDeviceToHost,c->stream));
    TRY(cudaStreamSynchronize(c->stream));return 0;
}
extern "C" int sp_propose_slots(void* p,int width,const int* targets,double h,double eps,
    int steps,int mode,double* x,double* u,double* ms){
    if(mode!=0||steps<1||steps>10000||!x||!u||!ms)return -1;
    int status=sp_begin(p,width,targets,h,eps);return status?status:sp_advance(p,steps,x,u,ms);
}
extern "C" int sp_propose(void* p,int width,const int* targets,double h,double eps,
    int steps,int mode,double* x,double* u,double* ms){
    if(!p||!targets||!width_ok(width))return -1;auto* c=static_cast<Context*>(p);
    int slots[64];for(int q=0;q<width;++q){if(targets[q]<0||targets[q]>=c->s/2)return -5;slots[q]=2*targets[q]+1;}
    return sp_propose_slots(p,width,slots,h,eps,steps,mode,x,u,ms);
}
extern "C" int sp_destroy(void* p){
    if(!p)return 0;auto e=cudaDeviceSynchronize();release(static_cast<Context*>(p));return fail(e);
}
