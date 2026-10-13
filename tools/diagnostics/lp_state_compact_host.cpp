// Host-only validation of both FMA constructions, including undefined behavior.
#define __device__
#define __forceinline__ inline
#define __global__
struct Dim { unsigned x; };
Dim blockIdx{},blockDim{},threadIdx{};
inline int __clz(unsigned value){return __builtin_clz(value);}
inline int __clzll(unsigned long long value){return __builtin_clzll(value);}
inline unsigned long long __umul64hi(unsigned long long a,unsigned long long b){return (unsigned long long)(((__uint128_t)a*b)>>64);}
template<class T> T min(T a,T b){return a<b?a:b;}
template<class T> T max(T a,T b){return a>b?a:b;}
#include "lp_state_compact_probe.cu"
#include <iostream>

bool valid(Value value,unsigned precision) {
    if(value.sign>1)return false;
    if(!value.m)return value.e==0;
    int minimum=-1022-(int)(precision-1),maximum=1023-(int)(precision-1);
    if(value.e<minimum||value.e>maximum)return false;
    if(precision==48&&value.m>=(1ull<<48))return false;
    return value.e==minimum||value.m>=(1ull<<(precision-1));
}
int main() {
    unsigned operation;
    while(std::cin>>operation) {
        unsigned precision,guard=0;
        Value v[3],result{};
        if(!(std::cin>>precision)||(precision!=48&&precision!=64))return 2;
        for(auto &value:v) {
            if(!(std::cin>>value.m>>value.e>>value.sign)||!valid(value,precision))return 2;
        }
        if(operation==2)result=precision==48?full_fma<48>(v[0],v[1],v[2],guard):full_fma<64>(v[0],v[1],v[2],guard);
        else if(operation==4)result=precision==48?compact_fma<48>(v[0],v[1],v[2],guard):compact_fma<64>(v[0],v[1],v[2],guard);
        else return 2;
        std::cout<<result.m<<' '<<result.e<<' '<<result.sign<<' '<<guard<<'\n';
    }
    return std::cin.eof()?0:2;
}
