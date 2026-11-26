// Exact GMP checking of inexact device proposals. No floating acceptance test.
#include "gmp_abi.h"
#include <algorithm>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <cstring>
#include <string>
#include <vector>
extern "C" void __gmpq_set_d(SpQ*, double);
extern "C" void __gmpz_lcm(SpZ*, const SpZ*, const SpZ*);
namespace {
struct Q {
    SpQ v;
    Q(){__gmpq_init(&v);}
    explicit Q(long x):Q(){__gmpq_set_si(&v,x,1);}
    Q(const Q& x):Q(){__gmpq_set(&v,&x.v);}
    Q& operator=(const Q& x){if(this!=&x)__gmpq_set(&v,&x.v);return *this;}
    ~Q(){__gmpq_clear(&v);}
    void parse(const char* s){
        if(!s || std::strlen(s)>100000 || __gmpq_set_str(&v,s,10) || !v.denominator.size)throw 4;
        __gmpq_canonicalize(&v);
    }
    void number(double x){if(!std::isfinite(x))throw 4;__gmpq_set_d(&v,x);}
    int sign()const{return (v.numerator.size>0)-(v.numerator.size<0);}
    size_t bits()const{return std::max(__gmpz_sizeinbase(&v.numerator,2),__gmpz_sizeinbase(&v.denominator,2));}
    std::string str()const{
        std::vector<char> s(__gmpz_sizeinbase(&v.numerator,10)+__gmpz_sizeinbase(&v.denominator,10)+8);
        __gmpq_get_str(s.data(),10,&v);return s.data();
    }
};
using Clock=std::chrono::steady_clock;
struct Context {
    int r,s;size_t max_bits,peak=0;uint64_t ops=0,limit=0;Clock::time_point deadline;
    Q h,low,two{2},quarter,matrix_den{1};bool opposite,integer_matrix=true;
    size_t matrix_integer_bits=0;int integer_products=0;
    std::vector<std::vector<std::pair<int,Q>>> rows;
    std::vector<std::vector<std::pair<int,Q>>> integer_rows;
    Context(int r_,int s_,const char** b,const char* h_,const char* eps,size_t bits,bool broadcast):
        r(r_),s(s_),max_bits(bits),opposite(broadcast),rows(r),integer_rows(r){
        if(std::strcmp(__gmp_version,"6.2.1"))throw 5;
        h.parse(h_);low.parse(eps);__gmpq_set_si(&quarter.v,1,4);
        if(h.sign()<=0 || low.sign()<=0 || __gmpq_cmp(&low.v,&quarter.v)>=0)throw 4;
        if(h.bits()>max_bits || low.bits()>max_bits)throw 3;
        __gmpq_neg(&low.v,&low.v);
        for(int i=0;i<r;++i)for(int j=0;j<s;++j){
            Q q;q.parse(b[size_t(i)*s+j]);if(q.bits()>max_bits)throw 3;
            if(q.sign())rows[i].emplace_back(j,q);
        }
        for(const auto& row:rows)for(const auto& entry:row)if(integer_matrix){
            __gmpz_lcm(&matrix_den.v.numerator,&matrix_den.v.numerator,&entry.second.v.denominator);
            if(matrix_den.bits()>max_bits/2)integer_matrix=false;
        }
        if(integer_matrix)for(int i=0;i<r;++i)for(const auto& entry:rows[i]){
            Q scaled;__gmpq_mul(&scaled.v,&entry.second.v,&matrix_den.v);
            matrix_integer_bits=std::max(matrix_integer_bits,scaled.bits());
            integer_rows[i].emplace_back(entry.first,scaled);
        }
    }
    void check(const Q& q){
        peak=std::max(peak,q.bits());
        if(++ops>limit)throw 2;
        if(peak>max_bits)throw 3;
        if((ops&511)==0 && Clock::now()>deadline)throw 1;
    }
    bool integer_product(const std::vector<Q>& v,std::vector<Q>& result,bool residual,int target){
        if(!integer_matrix)return false;
        Q denominator(1);size_t numerator_bits=0;
        for(const auto& value:v){
            numerator_bits=std::max(numerator_bits,__gmpz_sizeinbase(&value.v.numerator,2));
            __gmpz_lcm(&denominator.v.numerator,&denominator.v.numerator,&value.v.denominator);
            if(denominator.bits()>max_bits/2)return false;
            check(denominator);
        }
        size_t growth=2;for(int n=std::max(r,s);n;n/=2)++growth;
        if(matrix_integer_bits+denominator.bits()+numerator_bits+growth>max_bits ||
           matrix_den.bits()+denominator.bits()>max_bits)return false;
        std::vector<Q> scaled(v.size());Q common,term;
        for(size_t j=0;j<v.size();++j){__gmpq_mul(&scaled[j].v,&v[j].v,&denominator.v);check(scaled[j]);}
        __gmpq_mul(&common.v,&matrix_den.v,&denominator.v);check(common);
        for(int i=0;i<r;++i){
            if(residual)for(const auto& entry:integer_rows[i])if(entry.first==2*target+1){
                __gmpq_mul(&result[i].v,&entry.second.v,&denominator.v);check(result[i]);}
            for(const auto& entry:integer_rows[i]){
                int j=entry.first,index=residual?j:i,output=residual?i:j;
                if(!scaled[index].sign())continue;
                __gmpq_mul(&term.v,&entry.second.v,&scaled[index].v);check(term);
                if(residual)__gmpq_sub(&result[output].v,&result[output].v,&term.v);
                else __gmpq_add(&result[output].v,&result[output].v,&term.v);
                check(result[output]);
            }
        }
        for(auto& value:result){__gmpq_div(&value.v,&value.v,&common.v);check(value);}
        ++integer_products;return true;
    }
    std::string prove(int target,const double* raw_x,const double* raw_u,bool full,uint64_t ns,uint64_t cap,bool compact){
        ops=0;peak=0;integer_products=0;limit=cap;deadline=Clock::now()+std::chrono::nanoseconds(ns);
        std::vector<Q> x(r),y(s),u(s);Q minus_h,term,scale(1),ratio,upper;
        __gmpq_neg(&minus_h.v,&h.v);
        for(int i=0;i<r;++i){
            x[i].number(raw_x[i]);
            if(__gmpq_cmp(&x[i].v,&h.v)>0)x[i]=h;
            if(__gmpq_cmp(&x[i].v,&minus_h.v)<0)x[i]=minus_h;
            check(x[i]);
        }
        if(!integer_product(x,y,false,target))for(int i=0;i<r;++i)
            if(x[i].sign())for(const auto& entry:rows[i]){
                int j=entry.first;__gmpq_mul(&term.v,&entry.second.v,&x[i].v);check(term);
                __gmpq_add(&y[j].v,&y[j].v,&term.v);check(y[j]);
            }
        for(const auto& v:y){
            bool outside=false;
            if(__gmpq_cmp(&v.v,&two.v)>0){__gmpq_div(&ratio.v,&two.v,&v.v);outside=true;}
            else if(__gmpq_cmp(&v.v,&low.v)<0){__gmpq_div(&ratio.v,&low.v,&v.v);outside=true;}
            if(outside){check(ratio);if(__gmpq_cmp(&ratio.v,&scale.v)<0)scale=ratio;}
        }
        // Exact linearity gives (scale*x) B = scale*(x B). Repeating the
        // matrix product would add cost without strengthening this identity.
        for(auto& v:x){__gmpq_mul(&v.v,&v.v,&scale.v);check(v);}
        for(auto& v:y){__gmpq_mul(&v.v,&v.v,&scale.v);check(v);
            if(__gmpq_cmp(&v.v,&low.v)<0 || __gmpq_cmp(&v.v,&two.v)>0)throw 6;}
        bool resolved=__gmpq_cmp(&y[2*target+1].v,&quarter.v)>=0 ||
                      (opposite && __gmpq_cmp(&y[2*target].v,&quarter.v)>=0);
        bool dual=full || !resolved;
        if(dual){
            for(int j=0;j<s;++j){u[j].number(raw_u[j]);check(u[j]);
                __gmpq_mul(&term.v,&u[j].v,u[j].sign()>=0?&two.v:&low.v);check(term);
                __gmpq_add(&upper.v,&upper.v,&term.v);check(upper);}
            std::vector<Q> residuals(r);bool integers=integer_product(u,residuals,true,target);Q absolute;
            for(int i=0;i<r;++i){
                auto& residual=residuals[i];
                if(!integers){
                  for(const auto& entry:rows[i])if(entry.first==2*target+1)residual=entry.second;
                  for(const auto& entry:rows[i])if(u[entry.first].sign()){
                    __gmpq_mul(&term.v,&entry.second.v,&u[entry.first].v);check(term);
                    __gmpq_sub(&residual.v,&residual.v,&term.v);check(residual);}
                }
                absolute=residual;if(absolute.sign()<0)__gmpq_neg(&absolute.v,&absolute.v);
                __gmpq_mul(&term.v,&h.v,&absolute.v);check(term);
                __gmpq_add(&upper.v,&upper.v,&term.v);check(upper);
            }
        }
        if(Clock::now()>deadline)throw 1;
        if(compact){
            std::string labels(s/2,'0');
            for(int i=0;i<s/2;++i){
                if(__gmpq_cmp(&y[2*i+1].v,&quarter.v)>=0)labels[i]='+';
                else if(opposite && __gmpq_cmp(&y[2*i].v,&quarter.v)>=0)labels[i]='-';
            }
            if(dual && __gmpq_cmp(&upper.v,&quarter.v)<0){
                if(labels[target]=='+')throw 6;
                labels[target]='-';
            }
            return std::to_string(ops)+"\n"+std::to_string(peak)+"\n"+std::to_string(integer_products)+"\n"+labels+"\n";
        }
        std::string result=std::to_string(ops)+"\n"+std::to_string(peak)+"\n"+(dual?upper.str():"none")+"\n"+std::to_string(integer_products)+"\n";
        for(const auto& v:x)result+=v.str()+"\n";
        for(const auto& v:y)result+=v.str()+"\n";
        return result;
    }
};
}
extern "C" int sp_proof_create(int r,int s,const char** b,const char* h,const char* eps,
    uint64_t bits,int opposite,void** out){
    if(!out)return 4;
    *out=nullptr;
    if(r<1 || s<2 || s%2 || int64_t(r)*s>1000000 || !b || bits<8 || bits>1000000 || (opposite!=0&&opposite!=1))return 4;
    try{*out=new Context(r,s,b,h,eps,bits,opposite);return 0;}catch(int code){return code;}catch(...){return 7;}
}
static int checked(void* handle,int target,const double* x,const double* u,int full,
    uint64_t ns,uint64_t cap,char** out,bool compact){
    if(!out)return 4;
    *out=nullptr;
    if(!handle || !x || !u || ns==0 || ns>3600000000000ULL || (full!=0&&full!=1))return 4;
    auto* c=static_cast<Context*>(handle);
    if(target<0 || target>=c->s/2)return 4;
    for(int i=0;i<c->r;++i)if(!std::isfinite(x[i]))return 4;
    for(int i=0;i<c->s;++i)if(!std::isfinite(u[i]))return 4;
    try{auto result=c->prove(target,x,u,full,ns,cap,compact);*out=new char[result.size()+1];
        std::memcpy(*out,result.c_str(),result.size()+1);return 0;}catch(int code){return code;}catch(...){return 7;}
}
extern "C" int sp_proof_check(void* handle,int target,const double* x,const double* u,int full,
    uint64_t ns,uint64_t cap,char** out){return checked(handle,target,x,u,full,ns,cap,out,false);}
extern "C" int sp_proof_labels(void* handle,int target,const double* x,const double* u,int full,
    uint64_t ns,uint64_t cap,char** out){return checked(handle,target,x,u,full,ns,cap,out,true);}
extern "C" void sp_proof_free_string(char* s){delete[] s;}
extern "C" void sp_proof_destroy(void* handle){delete static_cast<Context*>(handle);}
