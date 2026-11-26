// Persistent exact auxiliary tableau. The origin is feasible by construction.
// A positive target can terminate early; negative labels require an optimum.
#include "gmp_abi.h"
#include <algorithm>
#include <chrono>
#include <cstdint>
#include <cstring>
#include <memory>
#include <stdexcept>
#include <string>
#include <vector>

namespace {
struct Rational {
    SpQ v;
    Rational(){__gmpq_init(&v);}
    explicit Rational(long x):Rational(){__gmpq_set_si(&v,x,1);}
    Rational(const Rational& x):Rational(){__gmpq_set(&v,&x.v);}
    Rational& operator=(const Rational& x){if(this!=&x)__gmpq_set(&v,&x.v);return *this;}
    ~Rational(){__gmpq_clear(&v);}
    void parse(const char* text){
        if(!text || std::strlen(text)>100000 || __gmpq_set_str(&v,text,10) || v.denominator.size==0)throw 4;
        __gmpq_canonicalize(&v);
    }
    int sign()const{return (v.numerator.size>0)-(v.numerator.size<0);}
    std::size_t bits()const{return std::max(__gmpz_sizeinbase(&v.numerator,2),__gmpz_sizeinbase(&v.denominator,2));}
    std::string str()const{
        std::vector<char> buffer(__gmpz_sizeinbase(&v.numerator,10)+__gmpz_sizeinbase(&v.denominator,10)+8);
        __gmpq_get_str(buffer.data(),10,&v);return buffer.data();
    }
};
using Clock=std::chrono::steady_clock;
struct Auxiliary {
    int m,r,n;std::size_t max_bits;
    std::vector<std::vector<Rational>> d;
    std::vector<int> basic,nonbasic;
    uint64_t operations=0,limit=0,pivots=0;Clock::time_point deadline;
    bool valid=true;
    Auxiliary(int rows,int variables,const char** a,const char** b,std::size_t bits):
        m(rows),r(variables),n(2*variables),max_bits(bits),d(m+1,std::vector<Rational>(n+1)),basic(m),nonbasic(n){
        if(std::strcmp(__gmp_version,"6.2.1"))throw 5;
        for(int j=0;j<n;++j)nonbasic[j]=j;
        for(int i=0;i<m;++i){
            basic[i]=n+i;d[i][n].parse(b[i]);if(d[i][n].sign()<0)throw 4;
            if(d[i][n].bits()>max_bits)throw 3;
            for(int j=0;j<r;++j){d[i][j].parse(a[i*r+j]);if(d[i][j].bits()>max_bits)throw 3;
                __gmpq_neg(&d[i][j+r].v,&d[i][j].v);}
        }
    }
    void check(const Rational& x){
        if(++operations>limit)throw 2;
        if(x.bits()>max_bits)throw 3;
        if((operations&1023)==0 && Clock::now()>deadline)throw 1;
    }
    void pivot(int row,int column){
        if(++pivots>4096)throw 2;
        Rational inverse(1),factor,product;
        __gmpq_div(&inverse.v,&inverse.v,&d[row][column].v);
        std::vector<int> entries;
        for(int j=0;j<=n;++j)if(j!=column && d[row][j].sign())entries.push_back(j);
        for(int i=0;i<=m;++i){
            if(i==row || !d[i][column].sign())continue;
            __gmpq_mul(&factor.v,&d[i][column].v,&inverse.v);
            for(int j:entries){__gmpq_mul(&product.v,&d[row][j].v,&factor.v);
                __gmpq_sub(&d[i][j].v,&d[i][j].v,&product.v);check(d[i][j]);}
        }
        for(int j:entries){__gmpq_mul(&d[row][j].v,&d[row][j].v,&inverse.v);check(d[row][j]);}
        __gmpq_neg(&inverse.v,&inverse.v);
        for(int i=0;i<=m;++i)if(i!=row){__gmpq_mul(&d[i][column].v,&d[i][column].v,&inverse.v);check(d[i][column]);}
        __gmpq_neg(&d[row][column].v,&inverse.v);std::swap(basic[row],nonbasic[column]);
    }
    std::string solve(const char** costs,uint64_t ns,uint64_t cap){
        if(!valid)throw 4;
        valid=false;operations=0;pivots=0;limit=cap;deadline=Clock::now()+std::chrono::nanoseconds(ns);
        std::vector<Rational> c(n);Rational product;
        for(int j=0;j<r;++j){c[j].parse(costs[j]);__gmpq_neg(&c[j+r].v,&c[j].v);check(c[j]);}
        for(int j=0;j<=n;++j){__gmpq_set_si(&d[m][j].v,0,1);
            if(j<n && nonbasic[j]<n)__gmpq_neg(&d[m][j].v,&c[nonbasic[j]].v);}
        for(int i=0;i<m;++i)if(basic[i]<n && c[basic[i]].sign()){
            for(int j=0;j<=n;++j)if(d[i][j].sign()){
                __gmpq_mul(&product.v,&c[basic[i]].v,&d[i][j].v);
                __gmpq_add(&d[m][j].v,&d[m][j].v,&product.v);check(d[m][j]);}}
        Rational threshold;__gmpq_set_si(&threshold.v,1,4);
        bool reached=false;
        for(;;){
            if(Clock::now()>deadline)throw 1;
            if(__gmpq_cmp(&d[m][n].v,&threshold.v)>=0){reached=true;break;}
            int entering=-1;
            for(int j=0;j<n;++j)if(d[m][j].sign()<0 && (entering<0 || nonbasic[j]<nonbasic[entering]))entering=j;
            if(entering<0)break;
            int leaving=-1;Rational ratio,best;
            for(int i=0;i<m;++i)if(d[i][entering].sign()>0){
                __gmpq_div(&ratio.v,&d[i][n].v,&d[i][entering].v);check(ratio);
                int compare=leaving<0?-1:__gmpq_cmp(&ratio.v,&best.v);
                if(compare<0 || (compare==0 && basic[i]<basic[leaving])){leaving=i;best=ratio;}}
            if(leaving<0)throw 6; // This interface is only for bounded auxiliaries.
            pivot(leaving,entering);
        }
        std::vector<Rational> x(n),y(m);
        for(int i=0;i<m;++i)if(basic[i]<n)x[basic[i]]=d[i][n];
        if(!reached)for(int j=0;j<n;++j)if(nonbasic[j]>=n)y[nonbasic[j]-n]=d[m][j];
        std::string result=std::string(reached?"feasible_target":"optimal")+"\n"+std::to_string(pivots)+"\n"+std::to_string(operations)+"\n";
        for(int j=0;j<r;++j){__gmpq_sub(&product.v,&x[j].v,&x[j+r].v);result+=product.str()+"\n";}
        for(const auto& v:y)result+=v.str()+"\n";
        result+=d[m][n].str()+"\n";valid=true;return result;
    }
};
}

extern "C" int sp_aux_create(int m,int r,const char** a,const char** b,uint64_t bits,void** out){
    if(!out)return 4;
    *out=nullptr;
    if(m<1 || r<1 || (int64_t(m)+1)*(2*int64_t(r)+1)>1000000 || !a || !b || bits<8 || bits>1000000)return 4;
    try{*out=new Auxiliary(m,r,a,b,bits);return 0;}catch(int code){return code;}catch(...){return 7;}
}
extern "C" int sp_aux_solve(void* handle,const char** c,uint64_t ns,uint64_t operations,char** out){
    if(!handle || !out || !c || !ns || ns>3600000000000ULL)return 4;
    *out=nullptr;
    try{auto text=static_cast<Auxiliary*>(handle)->solve(c,ns,operations);auto data=new char[text.size()+1];
        std::memcpy(data,text.c_str(),text.size()+1);*out=data;return 0;
    }catch(int code){return code;}catch(...){return 7;}
}
extern "C" void sp_aux_free_string(char* text){delete[] text;}
extern "C" void sp_aux_destroy(void* handle){delete static_cast<Auxiliary*>(handle);}

extern "C" int sp_rref(int m,int n,int columns,const char** values,uint64_t bits,uint64_t ns,uint64_t cap,char** out){
    if(!out)return 4;
    *out=nullptr;
    if(m<1 || n<1 || columns<0 || columns>n || int64_t(m)*n>1000000 || !values || !ns || ns>3600000000000ULL)return 4;
    try{
        if(std::strcmp(__gmp_version,"6.2.1"))throw 5;
        auto deadline=Clock::now()+std::chrono::nanoseconds(ns);uint64_t operations=0;
        auto check=[&](const Rational& value){
            if(++operations>cap)throw 2;
            if(value.bits()>bits)throw 3;
            if((operations&1023)==0 && Clock::now()>deadline)throw 1;
        };
        std::vector<std::vector<Rational>> rows(m,std::vector<Rational>(n));
        for(int i=0;i<m;++i)for(int j=0;j<n;++j){rows[i][j].parse(values[i*n+j]);check(rows[i][j]);}
        std::vector<int> pivots;Rational scale,product;
        for(int col=0;col<columns && int(pivots.size())<m;++col){
            if(Clock::now()>deadline)throw 1;
            int at=int(pivots.size()),chosen=at;
            while(chosen<m && !rows[chosen][col].sign())++chosen;
            if(chosen==m)continue;
            std::swap(rows[chosen],rows[at]);scale=rows[at][col];std::vector<int> entries;
            for(int j=col;j<n;++j)if(rows[at][j].sign()){
                __gmpq_div(&rows[at][j].v,&rows[at][j].v,&scale.v);check(rows[at][j]);entries.push_back(j);}
            for(int i=0;i<m;++i)if(i!=at && rows[i][col].sign()){
                scale=rows[i][col];
                for(int j:entries){__gmpq_mul(&product.v,&scale.v,&rows[at][j].v);
                    __gmpq_sub(&rows[i][j].v,&rows[i][j].v,&product.v);check(rows[i][j]);}}
            pivots.push_back(col);
        }
        std::string result=std::to_string(pivots.size())+"\n"+std::to_string(operations)+"\n";
        for(int pivot:pivots)result+=std::to_string(pivot)+"\n";
        for(const auto& row:rows)for(const auto& value:row)result+=value.str()+"\n";
        auto data=new char[result.size()+1];std::memcpy(data,result.c_str(),result.size()+1);*out=data;return 0;
    }catch(int code){return code;}catch(...){return 7;}
}
