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
__device__ __forceinline__ Wide divide(Wide numerator,const Wide &denominator,Wide &remainder) {
    Wide quotient=zero();remainder=zero();
    for(int index=319;index>=0;index--) {
        shift(remainder,1);remainder.w[0]|=bit(numerator,index);
        if(greater_equal(remainder,denominator)) {
            subtract(remainder,denominator);
            #pragma unroll
            for(int k=0;k<10;k++) if(k==index/32) quotient.w[k]|=1u<<(index%32);
        }
    }
    return quotient;
}
__device__ __forceinline__ Wide root(const Wide &radicand,Wide &remainder) {
    Wide result=zero();remainder=zero();
    for(int index=159;index>=0;index--) {
        shift(remainder,2);
        remainder.w[0]|=(bit(radicand,2*index+1)<<1)|bit(radicand,2*index);
        Wide trial=result;shift(trial,2);trial.w[0]|=1u;
        bool accept=greater_equal(remainder,trial);
        if(accept)subtract(remainder,trial);
        shift(result,1);result.w[0]|=(U)accept;
    }
    return result;
}
template<int Precision> __device__ __forceinline__ void probe(
    const U* input,U* output,U* guards,U count,U operation) {
    U index=blockIdx.x*blockDim.x+threadIdx.x;if(index>=count)return;
    Wide a,b;
    #pragma unroll
    for(int k=0;k<10;k++) { a.w[k]=input[20*index+k];b.w[k]=input[20*index+10+k]; }
    U any=0;
    #pragma unroll
    for(int k=0;k<10;k++)any|=b.w[k];
    if(operation==1&&!any){guards[index]=1;return;}
    Wide remainder;
    Wide result=operation==1?divide(a,b,remainder):root(a,remainder);
    // Retain full integer output/remainder: correct rounding is a later boundary.
    // Precision identifies which controller format's resource gate this probes.
    #pragma unroll
    for(int k=0;k<10;k++) {output[20*index+k]=result.w[k];output[20*index+10+k]=remainder.w[k];}
    guards[index]=Precision;
}
extern "C" __global__ void state_integer_p48(const U* a,U* b,U* g,U n,U op){probe<48>(a,b,g,n,op);}
extern "C" __global__ void state_integer_p64(const U* a,U* b,U* g,U n,U op){probe<64>(a,b,g,n,op);}

// The state-update construction uses the same exact integer helpers. Its
// intermediates are normalized at each declared primitive boundary. Zero,
// overflow and range outcomes are explicit; no native floating-point operation
// is used. This remains compile-only admission code, not an admitted image.
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
template<int P> __device__ __forceinline__ Value mul_value(Value a,Value b,U &guard) {
    return rounded<P>(from_words(a.m*b.m,__umul64hi(a.m,b.m),0),a.e+b.e,a.sign^b.sign,guard);
}
template<int P> __device__ __forceinline__ Value add_value(Value a,Value b,U &guard) {
    if(!a.m&&!b.m)return {0,0,a.sign&b.sign};
    if(!a.m)return b;if(!b.m)return a;
    int base=min(a.e,b.e),sa=a.e-base,sb=b.e-base;
    if(sa>256||sb>256){guard|=4u;return {0,0,0};}
    Wide left=from_words(a.m,0,sa),right=from_words(b.m,0,sb);
    if(a.sign==b.sign){plus(left,right);return rounded<P>(left,base,a.sign,guard);}
    if(greater_equal(left,right)){subtract(left,right);return rounded<P>(left,base,top(left)<0?0:a.sign,guard);}
    subtract(right,left);return rounded<P>(right,base,b.sign,guard);
}
template<int P> __device__ __forceinline__ Value div_value(Value a,Value b,U &guard) {
    if(!b.m){guard|=1u;return {0,0,0};}
    if(!a.m)return {0,0,a.sign^b.sign};
    int exact_top=63-__clzll(a.m)-(63-__clzll(b.m));
    // Quotient magnitude top is determined exactly with aligned integer words.
    Wide numerator=from_words(a.m,0,max(0,-exact_top));
    Wide denominator=from_words(b.m,0,max(0,exact_top));
    if(!greater_equal(numerator,denominator))exact_top--;
    int unit=max(exact_top+a.e-b.e-(P-1),-1022-(P-1));
    if(unit>1023-(P-1)){guard|=2u;return {0,0,a.sign^b.sign};}
    int offset=a.e-b.e-unit;
    if(offset>256||offset < -256){guard|=4u;return {0,0,0};}
    numerator=from_words(a.m,0,max(offset,0));denominator=from_words(b.m,0,max(-offset,0));
    Wide remainder;
    Wide quotient=divide(numerator,denominator,remainder);
    shift(remainder,1);
    bool ge=greater_equal(remainder,denominator);
    bool eq=ge&&greater_equal(denominator,remainder);
    if(ge&&(!eq||(quotient.w[0]&1u)))increment(quotient);
    return rounded<P>(quotient,unit,a.sign^b.sign,guard);
}
template<int P> __device__ __forceinline__ void update_probe(const Value* input,Value* output,U* guards,U count) {
    U index=blockIdx.x*blockDim.x+threadIdx.x;if(index>=count)return;
    const Value* v=input+8*index;U guard=0;
    // x - (step/weight)*(cost-dot), then Halpern toward/back averaging.
    Value step=div_value<P>(v[3],v[4],guard);
    Value minus_dot=v[2];minus_dot.sign^=1u;
    Value gradient=add_value<P>(v[1],minus_dot,guard);
    Value change=mul_value<P>(step,gradient,guard);change.sign^=1u;
    Value next=add_value<P>(v[0],change,guard);
    Value towards=div_value<P>(v[5],v[6],guard);
    Value backwards=div_value<P>(Value{1,0,0},v[6],guard);
    Value left=mul_value<P>(towards,next,guard);
    Value right=mul_value<P>(backwards,v[7],guard);
    Value result=add_value<P>(left,right,guard);
    guards[index]=guard;if(!guard)output[index]=result;
}
extern "C" __global__ void state_update_p48(const Value* a,Value* b,U* g,U n){update_probe<48>(a,b,g,n);}
extern "C" __global__ void state_update_p64(const Value* a,Value* b,U* g,U n){update_probe<64>(a,b,g,n);}

// Full-range scalar FMA is a separate obligation from the bounded row dot.
// For p=64, product bases range [-2170,1920], addend bases [-1085,960].
// A product plus an addend can require 3194 magnitude bits. 100 u32 limbs
// provide 3199 signed magnitude bits. This first construction retains every
// bit; sticky-tail/scratch alternatives need their own proof/construction.
struct FullWide {U w[100];};
__device__ __forceinline__ FullWide full_words(W lo,W hi,int offset) {
    FullWide result;int base=offset/32,rem=offset%32;
    U source[4]={(U)lo,(U)(lo>>32),(U)hi,(U)(hi>>32)};
    #pragma unroll
    for(int k=0;k<100;k++) {
        U a=0,b=0;
        #pragma unroll
        for(int j=0;j<4;j++){if(j==k-base)a=source[j];if(j==k-base-1)b=source[j];}
        result.w[k]=(a<<rem)|(rem?b>>(32-rem):0u);
    }
    return result;
}
__device__ __forceinline__ void full_negate(FullWide &a) {
    W carry=1;
    #pragma unroll
    for(int k=0;k<100;k++){W sum=(W)(~a.w[k])+carry;a.w[k]=(U)sum;carry=sum>>32;}
}
__device__ __forceinline__ void full_plus(FullWide &a,const FullWide &b) {
    W carry=0;
    #pragma unroll
    for(int k=0;k<100;k++){W sum=(W)a.w[k]+b.w[k]+carry;a.w[k]=(U)sum;carry=sum>>32;}
}
__device__ __forceinline__ U full_word(const FullWide &a,int index) {
    U result=0;
    #pragma unroll
    for(int k=0;k<100;k++)if(k==index)result=a.w[k];
    return result;
}
__device__ __forceinline__ bool full_below(const FullWide &a,int index) {
    U result=0;
    #pragma unroll
    for(int k=0;k<100;k++) {
        int count=index-32*k;
        U mask=count>=32?~0u:(count<=0?0u:((1u<<count)-1));
        result|=a.w[k]&mask;
    }
    return result!=0;
}
template<int P> __device__ __forceinline__ Value full_fma(Value a,Value b,Value c,U &guard) {
    bool nonzero_product=a.m&&b.m;
    int pe=nonzero_product?a.e+b.e:c.e,ce=c.m?c.e:pe;
    int base=min(pe,ce);
    FullWide sum=full_words(a.m*b.m,__umul64hi(a.m,b.m),pe-base);
    if(a.sign^b.sign)full_negate(sum);
    FullWide addend=full_words(c.m,0,ce-base);
    if(c.sign)full_negate(addend);
    full_plus(sum,addend);
    U sign=sum.w[99]>>31;if(sign)full_negate(sum);
    int highest=-1;
    #pragma unroll
    for(int k=0;k<100;k++)if(sum.w[k])highest=32*k+31-__clz(sum.w[k]);
    if(highest<0)return {0,0,(U)(!nonzero_product&&!c.m&&(a.sign^b.sign)&&c.sign)};
    int unit=max(base+highest-(P-1),-1022-(P-1));
    int offset=unit-base;W significand;
    if(offset<0)significand=((W)sum.w[0]|((W)sum.w[1]<<32))<<(-offset);
    else {
        int index=offset/32,rem=offset%32;
        W low=(W)full_word(sum,index)|((W)full_word(sum,index+1)<<32);
        significand=(low>>rem)|(rem?(W)full_word(sum,index+2)<<(64-rem):0ull);
    }
    if constexpr(P<64)significand&=(1ull<<P)-1;
    bool carry=false;
    if(offset>0&&((full_word(sum,(offset-1)/32)>>((offset-1)%32))&1u)&&
       (full_below(sum,offset-1)||(significand&1u))) {
        W previous=significand;significand++;carry=significand<previous;
    }
    bool too_wide=carry;
    if constexpr(P<64)too_wide|=significand==(1ull<<P);
    if(too_wide){significand=1ull<<(P-1);unit++;}
    if(unit>1023-(P-1)){guard|=2u;return {0,0,sign};}
    return {significand,significand?unit:0,sign};
}
template<int P> __device__ __forceinline__ void full_probe(const Value* input,Value* output,U* guards,U count) {
    U index=blockIdx.x*blockDim.x+threadIdx.x;if(index>=count)return;
    U guard=0;Value result=full_fma<P>(input[3*index],input[3*index+1],input[3*index+2],guard);
    guards[index]=guard;if(!guard)output[index]=result;
}
extern "C" __global__ void state_full_fma_p48(const Value* a,Value* b,U* g,U n){full_probe<48>(a,b,g,n);}
extern "C" __global__ void state_full_fma_p64(const Value* a,Value* b,U* g,U n){full_probe<64>(a,b,g,n);}
