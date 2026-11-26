// Standalone differential certificate stress harness, suitable for ASan/UBSan.
#include <algorithm>
#include <cassert>
#include <cstdint>
#include <iostream>
#include <random>
#include <vector>
extern "C" int sp_market(int,int,int,const int*,const int*,const int*,const std::int64_t*,
    const std::uint64_t*,const std::uint64_t*,std::uint64_t,std::uint64_t,std::int64_t*,
    std::uint64_t*,std::uint64_t*,std::uint64_t*);
int main() {
    std::mt19937 rng(9313);
    for(int trial=0;trial<96;++trial) {
        int n=1+trial%12;
        std::vector<int> offsets{0},coordinates,signs;
        std::vector<std::int64_t> demands;
        std::vector<std::uint64_t> weights,high;
        auto expert=[&](std::vector<int> c,std::vector<int> s,std::vector<std::int64_t> a) {
            coordinates.push_back(-1);signs.push_back(0);demands.push_back(0);
            coordinates.insert(coordinates.end(),c.begin(),c.end());
            signs.insert(signs.end(),s.begin(),s.end());demands.insert(demands.end(),a.begin(),a.end());
            offsets.push_back(int(coordinates.size()));weights.push_back(1+rng()%64);high.push_back(0);
        };
        for(int i=0;i<n;++i)for(int s:{-1,1})for(int a:{-7,0,7})expert({i},{s},{a});
        for(int e=0;e<64;++e) {
            std::vector<int> c,s;std::vector<std::int64_t>a;
            for(int k=0;k<4;++k){c.push_back(rng()%n);s.push_back(rng()%2?1:-1);a.push_back(int(rng()%15)-7);}
            expert(c,s,a);
        }
        int count=int(coordinates.size());
        std::vector<std::int64_t> price(n);
        std::vector<std::uint64_t> low(2*count),upper(2*count),metric(3);
        int code=sp_market(n,int(weights.size()),count,offsets.data(),coordinates.data(),signs.data(),demands.data(),
            weights.data(),high.data(),30000000000ULL,100000000ULL,price.data(),low.data(),upper.data(),metric.data());
        assert(code==0);
        std::vector<__int128> balance(n,0);
        __int128 lower_value=0,upper_value=0;
        for(int e=0;e<int(weights.size());++e) {
            __int128 allocation=0;std::int64_t utility=0;
            for(int j=offsets[e];j<offsets[e+1];++j) {
                assert(upper[2*j]==0&&upper[2*j+1]==0);
                auto mass=__int128(low[2*j])+low[2*j+1];allocation+=mass;
                lower_value+=mass*demands[j];
                if(coordinates[j]>=0) {
                    balance[coordinates[j]]+=signs[j]*mass;
                    utility=std::max(utility,2*demands[j]-signs[j]*price[coordinates[j]]);
                }
            }
            assert(allocation==2*weights[e]);upper_value+=__int128(weights[e])*utility;
        }
        assert(lower_value==upper_value);
        for(auto v:balance)assert(v==0);
    }
    std::cout<<"96 exact native flow certificate cases passed\n";
}
