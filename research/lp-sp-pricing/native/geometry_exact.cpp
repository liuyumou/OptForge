// Sparse GMP row reduction and exact bounded dyadic original-LP certificates.
#include "gmp_abi.h"
#include <algorithm>
#include <chrono>
#include <cstdint>
#include <cstring>
#include <map>
#include <string>
#include <vector>
namespace {
struct Q {
 SpQ v;Q(){__gmpq_init(&v);}~Q(){__gmpq_clear(&v);}
 Q(const Q& q):Q(){__gmpq_set(&v,&q.v);}Q& operator=(const Q&q){__gmpq_set(&v,&q.v);return *this;}
 bool nonzero()const{return v.numerator.size!=0;}
 size_t bits()const{return std::max(__gmpz_sizeinbase(&v.numerator,2),__gmpz_sizeinbase(&v.denominator,2));}
 void parse(const char*s){if(!s||strlen(s)>20000||__gmpq_set_str(&v,s,10)||!v.denominator.size)throw 4;__gmpq_canonicalize(&v);}
 std::string text()const{std::vector<char>s(__gmpz_sizeinbase(&v.numerator,10)+__gmpz_sizeinbase(&v.denominator,10)+8);__gmpq_get_str(s.data(),10,&v);return s.data();}
};
using Row=std::map<int,Q>;using Clock=std::chrono::steady_clock;
}
extern "C" int sp_geometry_rref(int m,int n,int columns,const uint64_t*offsets,const int*indices,
 const char**values,uint64_t nnz,uint64_t bits,uint64_t ns,uint64_t cap,uint64_t fill,uint64_t bytes_limit,char**out){
 if(!out)return 4;*out=nullptr;
 if(m<1||n<1||columns<0||columns>n||!offsets||!indices||!values||!ns||!fill||nnz>20000000||offsets[0]||offsets[m]!=nnz)return 4;
 try{
  if(std::strcmp(__gmp_version,"6.2.1"))throw 5;
  auto deadline=Clock::now()+std::chrono::nanoseconds(ns);uint64_t ops=0,peak=0,count=0,peakfill=0;
  auto check=[&](const Q&q){++ops;peak=std::max<uint64_t>(peak,q.bits());if(ops>cap)throw 2;if(peak>bits)throw 3;if((ops&511)==0&&Clock::now()>deadline)throw 1;};
  auto storage=[&](uint64_t entries){if(entries>fill||entries>bytes_limit/(112+(2*peak+7)/8))throw 8;};
  std::vector<Row> rows;std::vector<int>pivots;Q factor,term,scale;
  for(int original=0;original<m;++original){
   if(Clock::now()>deadline)throw 1;if(offsets[original]>offsets[original+1])throw 4;
   Row row;int last=-1;
   for(uint64_t k=offsets[original];k<offsets[original+1];++k){int j=indices[k];if(j<=last||j>=n)throw 4;last=j;Q q;q.parse(values[k]);check(q);if(q.nonzero())row.emplace(j,q);}
   for(size_t k=0;k<pivots.size();++k){auto at=row.find(pivots[k]);if(at==row.end())continue;factor=at->second;
    for(const auto&entry:rows[k]){int j=entry.first;__gmpq_mul(&term.v,&factor.v,&entry.second.v);auto&v=row[j];__gmpq_sub(&v.v,&v.v,&term.v);check(v);if(!v.nonzero())row.erase(j);}
   }
   storage(count+row.size());auto first=row.begin();if(first==row.end())continue;
   if(first->first>=columns){count+=row.size();storage(count);rows.push_back(row);continue;}
   int pivot=first->first;scale=first->second;
   for(auto&entry:row){__gmpq_div(&entry.second.v,&entry.second.v,&scale.v);check(entry.second);}
   for(auto&previous:rows){auto at=previous.find(pivot);if(at==previous.end())continue;factor=at->second;count-=previous.size();
    for(const auto&entry:row){int j=entry.first;__gmpq_mul(&term.v,&factor.v,&entry.second.v);auto&v=previous[j];__gmpq_sub(&v.v,&v.v,&term.v);check(v);if(!v.nonzero())previous.erase(j);}
    count+=previous.size();storage(count+row.size());
   }
   // Tail rows with augmented inconsistency are kept after all pivot rows.
   rows.insert(rows.begin()+pivots.size(),row);pivots.push_back(pivot);count+=row.size();peakfill=std::max(peakfill,count);storage(count);
  }
  std::vector<size_t>order(pivots.size());for(size_t k=0;k<order.size();++k)order[k]=k;
  std::sort(order.begin(),order.end(),[&](size_t a,size_t b){return pivots[a]<pivots[b];});
  std::string s=std::to_string(ops)+" "+std::to_string(peak)+" "+std::to_string(peakfill)+" "+std::to_string(rows.size())+"\n";
  for(size_t k:order)s+=std::to_string(pivots[k])+" ";s+="\n";
  for(size_t k=pivots.size();k<rows.size();++k)order.push_back(k);
  for(size_t k:order){s+=std::to_string(rows[k].size());for(const auto&e:rows[k])s+=" "+std::to_string(e.first)+" "+e.second.text();s+="\n";}
  if(Clock::now()>deadline)throw 1;*out=new char[s.size()+1];std::memcpy(*out,s.c_str(),s.size()+1);return 0;
 }catch(int code){return code;}catch(...){return 7;}
}
extern "C" void sp_geometry_free(char*p){delete[]p;}

extern "C" int sp_geometry_rank_cpu(int m,int n,const uint32_t*input,uint64_t ns,int*out){
 if(!input||!out||m<n||n<1||uint64_t(m)*n>10000000||!ns)return 4;*out=0;
 try{std::vector<uint32_t>a(input,input+size_t(m)*n);for(auto v:a)if(v>=65521)return 4;
 auto deadline=Clock::now()+std::chrono::nanoseconds(ns);
 for(int k=0;k<n;++k){if(Clock::now()>deadline)return 1;int chosen=k;while(chosen<m&&!a[size_t(chosen)*n+k])++chosen;if(chosen==m)return 0;
  if(chosen!=k)for(int j=k;j<n;++j)std::swap(a[size_t(k)*n+j],a[size_t(chosen)*n+j]);
  uint64_t v=a[size_t(k)*n+k],inv=1;for(unsigned power=65519;power;power>>=1,v=v*v%65521)if(power&1)inv=inv*v%65521;
  for(int j=k;j<n;++j)a[size_t(k)*n+j]=uint64_t(a[size_t(k)*n+j])*inv%65521;
  for(int i=k+1;i<m;++i){uint64_t f=a[size_t(i)*n+k];if(!f)continue;
   for(int j=k+1;j<n;++j){uint32_t p=f*a[size_t(k)*n+j]%65521;auto&v=a[size_t(i)*n+j];v=v>=p?v-p:v+65521-p;}a[size_t(i)*n+k]=0;}
  *out=k+1;
 }return 0;}catch(...){return 7;}
}

// Every input is bounded by 2^40; dimensions <= 2^20 and endpoint scale <= 24.
// Products/sums/objective shifts stay strictly below 2^125. No signed overflow.
extern "C" int sp_geometry_certificate(int m,int n,const uint64_t*off,const int*idx,const int64_t*a,
 uint64_t nnz,const int64_t*b,const int64_t*c,const int64_t*x,int px,const int64_t*y,int py){
 if(m<1||n<1||m>(1<<20)||n>(1<<20)||!off||!idx||!a||!b||!c||!x||!y||px<0||px>24||py<0||py>24||off[0]||off[m]!=nnz)return 4;
 const int64_t bound=1LL<<40;auto valid=[&](int64_t v){return v>=-bound&&v<=bound;};
 for(int j=0;j<n;++j)if(!valid(c[j])||!valid(x[j]))return 4;
 for(int i=0;i<m;++i)if(!valid(b[i])||!valid(y[i]))return 4;else if(y[i]<0)return 1;
 std::vector<__int128>dual(n,0);__int128 primal_value=0,dual_value=0;
 for(int i=0;i<m;++i){if(off[i]>off[i+1]||off[i+1]-off[i]>uint64_t(n))return 4;__int128 sum=0;int last=-1;
  for(uint64_t k=off[i];k<off[i+1];++k){int j=idx[k];if(j<=last||j>=n||!valid(a[k]))return 4;last=j;sum+=(__int128)a[k]*x[j];dual[j]+=(__int128)a[k]*y[i];}
  if(sum>(__int128)b[i]*((__int128)1<<px))return 1;
  dual_value+=(__int128)b[i]*y[i];
 }
 for(int j=0;j<n;++j){if(dual[j]!=(__int128)c[j]*((__int128)1<<py))return 1;primal_value+=(__int128)c[j]*x[j];}
 return primal_value*((__int128)1<<py)==dual_value*((__int128)1<<px)?0:1;
}
