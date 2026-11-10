// ADR-0046: normalized expanded reconstruction, with FP64 guard metadata only.
// No FP64 rounded iterate is used in any product or update.
#include "expanded_compact_helpers.h"
#include "expanded_fast.h"
#include "expanded_storage.h"

__device__ __forceinline__ Value xr_add(Value a,Value b,U &guard) {
    U fast=0;return expanded_fma(a,Value{1ull<<63,-63,0},b,guard,fast);
}
__device__ __forceinline__ Value xr_mul(Value a,Value b,U &guard) {
    U fast=0;Value v=expanded_fma(a,b,Value{0,0,a.sign^b.sign},guard,fast);
    if(a.m&&b.m&&!v.m)guard|=4u;
    return v;
}
// Successor of a nearest nonnegative operation encloses its exact result.
// Identity cases match the retained CPU outward arithmetic.
__device__ __forceinline__ double xr_up(double x) {
    return x>=0.&&isfinite(x)?__longlong_as_double(__double_as_longlong(x)+1):__longlong_as_double(0x7ff0000000000000ull);
}
__device__ __forceinline__ double xr_add_up(double a,double b) {
    return a==0.?b:b==0.?a:xr_up(__dadd_rn(a,b));
}
__device__ __forceinline__ double xr_mul_up(double a,double b) {
    return a==0.||b==0.?0.:xr_up(__dmul_rn(a,b));
}
__device__ __forceinline__ double xr_div_up(double a,double b) {
    return a==0.?0.:xr_up(__ddiv_rn(a,b));
}
__device__ __forceinline__ double xr_abs_upper(Value x,U &guard) {
    if(!x.m)return 0.;
    // Guard metadata permits rounding to zero; its successor still encloses x.
    Value f=rounded<53>(from_words(x.m,0,0),x.e,0,guard);
    W bits=f.m<(1ull<<52)?f.m:((W)(f.e+1075)<<52)|(f.m&0xfffffffffffffull);
    double upper=__longlong_as_double(bits+1);
    if(!isfinite(upper))guard|=8u;
    return upper;
}

extern "C" __global__ void xe_abs_blocks(ExpandedConst input,double *blocks,
    U *control,U count) {
    __shared__ double values[128];
    U lane=threadIdx.x,i=blockIdx.x*blockDim.x+lane,guard=0;
    double v=i<count?xr_abs_upper(expanded_load(input,i,guard),guard):0.;
    if(guard)atomicOr(control,guard);
    values[lane]=v;__syncthreads();
    for(U stride=64;stride;stride>>=1){if(lane<stride)values[lane]=fmax(values[lane],values[lane+stride]);__syncthreads();}
    if(!lane)blocks[blockIdx.x]=values[0];
}
extern "C" __global__ void xe_abs_finish(const double *blocks,double *norm,U count) {
    if(blockIdx.x||threadIdx.x)return;
    double maximum=0.;for(U i=0;i<count;i++)maximum=fmax(maximum,blocks[i]);
    norm[0]=maximum;norm[1]=0.;norm[2]=1.;
}

// Traversal is exactly line -> group -> stored ids, as in the CPU oracle.
// Matrix representation and coefficient-error constants remain source-bound.
extern "C" __global__ void xe_reconstruct(
    const W *original,const W *represented,ExpandedConst residual,
    const W *packed,const U *line,const U *group,const U *tiles,const U *ids,
    const U *inputs,const int *selected,const U *promoted,const double *constants,
    double *errors,const double *scales,ExpandedConst input,ExpandedOut output,
    const double *norm,U *control,U *flags,W *stats,ExpandedConst parts,
    const U *part_flags,U count,U start) {
    U i=blockIdx.x*blockDim.x+threadIdx.x;if(i>=count)return;
    U row=start+i,guard=control[0];Value total={0,0,0};
    W low_count=0,high_count=0,nonzero=0,residual_count=0;
    if(guard){flags[row]=guard;return;}
    for(U g=line[row];g<line[row+1];g++){
        U tile=tiles[g];bool low=!promoted[tile];
        Value sum={0,0,0},correction={0,0,0};
        if(low){
            if(selected[tile]<0){guard|=8u;break;}
            U at=(U)selected[tile]*32+i%32;
            guard|=part_flags[at];sum=expanded_load(parts,at,guard);
        }
        for(U k=group[g];k<group[g+1];k++){
            U id=ids[k],index=inputs[k];
            if(low){
                low_count++;if(packed[index])nonzero++;
                Value tail=expanded_load(residual,index,guard);
                if(tail.m){
                    residual_count++;
                    Value coefficient=expanded_from_fp64(represented[id],guard);
                    Value product=xr_mul(coefficient,tail,guard);
                    correction=xr_add(correction,product,guard);
                }
            }else{
                high_count++;
                Value coefficient=expanded_from_fp64(original[id],guard);
                Value x=expanded_load(input,index,guard);
                Value product=xr_mul(coefficient,x,guard);
                sum=xr_add(sum,product,guard);
            }
        }
        if(low)sum=xr_add(sum,correction,guard);
        total=xr_add(total,sum,guard);
    }
    double scaled=xr_add_up(xr_mul_up(constants[3*row],norm[0]),constants[3*row+2]);
    double original_bound=xr_add_up(xr_div_up(scaled,scales[row]),__longlong_as_double(1));
    if(!(original_bound<=1.e-7))guard|=1u;
    errors[row]=scaled;flags[row]=guard;
    if(guard)atomicOr(control,guard);else expanded_store(output,i,total);
    W *s=stats+7*row;s[0]+=low_count;s[1]+=high_count;s[2]+=nonzero;s[6]+=residual_count;
    if(original_bound<=1.e-7)s[3]++;else s[5]++;
}
