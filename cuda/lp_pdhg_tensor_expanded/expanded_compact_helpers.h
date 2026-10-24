// Generated exact helper sections; see helper-source-v1.json.
// GPUP-STATE compile-only resource admission. No host launcher or runtime linkage.
// Straight-line integer restoring division/root construction on the proposed
// exact 320-bit reduction intermediate. Other constructions require a new probe.
using U = unsigned int;
struct Wide { U w[10]; };
__device__ __forceinline__ Wide zero() { return {{0,0,0,0,0,0,0,0,0,0}}; }
__device__ __forceinline__ U word(const Wide &a,int index) {
    U result=0;
    #pragma unroll
    for(int k=0;k<10;k++) if(index==k) result=a.w[k];
    return result;
}
__device__ __forceinline__ U bit(const Wide &a,int index) {
    return (word(a,index/32)>>(index%32))&1u;
}
__device__ __forceinline__ void shift(Wide &a,int count) {
    #pragma unroll
    for(int k=9;k>=0;k--) a.w[k]=(a.w[k]<<count)|(k?a.w[k-1]>>(32-count):0u);
}
__device__ __forceinline__ bool greater_equal(const Wide &a,const Wide &b) {
    bool equal=true,greater=false;
    #pragma unroll
    for(int k=9;k>=0;k--) { greater|=equal&&(a.w[k]>b.w[k]); equal&=a.w[k]==b.w[k]; }
    return greater||equal;
}
__device__ __forceinline__ void subtract(Wide &a,const Wide &b) {
    unsigned long long borrow=0;
    #pragma unroll
    for(int k=0;k<10;k++) {
        unsigned long long rhs=(unsigned long long)b.w[k]+borrow;
        U out=(U)((unsigned long long)a.w[k]-rhs);
        borrow=(unsigned long long)a.w[k]<rhs;a.w[k]=out;
    }
}
using W=unsigned long long;
struct Value { W m;int e;U sign; };
__device__ __forceinline__ int top(const Wide &a) {
    int result=-1;
    #pragma unroll
    for(int k=0;k<10;k++)if(a.w[k])result=32*k+31-__clz(a.w[k]);
    return result;
}
__device__ __forceinline__ bool below(const Wide &a,int position) {
    U result=0;
    #pragma unroll
    for(int k=0;k<10;k++) {
        int count=position-32*k;
        U mask=count>=32?~0u:(count<=0?0u:((1u<<count)-1u));
        result|=a.w[k]&mask;
    }
    return result!=0;
}
__device__ __forceinline__ Wide from_words(W lo,W hi,int offset) {
    Wide result=zero();int base=offset/32,rem=offset%32;
    U source[4]={(U)lo,(U)(lo>>32),(U)hi,(U)(hi>>32)};
    #pragma unroll
    for(int k=0;k<10;k++) {
        U a=0,b=0;
        #pragma unroll
        for(int j=0;j<4;j++){if(j==k-base)a=source[j];if(j==k-base-1)b=source[j];}
        result.w[k]=(a<<rem)|(rem?b>>(32-rem):0u);
    }
    return result;
}
__device__ __forceinline__ void increment(Wide &a) {
    W carry=1;
    #pragma unroll
    for(int k=0;k<10;k++){W sum=(W)a.w[k]+carry;a.w[k]=(U)sum;carry=sum>>32;}
}
__device__ __forceinline__ void plus(Wide &a,const Wide &b) {
    W carry=0;
    #pragma unroll
    for(int k=0;k<10;k++){W sum=(W)a.w[k]+b.w[k]+carry;a.w[k]=(U)sum;carry=sum>>32;}
}
template<int P> __device__ __forceinline__ Value rounded(Wide a,int exponent,U sign,U &guard) {
    int highest=top(a);if(highest<0)return {0,0,sign};
    int unit=max(exponent+highest-(P-1),-1022-(P-1));
    int shift_bits=unit-exponent;
    W significand=0;
    #pragma unroll
    for(int k=0;k<P;k++)if(k+shift_bits>=0&&k+shift_bits<320)significand|=(W)bit(a,k+shift_bits)<<k;
    bool carry=false;
    if(shift_bits>0&&bit(a,shift_bits-1)&&(below(a,shift_bits-1)||(significand&1u))) {
        W previous=significand;significand++;
        carry=significand<previous;
    }
    bool too_wide=carry;
    if constexpr(P<64)too_wide|=significand==(1ull<<P);
    if(too_wide){significand=1ull<<(P-1);unit++;}
    if(unit>1023-(P-1)){guard|=2u;return {0,0,sign};}
    return {significand,significand?unit:0,sign};
}
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

