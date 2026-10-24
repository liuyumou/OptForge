// Expansion64 SoA, with three exact integer FP32 limbs and one exponent/sign word.
// Include source-bound integer helpers and expanded_fast.h before this header.
struct ExpandedConst { const float *hi,*mid,*lo;const U *meta; };
struct ExpandedOut { float *hi,*mid,*lo;U *meta; };

__device__ __forceinline__ Value expanded_load(ExpandedConst x,U i,U &guard) {
    U tag=x.meta[i];
    float h=x.hi[i],m=x.mid[i],l=x.lo[i];
    if((tag&0x7fff0000u)||!isfinite(h)||!isfinite(m)||!isfinite(l)||
       __float_as_uint(h)>>31||__float_as_uint(m)>>31||__float_as_uint(l)>>31||
       h>=16777216.f||m>=16777216.f||l>=65536.f) {
        guard|=8u;return {0,0,0};
    }
    U hi=(U)h,mid=(U)m,lo=(U)l;
    if((float)hi!=h||(float)mid!=m||(float)lo!=l){guard|=8u;return {0,0,0};}
    W magnitude=((W)hi<<40)|((W)mid<<16)|lo;
    int exponent=(int)(tag&0xffffu);
    if(exponent&0x8000)exponent-=65536;
    if((!magnitude&&exponent)||(magnitude&&(exponent < -1085||exponent>960||
        (exponent != -1085&&magnitude<(1ull<<63)))))guard|=8u;
    return {magnitude,exponent,tag>>31};
}

__device__ __forceinline__ void expanded_store(ExpandedOut x,U i,Value v) {
    x.hi[i]=(float)(v.m>>40);
    x.mid[i]=(float)((v.m>>16)&0xffffffull);
    x.lo[i]=(float)(v.m&0xffffull);
    x.meta[i]=((U)v.e&0xffffu)|(v.sign<<31);
}

__device__ __forceinline__ bool expanded_less(Value a,Value b) {
    if(!a.m&&!b.m)return false;
    if(!a.m)return !b.sign;
    if(!b.m)return a.sign!=0;
    if(a.sign!=b.sign)return a.sign!=0;
    bool magnitude_less=a.e==b.e?a.m<b.m:a.e<b.e;
    bool equal=a.m==b.m&&a.e==b.e;
    return a.sign?!magnitude_less&&!equal:magnitude_less;
}

__device__ __forceinline__ Value expanded_from_fp64(W bits,U &guard) {
    U field=(U)(bits>>52)&2047u,sign=(U)(bits>>63);
    W m=bits&0xfffffffffffffull;
    if(field==2047u){guard|=8u;return {0,0,sign};}
    int e=-1074;
    if(field){m|=1ull<<52;e=(int)field-1075;}
    if(!m)return {0,0,sign};
    int shift=min(__clzll(m),e+1085);
    return {m<<shift,e-shift,sign};
}

__device__ __forceinline__ W expanded_to_fp64(Value v,U &guard) {
    Value f=rounded<53>(from_words(v.m,0,0),v.e,v.sign,guard);
    if(v.m&&!f.m)guard|=4u;
    if(guard)return 0;
    W bits=f.m<(1ull<<52)?f.m:((W)(f.e+1075)<<52)|(f.m&0xfffffffffffffull);
    return bits|((W)f.sign<<63);
}
