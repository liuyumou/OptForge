// Versioned parser correction; all arithmetic includes retain their exact bytes.
#define __device__
#define __forceinline__ inline
#define __global__
#define EXPANDED_HOST
#include <charconv>
#include <cmath>
#include <iostream>
#include <sstream>
#include <string>
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

template<class T> bool field(std::istringstream &row, T &out) {
    std::string token;
    if(!(row>>token))return false;
    auto result=std::from_chars(token.data(),token.data()+token.size(),out);
    return result.ec==std::errc{}&&result.ptr==token.data()+token.size();
}

int main() {
    std::string line;
    unsigned long long index=0;
    while(std::getline(std::cin,line)) {
        ++index;
        std::istringstream row(line);
        Value v[3];
        for(int k=0;k<3;k++) {
            if(!field(row,v[k].m)||!field(row,v[k].e)||!field(row,v[k].sign)) {
                std::cerr<<"input "<<index<<", operand "<<k<<": malformed or overflowing field\n";
                return 2;
            }
            auto x=v[k];
            if(x.sign>1||(!x.m&&x.e)||
               (x.m&&(x.e < -1085||x.e>960||(x.e != -1085&&x.m<(1ull<<63))))) {
                std::cerr<<"input "<<index<<", operand "<<k<<": noncanonical value "
                         <<x.m<<' '<<x.e<<' '<<x.sign<<'\n';
                return 2;
            }
        }
        std::string extra;
        if(row>>extra) {
            std::cerr<<"input "<<index<<": trailing field\n";
            return 2;
        }
        U guard=0,fast=0;
        Value out=expanded_fma(v[0],v[1],v[2],guard,fast);
        std::cout<<out.m<<' '<<out.e<<' '<<out.sign<<' '<<guard<<' '<<fast<<'\n';
    }
    if(!std::cin.eof()) {
        std::cerr<<"input "<<index+1<<": stream failure\n";
        return 2;
    }
    return 0;
}
