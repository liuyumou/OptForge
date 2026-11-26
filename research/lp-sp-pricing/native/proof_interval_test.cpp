#include <cassert>
#include <cstdint>
#include <sstream>
#include <string>
#include <vector>
extern "C" int sp_interval_create(int,int,const double*,const double*,double,double,double,double,int,void**);
extern "C" int sp_interval_batch(void*,int,const int*,const int*,const double*,const double*,const int*,int*,int*,uint64_t,uint64_t,uint64_t*);
extern "C" void sp_interval_destroy(void*);
extern "C" int sp_proof_create(int,int,const char**,const char*,const char*,uint64_t,int,void**);
extern "C" int sp_proof_labels(void*,int,const double*,const double*,int,uint64_t,uint64_t,char**);
extern "C" void sp_proof_free_string(char*);
extern "C" void sp_proof_destroy(void*);
int main(){
    uint32_t seed=11743;auto random=[&](){seed=1664525*seed+1013904223;return int(seed%17)-8;};
    for(int test=0;test<128;++test){
        int r=1+test%5,n=1+test%7,s=2*n;
        std::vector<double> b(r*s),x(r),u(s);std::vector<std::string> text(r*s);std::vector<const char*> strings(r*s);
        for(int i=0;i<r*s;++i){int v=random();b[i]=double(v)/4;text[i]=std::to_string(v)+"/4";strings[i]=text[i].c_str();}
        for(auto& v:x)v=double(random())/4;
        for(auto& v:u)v=double(random())/8;
        void* interval=nullptr;void* exact=nullptr;
        assert(sp_interval_create(r,s,b.data(),b.data(),4,4,1./65536,1./65536,0,&interval)==0);
        assert(sp_proof_create(r,s,strings.data(),"4","1/65536",16384,0,&exact)==0);
        int target=test%n,active=1,uncertain=0;std::vector<int> known(n,0),labels(n,0);uint64_t stats[4];
        assert(sp_interval_batch(interval,1,&target,&active,x.data(),u.data(),known.data(),labels.data(),&uncertain,
            1000000000ULL,10000000,stats)==0);
        char* result=nullptr;assert(sp_proof_labels(exact,target,x.data(),u.data(),0,1000000000ULL,10000000,&result)==0);
        std::istringstream stream(result);std::string line,decisions;for(int i=0;i<4;++i){std::getline(stream,line);if(i==3)decisions=line;}
        assert(int(decisions.size())==n);
        for(int i=0;i<n;++i){int expected=decisions[i]=='+'?1:decisions[i]=='-'?-1:0;
            if(labels[i])assert(labels[i]==expected);if(!uncertain)assert(labels[i]==expected);}
        sp_proof_free_string(result);sp_proof_destroy(exact);sp_interval_destroy(interval);
    }
}
