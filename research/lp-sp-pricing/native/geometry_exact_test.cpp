#include <cstdint>
#include <cstdio>
extern "C" int sp_geometry_certificate(int,int,const uint64_t*,const int*,const int64_t*,uint64_t,const int64_t*,const int64_t*,const int64_t*,int,const int64_t*,int);
int main(){uint64_t o[]={0,1,2};int j[]={0,1};int64_t a[]={1,1},b[]={2,3},c[]={4,5},x[]={2,3},y[]={4,5};
 for(int k=0;k<64;++k){int64_t q[2]={x[0],x[1]};if(k%2)++q[0];int r=sp_geometry_certificate(2,2,o,j,a,2,b,c,q,0,y,0);if(r!=(k%2?1:0))return 1;}
 int64_t huge[]={1LL<<50,3};if(sp_geometry_certificate(2,2,o,j,a,2,b,c,huge,0,y,0)!=4)return 2;
 puts("64 exact certificate cases and overflow refusal passed");return 0;}
