// CPU validation of the exact integer resource probe, not a runtime implementation.
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
#include "lp_state_integer_probe.cu"
#include <iostream>
int main() {
    unsigned operation;
    while(std::cin>>operation) {
        if(operation==2||operation==3) {
            unsigned precision,guard=0;std::cin>>precision;
            Value inputs[8],result{};
            unsigned count=operation==2?3:8;
            for(unsigned k=0;k<count;k++)std::cin>>inputs[k].m>>inputs[k].e>>inputs[k].sign;
            if(!std::cin||(precision!=48&&precision!=64))return 2;
            if(operation==2)result=precision==48?full_fma<48>(inputs[0],inputs[1],inputs[2],guard):full_fma<64>(inputs[0],inputs[1],inputs[2],guard);
            else {
                blockDim.x=1;
                if(precision==48)update_probe<48>(inputs,&result,&guard,1);
                else update_probe<64>(inputs,&result,&guard,1);
            }
            std::cout<<result.m<<' '<<result.e<<' '<<result.sign<<' '<<guard<<'\n';
            continue;
        }
        Wide a,b,r;
        for(auto &x:a.w)std::cin>>x;
        for(auto &x:b.w)std::cin>>x;
        if(!std::cin)return 2;
        U any=0;for(auto x:b.w)any|=x;
        if(operation==1&&!any)return 3;
        Wide result=operation==1?divide(a,b,r):root(a,r);
        for(auto x:result.w)std::cout<<x<<' ';
        for(auto x:r.w)std::cout<<x<<' ';
        std::cout<<'\n';
    }
}
