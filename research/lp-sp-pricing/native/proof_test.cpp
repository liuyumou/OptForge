#include <cstdint>
#include <cstring>
#include <iostream>
#include <limits>
extern "C" int sp_proof_create(int,int,const char**,const char*,const char*,uint64_t,int,void**);
extern "C" int sp_proof_check(void*,int,const double*,const double*,int,uint64_t,uint64_t,char**);
extern "C" int sp_proof_labels(void*,int,const double*,const double*,int,uint64_t,uint64_t,char**);
extern "C" void sp_proof_free_string(char*);
extern "C" void sp_proof_destroy(void*);
int main(){
    const char* b[]={"0","1","1","0"};double x[]={1,0},u[]={0,0};
    for(int k=0;k<96;++k){
        void* ctx=nullptr;char* text=nullptr;
        if(sp_proof_create(2,2,b,"1","1/1024",16384,1,&ctx))return 1;
        x[0]=(k%17-8)/4.;x[1]=(k%13-6)/4.;u[0]=(k%5-2)/8.;u[1]=(k%7-3)/8.;
        if(sp_proof_check(ctx,0,x,u,k%2,1000000000,10000,&text)||!text)return 2;
        if(std::strlen(text)<8)return 3;sp_proof_free_string(text);text=nullptr;
        if(sp_proof_labels(ctx,0,x,u,0,1000000000,10000,&text)||!text)return 9;
        sp_proof_free_string(text);text=nullptr;
        if(sp_proof_check(ctx,1,x,u,0,1000000000,10000,&text)!=4||text)return 4;
        if(sp_proof_check(ctx,0,x,u,0,1000000000,0,&text)!=2||text)return 5;
        x[0]=std::numeric_limits<double>::infinity();
        if(sp_proof_check(ctx,0,x,u,0,1000000000,10000,&text)!=4||text)return 6;
        sp_proof_destroy(ctx);
    }
    void* out=nullptr;const char* bad[]={"1/0","0"};
    if(sp_proof_create(1,2,bad,"1","1/1024",16384,0,&out)!=4||out)return 7;
    if(sp_proof_create(2147483647,2,bad,"1","1/1024",16384,0,&out)!=4||out)return 8;
    std::cout<<"96 native exact proof cases and malformed inputs passed\n";
}
