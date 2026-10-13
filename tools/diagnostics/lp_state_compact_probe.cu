// PR 19 CPU/compile-only alternative. Not a runtime image or device acceptance.
// ADR-0036 records the proof and separately bounded experiment contract.
#include "lp_state_integer_probe.cu"

// Right shift an unsigned 128-bit value and retain a nonzero discarded tail as
// an odd low bit. Every shift count is guarded, including exactly 64 and 128.
__device__ __forceinline__ Wide compact_words(W lo,W hi,int offset) {
    if(offset>=0)return from_words(lo,hi,offset);
    int distance=-offset;
    bool sticky;
    if(distance<64) {
        sticky=(lo&((1ull<<distance)-1))!=0;
        lo=(lo>>distance)|(hi<<(64-distance));hi>>=distance;
    } else if(distance==64) {
        sticky=lo!=0;lo=hi;hi=0;
    } else if(distance<128) {
        sticky=lo||(hi&((1ull<<(distance-64))-1));
        lo=hi>>(distance-64);hi=0;
    } else {
        sticky=lo||hi;lo=0;hi=0;
    }
    lo|=(W)sticky;
    return from_words(lo,hi,0);
}

template<int P> __device__ __forceinline__ Value compact_fma(Value a,Value b,Value c,U &guard) {
    bool nonzero_product=a.m&&b.m;
    int pe=nonzero_product?a.e+b.e:c.e,ce=c.m?c.e:pe;
    int base=max(pe,ce)-160;
    Wide left=compact_words(a.m*b.m,__umul64hi(a.m,b.m),pe-base);
    Wide right=compact_words(c.m,0,ce-base);
    U product_sign=a.sign^b.sign;
    if(product_sign==c.sign) {
        plus(left,right);
        return rounded<P>(left,base,product_sign,guard);
    }
    if(greater_equal(left,right)) {
        subtract(left,right);
        return rounded<P>(left,base,top(left)<0?0:product_sign,guard);
    }
    subtract(right,left);
    return rounded<P>(right,base,c.sign,guard);
}

template<int P> __device__ __forceinline__ void compact_probe(
    const Value* input,Value* output,U* guards,U count) {
    U index=blockIdx.x*blockDim.x+threadIdx.x;if(index>=count)return;
    U guard=0;
    Value result=compact_fma<P>(input[3*index],input[3*index+1],input[3*index+2],guard);
    guards[index]=guard;if(!guard)output[index]=result;
}
extern "C" __global__ void state_compact_fma_p48(const Value* a,Value* b,U* g,U n){compact_probe<48>(a,b,g,n);}
extern "C" __global__ void state_compact_fma_p64(const Value* a,Value* b,U* g,U n){compact_probe<64>(a,b,g,n);}
