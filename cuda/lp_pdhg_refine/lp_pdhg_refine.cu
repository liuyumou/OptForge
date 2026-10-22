// ADR-0037: one canonical sparse A, transpose permutation and implicit activity block.
// FP64 updates/control are host owned. No atomics and no context outside the lease.
#include <cuda_runtime.h>
#include <math.h>
extern "C" __global__ void refine_product(
    const double* coefficient,const float* coefficient32,const unsigned* offsets,const unsigned* indices,
    const unsigned* permutation,const double* diagonal,const double* input,
    double* output,unsigned* guards,unsigned count,unsigned original_columns,
    unsigned transpose,unsigned width32) {
    unsigned line=(blockIdx.x*blockDim.x+threadIdx.x)/32;
    unsigned lane=threadIdx.x%32;
    if(line>=count)return;
    double sum64=0.0;float sum32=0.0f;unsigned bad=0;
    if(!transpose || line<original_columns){
        for(unsigned t=offsets[line]+lane;t<offsets[line+1];t+=32){
            unsigned k=transpose?permutation[t]:t;double b=input[indices[t]];
            if(width32){
                float af=coefficient32[k],bf=(float)b;
                if(!isfinite(af)||!isfinite(bf)||(b!=0.0&&bf==0.0f))bad=1;
                float product=af*bf;
                if(!isfinite(product)||(af!=0.0f&&bf!=0.0f&&product==0.0f))bad=1;
                sum32=sum32+product;
            }else{
                double a=coefficient[k];double product=a*b;
                if(!isfinite(product)||(a!=0.0&&b!=0.0&&product==0.0))bad=1;
                sum64=sum64+product;
            }
        }
    }
    for(unsigned d=16;d;d>>=1){
        if(width32)sum32=sum32+__shfl_down_sync(0xffffffff,sum32,d);
        else sum64=sum64+__shfl_down_sync(0xffffffff,sum64,d);
        bad|=__shfl_down_sync(0xffffffff,bad,d);
    }
    if(lane==0){
        double result=width32?(double)sum32:sum64;
        if(transpose && line>=original_columns){unsigned i=line-original_columns;double product=diagonal[i]*input[i];if(!isfinite(product)||(diagonal[i]!=0.0&&input[i]!=0.0&&product==0.0))bad=1;result=result+product;}
        else if(!transpose){double product=diagonal[line]*input[original_columns+line];if(!isfinite(product)||(diagonal[line]!=0.0&&input[original_columns+line]!=0.0&&product==0.0))bad=1;result=result+product;}
        if(!isfinite(result))bad=1;
        output[line]=result;guards[line]=bad;
    }
}
