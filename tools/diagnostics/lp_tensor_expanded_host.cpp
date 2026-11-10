// Independent-host build of the new FP32 EFT/full-range scalar candidate.
#define __device__
#define __forceinline__ inline
#define __global__
#define EXPANDED_HOST
#include <cmath>
#include <iostream>
struct Dim { unsigned x; };
Dim blockIdx{},blockDim{},threadIdx{};
inline int __clz(unsigned v){return __builtin_clz(v);}
inline int __clzll(unsigned long long v){return __builtin_clzll(v);}
inline unsigned long long __umul64hi(unsigned long long a,unsigned long long b){
    return (unsigned long long)(((__uint128_t)a*b)>>64);
}
template<class T> T min(T a,T b){return a<b?a:b;}
template<class T> T max(T a,T b){return a>b?a:b;}
#include "lp_state_compact_probe.cu"
#include "../../cuda/lp_pdhg_tensor_expanded/expanded_fast.h"

int main() {
    Value v[3];
    while(std::cin>>v[0].m>>v[0].e>>v[0].sign) {
        for(int k=1;k<3;k++)if(!(std::cin>>v[k].m>>v[k].e>>v[k].sign))return 2;
        for(auto x:v)if(x.sign>1||(!x.m&&x.e)||
            (x.m&&(x.e < -1085||x.e>960||(x.e != -1085&&x.m<(1ull<<63)))))return 2;
        U guard=0,fast=0;
        Value out=expanded_fma(v[0],v[1],v[2],guard,fast);
        std::cout<<out.m<<' '<<out.e<<' '<<out.sign<<' '<<guard<<' '<<fast<<'\n';
    }
    return std::cin.eof()?0:2;
}
