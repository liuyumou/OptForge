#include <cassert>
#include <cstdint>
#include <cstdio>
#include <sstream>
#include <string>
#include <vector>
extern "C" int sp_aux_create(int,int,const char**,const char**,uint64_t,void**);
extern "C" int sp_aux_solve(void*,const char**,uint64_t,uint64_t,char**);
extern "C" void sp_aux_free_string(char*);
extern "C" void sp_aux_destroy(void*);
extern "C" int sp_rref(int,int,int,const char**,uint64_t,uint64_t,uint64_t,char**);
int main(){
    for(int run=0;run<96;++run){
        int n=1+run%12,m=2*n;
        std::vector<std::string> a(m*n,"0"),b(m,"2"),c(n,"1");
        for(int j=0;j<n;++j){a[(2*j)*n+j]="1";a[(2*j+1)*n+j]="-1";}
        std::vector<const char*> ap,bp,cp;
        for(auto& v:a)ap.push_back(v.c_str());
        for(auto& v:b)bp.push_back(v.c_str());
        void* handle=nullptr;
        assert(sp_aux_create(m,n,ap.data(),bp.data(),16384,&handle)==0);
        for(int k=0;k<8;++k){
            for(int j=0;j<n;++j)c[j]=k%2?"0":((j+k)%2?"-1":"1");
            cp.clear();for(auto& v:c)cp.push_back(v.c_str());char* result=nullptr;
            assert(sp_aux_solve(handle,cp.data(),1000000000,10000000,&result)==0);
            std::string text(result);assert(text.rfind(k%2?"optimal\n":"feasible_target\n",0)==0);
            sp_aux_free_string(result);
        }
        sp_aux_destroy(handle);
        char* reduced=nullptr;
        assert(sp_rref(m,n,n,ap.data(),16384,1000000000,10000000,&reduced)==0);
        std::istringstream lines(reduced);int rank=0;lines>>rank;assert(rank==n);sp_aux_free_string(reduced);
    }
    void* handle=nullptr;const char* bad[]={"1/0"};const char* bound[]={"1"};
    assert(sp_aux_create(1,1,bad,bound,16384,&handle)==4 && !handle);
    assert(sp_aux_create(2147483647,1,bad,bound,16384,&handle)==4 && !handle);
    std::puts("96 persistent-tableau and elimination cases passed; malformed denominator rejected");
}
