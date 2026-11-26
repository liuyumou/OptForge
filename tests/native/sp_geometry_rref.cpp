#include <cstdint>
#include <cstdio>
#include <cstring>
extern "C" int sp_geometry_rref(int,int,int,const uint64_t*,const int*,const char**,uint64_t,uint64_t,uint64_t,uint64_t,uint64_t,uint64_t,char**);
extern "C" void sp_geometry_free(char*);
int main(){uint64_t o[]={0,3,6,9};int j[]={0,1,2,0,1,2,0,1,2};
 const char*values[]={"0","1/3","2","1","0","4","2","0","8"};
 for(int k=0;k<64;++k){char*out=nullptr;int r=sp_geometry_rref(3,3,k%2?2:3,o,j,values,9,16384,1000000000,1000000,10000,1ULL<<30,&out);
  if(r||!out||!std::strchr(out,'\n'))return 1;sp_geometry_free(out);}
 char*out=nullptr;int bad[]={0,0,2,0,1,2,0,1,2};
 if(sp_geometry_rref(3,3,3,o,bad,values,9,16384,1000000000,1000000,10000,1ULL<<30,&out)!=4||out)return 2;
 if(sp_geometry_rref(3,3,3,o,j,values,9,16384,1000000000,1000000,1,1ULL<<30,&out)!=8||out)return 3;
 puts("64 RREF lifetime cases, malformed CSR and fill refusal passed");return 0;}
