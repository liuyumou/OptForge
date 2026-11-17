// SPEC-0045: rectangular sparse single-vector products. Explicit compilation only.
// FP4 storage/components, FP32 increment arithmetic, FP64 state and references.
#include <cuda_runtime.h>
#include <stdint.h>
#include <math.h>
namespace general {
constexpr int WARPS=8;
__device__ double add(double a,double b){return __dadd_ru(a,b);}
__device__ double mul(double a,double b){return __dmul_ru(a,b);}
__device__ double gamma(unsigned count,double u){double x=mul(double(count),u);return __ddiv_ru(x,__dsub_rd(1.,x));}
__device__ double maximum(double v){for(int d=16;d;d>>=1)v=fmax(v,__shfl_down_sync(0xffffffff,v,d));return v;}
__device__ float fp4(unsigned code){float a[8]={0,.5f,1,1.5f,2,3,4,6};return (code&8)?-a[code&7]:a[code&7];}
__device__ void summary(double value,double anchor,float* delta,double* stat){
    double d=__dsub_rn(value,anchor);float f=__double2float_rn(d);*delta=f;
    double round=add(mul(0x1p-52,add(fabs(value),fabs(anchor))),0x1p-1000);
    stat[0]=add(fabs(d),round);stat[1]=add(fabs(__dsub_rn(d,double(f))),round);
    stat[2]=fabs(double(f));stat[3]=fabs(anchor);
}
__device__ void publish_stats(double* output,const double* values){
    // Each warp's first lane publishes one vector element's four summaries.
    __shared__ double shared[WARPS*4];int w=threadIdx.x/32,l=threadIdx.x%32;
    if(!l)for(int q=0;q<4;q++)shared[4*w+q]=values[q];__syncthreads();
    if(!threadIdx.x)for(int q=0;q<4;q++){double v=0;for(int j=0;j<WARPS;j++)v=fmax(v,shared[4*j+q]);output[4*blockIdx.x+q]=v;}
}
}
extern "C" __global__ void general_encode(const double* x,const double* anchor,float* delta,double* stats,unsigned n){
    unsigned i=blockIdx.x*general::WARPS+threadIdx.x/32;double s[4]={0,0,0,0};
    if(!(threadIdx.x%32)&&i<n)general::summary(x[i],anchor[i],delta+i,s);
    general::publish_stats(stats,s);
}
extern "C" __global__ void general_summary(const double* stats,double* out,unsigned blocks){
    __shared__ double partial[general::WARPS*4];int lane=threadIdx.x%32,warp=threadIdx.x/32;
    for(int q=0;q<4;q++){
        double v=0;for(unsigned j=threadIdx.x;j<blocks;j+=blockDim.x)v=fmax(v,stats[4*j+q]);
        v=general::maximum(v);if(!lane)partial[warp*4+q]=v;__syncthreads();
        if(!threadIdx.x){v=0;for(int w=0;w<general::WARPS;w++)v=fmax(v,partial[w*4+q]);out[q]=v;}__syncthreads();
    }
}
extern "C" __global__ void general_copy(const double* x,double* y,unsigned n){unsigned i=blockIdx.x*blockDim.x+threadIdx.x;if(i<n)y[i]=x[i];}
extern "C" __global__ void general_reference(const unsigned* offsets,const unsigned* indices,const double* values,const double* x,double* out,double* error,unsigned rows){
    unsigned row=blockIdx.x*general::WARPS+threadIdx.x/32,lane=threadIdx.x%32;
    double sum=0,absolute=0;unsigned begin=row<rows?offsets[row]:0,end=row<rows?offsets[row+1]:0;
    for(unsigned j=begin+lane;j<end;j+=32){double v=values[j]*x[indices[j]];sum=__dadd_rn(sum,v);absolute=general::add(absolute,fabs(v));}
    for(int d=16;d;d>>=1){sum=__dadd_rn(sum,__shfl_down_sync(0xffffffff,sum,d));absolute=general::add(absolute,__shfl_down_sync(0xffffffff,absolute,d));}
    if(!lane&&row<rows){out[row]=sum;error[row]=general::add(general::mul(general::gamma(2*(end-begin)+32,0x1p-52),absolute),0x1p-1000);}
}
// mode: 0 native; 1 FP32; 2 FP4x1; 3 FP4x2. direction: 0 primal, 1 dual, 2 probe.
extern "C" __global__ void general_step(
    const unsigned* offsets,const unsigned* indices,const unsigned* ids,const double* original,
    const unsigned char* codes,const int* exponents,const float* fp32,const float* delta,
    const double* summary,const double* meta,const double* reference,const double* reference_error,
    const double* input,double* state,double* extra,const double* ref_anchor,const double* controller_anchor,
    const double* lower,const double* upper,const double* objective,
    float* output_delta,double* output_stats,unsigned* flags,double* product,double* bound,
    unsigned rows,unsigned mode,unsigned direction,double step,double toward,double back,double limit){
    unsigned row=blockIdx.x*general::WARPS+threadIdx.x/32,lane=threadIdx.x%32;
    unsigned begin=row<rows?offsets[row]:0,end=row<rows?offsets[row+1]:0;
    double exact=0;float sum=0;
    for(unsigned j=begin+lane;j<end;j+=32){
        unsigned column=indices[j];
        if(!mode)exact=__dadd_rn(exact,__dmul_rn(original[j],input[column]));
        else{
            unsigned q=ids[j];float v=delta[column];
            if(mode==1)sum=__fadd_rn(sum,__fmul_rn(fp32[q],v));
            else{
                unsigned code=codes[q];int block=q/32;
                float a=ldexpf(general::fp4(code&15),exponents[2*block]);
                sum=__fadd_rn(sum,__fmul_rn(a,v));
                if(mode==3){a=ldexpf(general::fp4(code>>4),exponents[2*block+1]);sum=__fadd_rn(sum,__fmul_rn(a,v));}
            }
        }
    }
    for(int d=16;d;d>>=1){exact=__dadd_rn(exact,__shfl_down_sync(0xffffffff,exact,d));sum=__fadd_rn(sum,__shfl_down_sync(0xffffffff,sum,d));}
    double stats[4]={0,0,0,0};
    if(!lane&&row<rows){
        double value=mode?__dadd_rn(reference[row],double(sum)):exact;
        double enclosure=0;
        if(mode){
            enclosure=general::add(reference_error[row],general::mul(meta[3*row],summary[0]));
            enclosure=general::add(enclosure,general::mul(meta[3*row+1],summary[1]));
            enclosure=general::add(enclosure,general::mul(meta[3*row+2],summary[2]));
            enclosure=general::add(enclosure,general::mul(double(4*(end-begin)+32),0x1p-149));
            enclosure=general::add(enclosure,general::add(general::mul(0x1p-52,general::add(fabs(reference[row]),fabs(double(sum)))),0x1p-1000));
        }
        // An empty dot product is exactly zero. Generic underflow allowances
        // must not reject a stationary zero operator with a zero local budget.
        if(begin==end){value=0.;enclosure=0.;}
        if(direction==2){product[row]=value;bound[row]=enclosure;}
        bool bad=!isfinite(value)||!isfinite(enclosure)||(mode&&general::mul(step,enclosure)>limit);
        if(direction<2){
            double old=state[row],next;
            if(direction==0){next=fmin(upper[row],fmax(lower[row],old-step*(objective[row]-value)));extra[row]=2*next-old;}
            else {double raw=old-step*value;next=raw-step*fmin(-lower[row],fmax(-upper[row],raw/step));}
            double blended=toward*next+back*controller_anchor[row];
            bad=bad||!isfinite(blended)||(direction==0&&!isfinite(extra[row]));
            bad=bad||(mode&&(fabs(blended)>0x1p40||(direction==0&&fabs(extra[row])>0x1p40)));
            if(!bad){state[row]=blended;if(mode)general::summary(direction==0?extra[row]:blended,ref_anchor[row],output_delta+row,stats);}
        }
        flags[row]|=bad?1:0;
    }
    if(direction<2&&mode)general::publish_stats(output_stats,stats);
}
