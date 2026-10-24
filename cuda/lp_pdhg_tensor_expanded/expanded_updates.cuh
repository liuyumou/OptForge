// Fused normalized update primitives. Error-enclosure guards and publication
// remain separate prerequisites: these kernels only write private working SoAs.
__device__ __forceinline__ Value xmul(Value a,Value b,U &guard) {
    U fast=0;Value z={0,0,a.sign^b.sign};
    Value v=expanded_fma(a,b,z,guard,fast);
    if(a.m&&b.m&&!v.m)guard|=4u;
    return v;
}
__device__ __forceinline__ Value xadd(Value a,Value b,U &guard) {
    U fast=0;return expanded_fma(a,Value{1ull<<63,-63,0},b,guard,fast);
}
__device__ __forceinline__ Value xsub(Value a,Value b,U &guard) {
    b.sign^=1u;return xadd(a,b,guard);
}
__device__ __forceinline__ Value xproject(Value v,W lower,W upper,U &guard) {
    U lf=(U)(lower>>52)&2047u,uf=(U)(upper>>52)&2047u;
    Value lo={0,0,0},hi={0,0,0};
    if(lf==2047u) {if(lower!=0xfff0000000000000ull)guard|=8u;}
    else lo=expanded_from_fp64(lower,guard);
    if(uf==2047u) {if(upper!=0x7ff0000000000000ull)guard|=8u;}
    else hi=expanded_from_fp64(upper,guard);
    if(lf!=2047u&&uf!=2047u&&expanded_less(hi,lo))guard|=8u;
    if(lf!=2047u&&expanded_less(v,lo))v=lo;
    if(uf!=2047u&&expanded_less(hi,v))v=hi;
    return v;
}

extern "C" __global__ void xe_primal_update(
    ExpandedConst primal,ExpandedConst product,ExpandedConst anchor,
    const W *objective,const W *lower,const W *upper,const Value *coefficients,
    ExpandedOut next,ExpandedOut extrapolated,U *guards,U count) {
    U i=blockIdx.x*blockDim.x+threadIdx.x;if(i>=count)return;
    U guard=0;
    Value x=expanded_load(primal,i,guard);
    Value aty=expanded_load(product,i,guard);
    Value c=expanded_from_fp64(objective[i],guard);
    Value diff=xsub(c,aty,guard);
    Value change=xmul(coefficients[0],diff,guard);
    Value projected=xproject(xsub(x,change,guard),lower[i],upper[i],guard);
    Value bar=xsub(xmul(Value{1ull<<63,-62,0},projected,guard),x,guard);
    Value a=expanded_load(anchor,i,guard);
    Value left=xmul(coefficients[2],projected,guard);
    Value right=xmul(coefficients[3],a,guard);
    Value out=xadd(left,right,guard);
    guards[i]=guard;
    if(!guard){expanded_store(next,i,out);expanded_store(extrapolated,i,bar);}
}

extern "C" __global__ void xe_dual_update(
    ExpandedConst dual,ExpandedConst product,ExpandedConst anchor,
    const W *row_lower,const W *row_upper,const Value *coefficients,
    ExpandedOut next,U *guards,U count) {
    U i=blockIdx.x*blockDim.x+threadIdx.x;if(i>=count)return;
    U guard=0;
    Value step=coefficients[1];
    if(!step.m||step.sign){guards[i]=8u;return;}
    Value y=expanded_load(dual,i,guard);
    Value ax=expanded_load(product,i,guard);
    Value raw=xsub(y,xmul(step,ax,guard),guard);
    W lower=row_upper[i]^(1ull<<63),upper=row_lower[i]^(1ull<<63);
    U lf=(U)(lower>>52)&2047u,uf=(U)(upper>>52)&2047u;
    Value lo={0,0,0},hi={0,0,0};
    if(lf==2047u){if(lower!=0xfff0000000000000ull)guard|=8u;}
    else lo=xmul(step,expanded_from_fp64(lower,guard),guard);
    if(uf==2047u){if(upper!=0x7ff0000000000000ull)guard|=8u;}
    else hi=xmul(step,expanded_from_fp64(upper,guard),guard);
    if(lf!=2047u&&uf!=2047u&&expanded_less(hi,lo))guard|=8u;
    Value clamp=raw;
    if(lf!=2047u&&expanded_less(clamp,lo))clamp=lo;
    if(uf!=2047u&&expanded_less(hi,clamp))clamp=hi;
    Value projected=xsub(raw,clamp,guard);
    Value a=expanded_load(anchor,i,guard);
    Value left=xmul(coefficients[2],projected,guard);
    Value right=xmul(coefficients[3],a,guard);
    Value out=xadd(left,right,guard);
    guards[i]=guard;if(!guard)expanded_store(next,i,out);
}

// Full u64 magnitudes and independent signs; no signed-i64 truncation.
extern "C" __global__ void xe_pack64(
    ExpandedConst input,W *magnitude,U *sign,int *exponents,ExpandedOut residual,
    U *guards,U *control,U count) {
    U i=blockIdx.x*blockDim.x+threadIdx.x;
    U padded=(count+31u)&~31u;if(i>=padded)return;
    U guard=0;Value x=i<count?expanded_load(input,i,guard):Value{0,0,0};
    int e=x.m?x.e+64-__clzll(x.m):-1085;
#pragma unroll
    for(int offset=1;offset<32;offset*=2)e=max(e,__shfl_xor_sync(0xffffffffu,e,offset));
    if((i&31u)==0)exponents[i/32]=e;
    W q=0,tail=0;
    if(x.m) {
        int shift=x.e-e+64;
        if(shift>=0) {
            if(shift>=64||64-__clzll(x.m)+shift>64)guard|=8u;
            else q=x.m<<shift;
        } else {
            int distance=-shift;
            q=distance>=64?0:x.m>>distance;
            tail=distance>=64?x.m:x.m&((1ull<<distance)-1);
        }
    }
    Value r=rounded<64>(from_words(tail,0,0),x.e,x.sign,guard);
    guards[i]=guard;
    if(guard){atomicOr(control,guard);return;}
    magnitude[i]=q;sign[i]=x.sign;expanded_store(residual,i,r);
}
