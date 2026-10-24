// ADR-0046 scalar construction. Include the source-bound compact integer helpers
// first. This header has no kernel entry points and performs no FP64 arithmetic.
// The exact partials are integer-valued FP32 numbers, so TwoProduct has neither
// overflow nor subnormal loss: each input digit has at most 24 significant bits.
struct ExpandedSigned { Wide magnitude; U sign; };

__device__ __forceinline__ void expanded_term(
    ExpandedSigned &sum, float term, int exponent, int base, U sign, U &guard) {
#ifdef EXPANDED_HOST
    U raw; __builtin_memcpy(&raw,&term,sizeof(raw));
#else
    U raw=__float_as_uint(term);
#endif
    U field=(raw>>23)&255u;
    W m=raw&0x7fffffu;
    if(!field&&!m)return;
    if(!field||field==255u){guard|=8u;return;}
    m|=1ull<<23;
    int e=(int)field-127-23;
    while(!(m&1ull)){m>>=1;e++;}
    int offset=exponent+e-base;
    if(offset<0||offset>256){guard|=8u;return;}
    Wide value=from_words(m,0,offset);
    U s=sign^(raw>>31);
    if(sum.sign==s){plus(sum.magnitude,value);return;}
    if(greater_equal(sum.magnitude,value)) {
        subtract(sum.magnitude,value);
        if(top(sum.magnitude)<0)sum.sign=0;
    } else {
        subtract(value,sum.magnitude);sum.magnitude=value;sum.sign=s;
    }
}

__device__ __forceinline__ Value expanded_fma(
    Value a,Value b,Value c,U &guard,U &used_fast) {
    bool product=a.m&&b.m;
    int pe=product?a.e+b.e:c.e;
    int ce=c.m?c.e:pe;
    int base=min(pe,ce);
    int top_bound=max(product?pe+128:base,c.m?ce+64:base);
    used_fast=(U)(product&&top_bound-base<=128);
    if(!used_fast)return compact_fma<64>(a,b,c,guard);
    float av[3]={(float)(a.m>>40),(float)((a.m>>16)&0xffffffull),(float)(a.m&0xffffull)};
    float bv[3]={(float)(b.m>>40),(float)((b.m>>16)&0xffffffull),(float)(b.m&0xffffull)};
    float cv[3]={(float)(c.m>>40),(float)((c.m>>16)&0xffffffull),(float)(c.m&0xffffull)};
    int offsets[3]={40,16,0};
    ExpandedSigned sum={zero(),0};
#pragma unroll
    for(int i=0;i<3;i++) {
#pragma unroll
        for(int j=0;j<3;j++) {
            float p=av[i]*bv[j];
#ifdef EXPANDED_HOST
            float error=__builtin_fmaf(av[i],bv[j],-p);
#else
            float error=__fmaf_rn(av[i],bv[j],-p);
#endif
            int exponent=pe+offsets[i]+offsets[j];
            expanded_term(sum,p,exponent,base,a.sign^b.sign,guard);
            expanded_term(sum,error,exponent,base,a.sign^b.sign,guard);
        }
        expanded_term(sum,cv[i],ce+offsets[i],base,c.sign,guard);
    }
    if(guard)return {0,0,0};
    if(top(sum.magnitude)<0)return {0,0,0};
    return rounded<64>(sum.magnitude,base,sum.sign,guard);
}
