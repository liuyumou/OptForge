// Shared-matrix batched PDHG proposal engine. Exact host checks decide labels.
// These are CUDA-core products, including simulated scaled E2M1 expansions;
// there is no claim that the prototype uses tensor-core FP4 instructions.
#include <cuda_runtime.h>
#include <algorithm>
#include <cmath>
#include <cstdint>
#include <new>
#include <vector>

struct Matrix { int rows, cols; double* values=nullptr; int* offsets=nullptr; int* indices=nullptr; };
struct Context { int r, s; bool sparse; Matrix b, bt; double step; };
static int fail(cudaError_t e) { return e == cudaSuccess ? 0 : 1000 + int(e); }
template<class T> static cudaError_t upload(T*& p, const std::vector<T>& x) {
    if (x.empty()) return cudaSuccess;
    auto e=cudaMalloc((void**)&p,x.size()*sizeof(T));
    return e==cudaSuccess ? cudaMemcpy(p,x.data(),x.size()*sizeof(T),cudaMemcpyHostToDevice):e;
}
static void release(Matrix& m) { cudaFree(m.values); cudaFree(m.offsets); cudaFree(m.indices); }
static cudaError_t matrix(Matrix& m, const std::vector<double>& dense, int r, int s, bool sparse) {
    m.rows=r; m.cols=s;
    if (!sparse) return upload(m.values,dense);
    std::vector<double> values; std::vector<int> offsets{0}, indices;
    for(int i=0;i<r;++i) {
        for(int j=0;j<s;++j) if(dense[size_t(i)*s+j]!=0) {
            values.push_back(dense[size_t(i)*s+j]); indices.push_back(j);
        }
        offsets.push_back(int(values.size()));
    }
    auto e=upload(m.values,values); if(e!=cudaSuccess)return e;
    e=upload(m.offsets,offsets); return e==cudaSuccess ? upload(m.indices,indices):e;
}
extern "C" int batch_create(int r,int s,int sparse,const double* b,void** out) {
    *out=nullptr;
    try {
        std::vector<double> a(b,b+size_t(r)*s), t(a.size());
        double norm=0;
        for(int i=0;i<r;++i)for(int j=0;j<s;++j) {
            double v=a[size_t(i)*s+j]; if(!std::isfinite(v))return -3;
            norm=std::hypot(norm,v); t[size_t(j)*r+i]=v;
        }
        if(!std::isfinite(norm))return -3;
        Context* c=new Context{r,s,bool(sparse),{}, {}, norm>0 ? .9/norm:1.0};
        auto e=matrix(c->b,a,r,s,sparse);
        if(e==cudaSuccess)e=matrix(c->bt,t,s,r,sparse);
        if(e!=cudaSuccess) { release(c->b);release(c->bt);delete c;return fail(e); }
        *out=c;return 0;
    } catch(const std::bad_alloc&) {return -4;}
}
extern "C" int batch_destroy(void* p) {
    if(!p)return 0; Context* c=(Context*)p;
    auto e=cudaDeviceSynchronize(); release(c->b);release(c->bt);delete c; return fail(e);
}
__device__ double part(double v,bool fp4) {
    if(!fp4)return double(float(v));
    if(v==0 || !isfinite(v))return v;
    int e; double a=frexp(fabs(v),&e)*8; // a in [4,8), scale=2^(e-3)
    double q=a<5 ? 4:6; // scaled E2M1, round-nearest with upper saturation
    return copysign(ldexp(q,e-3),v);
}
__device__ double product(double a,double b,int mode) {
    if(mode==0)return a*b;
    bool fp4=mode>=4;
    int count=fp4 ? (1<<(mode-4)):(1<<mode); // FP32x2/4/8; FP4x1/2/4
    double ap[8],bp[8],result=0;
    for(int k=0;k<count;++k) {ap[k]=part(a,fp4);a-=ap[k];bp[k]=part(b,fp4);b-=bp[k];}
    for(int i=0;i<count;++i)for(int j=0;j<count;++j) {
        if(fp4)result+=ap[i]*bp[j];
        else { float x=float(ap[i]),y=float(bp[j]),p=x*y;
            result+=double(p)+double(fmaf(x,y,-p)); }
    }
    return result;
}
__global__ void multiply(Matrix a,const double* x,double* y,int mode) {
    int row=blockIdx.x,query=blockIdx.y,lane=threadIdx.x;
    double sum=0;
    int begin=a.offsets?a.offsets[row]:row*a.cols;
    int end=a.offsets?a.offsets[row+1]:(row+1)*a.cols;
    for(int k=begin+lane;k<end;k+=blockDim.x) {
        int j=a.indices?a.indices[k]:k-begin;
        sum+=product(a.values[k],x[size_t(query)*a.cols+j],mode);
    }
    __shared__ double partial[128];partial[lane]=sum;__syncthreads();
    for(int d=64;d;d/=2){if(lane<d)partial[lane]+=partial[lane+d];__syncthreads();}
    if(!lane)y[size_t(query)*a.rows+row]=partial[0];
}
__global__ void primal(int r,int width,double h,double tau,const double* grad,
    const double* objectives,double* x,double* extrapolated) {
    int k=blockIdx.x*blockDim.x+threadIdx.x;
    if(k>=r*width)return;
    double old=x[k],v=fmax(-h,fmin(h,old+tau*(objectives[k]-grad[k])));
    x[k]=v;extrapolated[k]=2*v-old;
}
__global__ void dual(int s,int width,double eps,double sigma,const double* product,double* u) {
    int k=blockIdx.x*blockDim.x+threadIdx.x;if(k>=s*width)return;
    double v=u[k]+sigma*product[k];u[k]=v-sigma*fmax(-eps,fmin(2.0,v/sigma));
}
struct Buffers {
    double *x=nullptr,*bar=nullptr,*u=nullptr,*grad=nullptr,*value=nullptr,*obj=nullptr;
    cudaEvent_t start=nullptr,end=nullptr;
    ~Buffers(){cudaFree(x);cudaFree(bar);cudaFree(u);cudaFree(grad);cudaFree(value);cudaFree(obj);
        if(start)cudaEventDestroy(start);if(end)cudaEventDestroy(end);}
};
static int propose_indexed(void* p,int width,const int* targets,double h,double eps,
    int steps,int mode,double* x,double* u,double* milliseconds,bool slots) {
    Context* c=(Context*)p; Buffers d;
    for(int i=0;i<width;++i)if(targets[i]<0||targets[i]>=(slots?c->s:c->s/2))return -5;
    #define TRY(call) do{auto e=(call);if(e!=cudaSuccess)return fail(e);}while(0)
    size_t nx=size_t(width)*c->r,nu=size_t(width)*c->s;
    TRY(cudaMalloc((void**)&d.x,nx*8));TRY(cudaMalloc((void**)&d.bar,nx*8));
    TRY(cudaMalloc((void**)&d.u,nu*8));TRY(cudaMalloc((void**)&d.grad,nx*8));
    TRY(cudaMalloc((void**)&d.value,nu*8));TRY(cudaMalloc((void**)&d.obj,nx*8));
    TRY(cudaMemset(d.x,0,nx*8));TRY(cudaMemset(d.u,0,nu*8));
    // Unit vectors extract objective columns using the same shared matrix.
    try {
        std::vector<double> units(nu,0.0);
        for(int q=0;q<width;++q)units[size_t(q)*c->s+(slots?targets[q]:2*targets[q]+1)]=1;
        TRY(cudaMemcpy(d.value,units.data(),nu*8,cudaMemcpyHostToDevice));
    }catch(const std::bad_alloc&){return -4;}
    multiply<<<dim3(c->r,width),128>>>(c->b,d.value,d.obj,0);
    TRY(cudaEventCreate(&d.start));TRY(cudaEventCreate(&d.end));TRY(cudaEventRecord(d.start));
    for(int k=0;k<steps;++k) {
        multiply<<<dim3(c->r,width),128>>>(c->b,d.u,d.grad,mode);
        primal<<<(nx+127)/128,128>>>(c->r,width,h,c->step,d.grad,d.obj,d.x,d.bar);
        multiply<<<dim3(c->s,width),128>>>(c->bt,d.bar,d.value,mode);
        dual<<<(nu+127)/128,128>>>(c->s,width,eps,c->step,d.value,d.u);
    }
    TRY(cudaGetLastError());TRY(cudaEventRecord(d.end));TRY(cudaEventSynchronize(d.end));
    float ms;TRY(cudaEventElapsedTime(&ms,d.start,d.end));*milliseconds=ms;
    TRY(cudaMemcpy(x,d.x,nx*8,cudaMemcpyDeviceToHost));
    TRY(cudaMemcpy(u,d.u,nu*8,cudaMemcpyDeviceToHost));return 0;
}
extern "C" int batch_propose(void* p,int width,const int* targets,double h,double eps,
    int steps,int mode,double* x,double* u,double* milliseconds) {
    return propose_indexed(p,width,targets,h,eps,steps,mode,x,u,milliseconds,false);
}
extern "C" int batch_propose_slots(void* p,int width,const int* targets,double h,double eps,
    int steps,int mode,double* x,double* u,double* milliseconds) {
    return propose_indexed(p,width,targets,h,eps,steps,mode,x,u,milliseconds,true);
}
