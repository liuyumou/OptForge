// ADR-0035 separate image; legacy source/images are unchanged.
// Native FP64 vector updates are explicitly outside the exact sparse path.
#include "../lp_pdhg_precision/lp_pdhg_precision.cu"
using U = unsigned int;
using W = unsigned long long;
struct ExecDecoded { W m; int e; U negative; };
struct ExecAcc { U v[8]; };
__device__ __forceinline__ ExecDecoded exec_decode(W bits,U &g) {
    U field=(U)(bits>>52)&2047u; W m=bits&0xfffffffffffffull; int e=-1074;
    if(field==2047u){g|=1u;return {0,0,0};}
    if(field){m|=1ull<<52;e=(int)field-1075;}
    if(m){int s=__clzll(m)-11;m<<=s;e-=s;}else e=0;
    return {m,e,(U)(bits>>63)};
}
__device__ __forceinline__ U exec_word(const ExecAcc &a,int i){
    U out=0;
    #pragma unroll
    for(int k=0;k<8;k++)if(i==k)out=a.v[k];
    return out;
}
__device__ __forceinline__ bool exec_bit(const ExecAcc &a,int k){return k>=0&&k<256&&((exec_word(a,k/32)>>(k%32))&1u);}
__device__ __forceinline__ bool exec_below(const ExecAcc &a,int k){
    U any=0;
    #pragma unroll
    for(int i=0;i<8;i++){int count=k-32*i;U mask=count>=32?~0u:(count<=0?0u:((1u<<count)-1));any|=a.v[i]&mask;}
    return any!=0;
}
__device__ __forceinline__ void exec_add(ExecAcc &a,const ExecAcc &b){
    W carry=0;
    #pragma unroll
    for(int i=0;i<8;i++){W v=(W)a.v[i]+b.v[i]+carry;a.v[i]=(U)v;carry=v>>32;}
}
__device__ __forceinline__ void exec_negate(ExecAcc &a){
    W carry=1;
    #pragma unroll
    for(int i=0;i<8;i++){W v=(W)(~a.v[i])+carry;a.v[i]=(U)v;carry=v>>32;}
}
__device__ __forceinline__ U exec_product_word(W lo,W hi,int k){return k==0?(U)lo:k==1?(U)(lo>>32):k==2?(U)hi:k==3?(U)(hi>>32):0u;}
__device__ __forceinline__ ExecAcc exec_product(ExecDecoded a,ExecDecoded b,int base){
    W lo=a.m*b.m,hi=__umul64hi(a.m,b.m);int shift=a.e+b.e-base,word=shift/32,rem=shift%32;
    ExecAcc p;
    #pragma unroll
    for(int k=0;k<8;k++)p.v[k]=(exec_product_word(lo,hi,k-word)<<rem)|(rem?exec_product_word(lo,hi,k-word-1)>>(32-rem):0u);
    if(a.negative!=b.negative)exec_negate(p);
    return p;
}
__device__ __forceinline__ W exec_round(ExecAcc a,int base,U &g,U &flags,int &error){
    bool negative=(a.v[7]>>31)!=0;if(negative)exec_negate(a);
    int top=-1;
    #pragma unroll
    for(int k=0;k<8;k++)if(a.v[k])top=32*k+31-__clz(a.v[k]);
    if(top<0){error=2147483647;flags=0;return 0;}
    int unit=max(base+top-52,-1074),shift=unit-base;
    W m;
    if(shift<0)m=((W)a.v[0]|((W)a.v[1]<<32))<<(-shift);
    else {
        int word=shift/32,rem=shift%32;
        W low=(W)exec_word(a,word)|((W)exec_word(a,word+1)<<32);
        m=(low>>rem)|(rem?(W)exec_word(a,word+2)<<(64-rem):0ull);
    }
    m&=(1ull<<53)-1;
    bool inexact=exec_below(a,shift);
    if(exec_bit(a,shift-1)&&(exec_below(a,shift-1)||(m&1)))m++;
    if(m==(1ull<<53)){m>>=1;unit++;}
    if(unit>971){g|=4u;error=2147483647;return 0;}
    W magnitude=m<(1ull<<52)?m:((W)(unit+1075)<<52)|(m&0xfffffffffffffull);
    bool tiny=magnitude<(1ull<<52);
    flags=(inexact?1u:0u)|((tiny&&m)?2u:0u)|((tiny&&inexact)?4u:0u);
    error=inexact?unit-1:2147483647;
    return magnitude|((W)negative<<63);
}
extern "C" __global__ void exec_prepare(const W* x,ExecDecoded* out,U* guards,U n){
    U i=blockIdx.x*blockDim.x+threadIdx.x;if(i>=n)return;
    U g=0;out[i]=exec_decode(x[i],g);guards[i]|=g;
}
template<bool Cached> __device__ __forceinline__ void exec_sparse(
 const W* values,const U* indices,const U* offsets,const U* permutation,const W* x,
 const ExecDecoded* cached,W* out,U* guards,U* flags,int* errors,U lines,U transpose){
    U row=(blockIdx.x*blockDim.x+threadIdx.x)/32,lane=threadIdx.x&31;
    if(row>=lines)return;
    int low=2147483647,high=-2147483647;U g=0;
    for(U k=offsets[row]+lane;k<offsets[row+1];k+=32){
        ExecDecoded a=exec_decode(values[transpose?permutation[k]:k],g);
        ExecDecoded b;
        if constexpr(Cached)b=cached[indices[k]];else b=exec_decode(x[indices[k]],g);
        if(a.m&&b.m){int e=a.e+b.e;low=min(low,e);high=max(high,e);}
    }
    #pragma unroll
    for(int k=16;k;k>>=1){low=min(low,__shfl_xor_sync(0xffffffffu,low,k));high=max(high,__shfl_xor_sync(0xffffffffu,high,k));g|=__shfl_xor_sync(0xffffffffu,g,k);}
    bool empty=low==2147483647;
    if(!empty&&high-low>128)g|=2u;
    if(offsets[row+1]-offsets[row]>65536u)g|=8u;
    ExecAcc sum={{0,0,0,0,0,0,0,0}};
    if(!g&&!empty)for(U k=offsets[row]+lane;k<offsets[row+1];k+=32){
        ExecDecoded a=exec_decode(values[transpose?permutation[k]:k],g);
        ExecDecoded b;
        if constexpr(Cached)b=cached[indices[k]];else b=exec_decode(x[indices[k]],g);
        if(a.m&&b.m)exec_add(sum,exec_product(a,b,low));
    }
    #pragma unroll
    for(int k=16;k;k>>=1){
        ExecAcc other;
        #pragma unroll
        for(int i=0;i<8;i++)other.v[i]=__shfl_down_sync(0xffffffffu,sum.v[i],k);
        if(lane<(U)k)exec_add(sum,other);
    }
    if(lane==0){U f=0;int e=2147483647;W bits=g||empty?0:exec_round(sum,low,g,f,e);out[row]=bits;guards[row]|=g;flags[row]|=f;errors[row]=e;}
}
#define EXEC_ENTRY(Name,Cached) extern "C" __global__ void Name(const W* a,const U* i,const U* o,const U* p,const W* x,const ExecDecoded* c,W* y,U* g,U* f,int* e,U n,U t){exec_sparse<Cached>(a,i,o,p,x,c,y,g,f,e,n,t);}
EXEC_ENTRY(exec_cached,true)
EXEC_ENTRY(exec_uncached,false)
