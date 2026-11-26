#include <cassert>
#include <cstdint>
#include <vector>
extern "C" int sp_compact_proof_create(int,int,double,double,double,double,int,void**);
extern "C" int sp_compact_proof_begin(void*,int,const double*,const double*,uint64_t,uint64_t);
extern "C" int sp_compact_proof_tile(void*,int,int,int,int,int,const double*,const double*);
extern "C" int sp_compact_proof_finish(void*,int,int*,int*,uint64_t*);
extern "C" int sp_compact_proof_sparse(void*,int,int,int,int,int,int,const int*,const int*,const double*,const double*);
extern "C" void sp_compact_proof_destroy(void*);
int main(){
    for(int r=1;r<=64;++r){
        void* p=nullptr;double eps=1./65536;
        assert(sp_compact_proof_create(r,4,4,4,eps,eps,0,&p)==0);
        std::vector<double> x(r,.5/r),u(4,0),a(r*4,0);
        for(int i=0;i<r;++i)a[4*i+1]=1;
        int labels[2]={0,0},uncertain=0;uint64_t operations=0;
        assert(sp_compact_proof_begin(p,0,x.data(),u.data(),1000000000,1000000)==0);
        assert(sp_compact_proof_tile(p,0,0,0,r,4,a.data(),a.data())==0);
        assert(sp_compact_proof_finish(p,0,labels,&uncertain,&operations)==0);
        assert(labels[0]==1&&labels[1]==0);
        assert(sp_compact_proof_begin(p,1,x.data(),u.data(),1000000000,1000000)==0);
        assert(sp_compact_proof_tile(p,1,0,0,r,4,a.data(),a.data())==0);
        assert(sp_compact_proof_finish(p,1,labels,&uncertain,&operations)==0);
        assert(labels[1]==-1);
        std::vector<int> offsets(r+1),indices(r,1);std::vector<double> values(r,1);
        for(int i=0;i<=r;++i)offsets[i]=i;labels[0]=labels[1]=0;
        assert(sp_compact_proof_begin(p,0,x.data(),u.data(),1000000000,1000000)==0);
        assert(sp_compact_proof_sparse(p,0,0,0,r,4,r,offsets.data(),indices.data(),values.data(),values.data())==0);
        assert(sp_compact_proof_finish(p,0,labels,&uncertain,&operations)==0);
        assert(labels[0]==1);
        assert(sp_compact_proof_tile(p,0,r,0,1,4,a.data(),a.data())==4);
        sp_compact_proof_destroy(p);
    }
    return 0;
}
