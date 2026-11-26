// Rigorous binary64 enclosures of the unchanged rational proposal tests.
// Every uncertain decision is returned to the exact GMP checker.
#include <algorithm>
#include <cfenv>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <limits>
#include <vector>
#include <xmmintrin.h>

namespace {
struct I { double lo=0,hi=0; };
double down(double x){return std::nextafter(x,-std::numeric_limits<double>::infinity());}
double up(double x){return std::nextafter(x,std::numeric_limits<double>::infinity());}
I add(I a,I b){
    if(a.lo==0&&a.hi==0)return b;
    if(b.lo==0&&b.hi==0)return a;
    return {down(a.lo+b.lo),up(a.hi+b.hi)};
}
I mul(I a,double b){
    if(b==0 || (a.lo==0&&a.hi==0))return {};
    return b>0?I{down(a.lo*b),up(a.hi*b)}:I{down(a.hi*b),up(a.lo*b)};
}
I positive_product(I a,I b){
    return {std::max(0.0,down(a.lo*b.lo)),up(a.hi*b.hi)};
}
I absolute(I a){
    if(a.lo>=0)return a;
    if(a.hi<=0)return {-a.hi,-a.lo};
    return {0,std::max(-a.lo,a.hi)};
}
bool finite(I a){return std::isfinite(a.lo)&&std::isfinite(a.hi)&&a.lo<=a.hi;}
struct Entry {int j;I value;};
using Clock=std::chrono::steady_clock;
struct Context {
    int r,s;I h,eps;bool opposite;
    std::vector<std::vector<Entry>> rows;
    std::vector<I> y;
    uint64_t operations=0,cap=0;Clock::time_point deadline;
    Context(int r_,int s_,const double* lo,const double* hi,I h_,I e_,bool opposite_):
        r(r_),s(s_),h(h_),eps(e_),opposite(opposite_),rows(r),y(s){
        for(int i=0;i<r;++i)for(int j=0;j<s;++j){
            I a{lo[size_t(i)*s+j],hi[size_t(i)*s+j]};
            if(!finite(a))throw 4;
            if(a.lo!=0 || a.hi!=0)rows[i].push_back({j,a});
        }
    }
    void tick(uint64_t n=1){
        operations+=n;if(operations>cap)throw 2;
        if((operations&255)<n && Clock::now()>deadline)throw 1;
    }
    // Return the original checker's scaled-product enclosure. The scale interval
    // encloses its exact minimum of all upper/lower constraint ratios.
    bool primal(const double* x){
        std::fill(y.begin(),y.end(),I{});
        for(int i=0;i<r;++i){
            if(!std::isfinite(x[i]) || std::abs(x[i])>h.lo)return false;
            if(x[i]!=0)for(const auto& e:rows[i]){y[e.j]=add(y[e.j],mul(e.value,x[i]));tick(4);}
        }
        I scale{1,1};
        for(I a:y){
            if(!finite(a))return false;
            if(a.hi>2)scale.lo=std::min(scale.lo,std::max(0.0,down(2/a.hi)));
            if(a.lo>2)scale.hi=std::min(scale.hi,up(2/a.lo));
            if(a.lo < -eps.lo)scale.lo=std::min(scale.lo,std::max(0.0,down(eps.lo/(-a.lo))));
            if(a.hi < -eps.hi)scale.hi=std::min(scale.hi,up(eps.hi/(-a.hi)));
            tick(4);
        }
        if(!finite(scale)||scale.lo<0||scale.hi>1)return false;
        for(auto& a:y){
            if(a.lo>=0)a=positive_product(a,scale);
            else if(a.hi<=0){I v=positive_product({-a.hi,-a.lo},scale);a={-v.hi,-v.lo};}
            else a={down(a.lo*scale.hi),up(a.hi*scale.hi)};
            if(!finite(a))return false;
            tick(2);
        }
        return true;
    }
    I dual(int target,const double* u){
        I result;
        for(int j=0;j<s;++j){
            if(!std::isfinite(u[j]))return {0,std::numeric_limits<double>::infinity()};
            result=add(result,u[j]>=0?mul({2,2},u[j]):mul(eps,-u[j]));tick(4);
        }
        for(int i=0;i<r;++i){
            I residual;
            for(const auto& e:rows[i]){
                if(e.j==2*target+1)residual=add(residual,e.value);
                residual=add(residual,mul(e.value,-u[e.j]));tick(4);
            }
            if(!finite(residual))return {0,std::numeric_limits<double>::infinity()};
            result=add(result,positive_product(absolute(residual),h));tick(4);
            // All following support and absolute-residual contributions are
            // nonnegative. This exact-test rejection cannot become acceptance.
            if(result.lo>=.25)break;
        }
        return result;
    }
};
}

extern "C" int sp_interval_create(int r,int s,const double* lo,const double* hi,
    double hl,double hh,double el,double eh,int opposite,void** output){
    if(!output)return 4;*output=nullptr;
    if(r<1||s<2||s%2||int64_t(r)*s>1000000||!lo||!hi||!finite({hl,hh})||!finite({el,eh})||
       hl<=0||el<=0||eh>=.25||(opposite!=0&&opposite!=1))return 4;
    try{*output=new Context(r,s,lo,hi,{hl,hh},{el,eh},opposite);return 0;}
    catch(int code){return code;}catch(...){return 7;}
}

extern "C" int sp_interval_batch(void* handle,int width,const int* targets,const int* active,
    const double* x,const double* u,const int* known,int* labels,int* uncertain,
    uint64_t ns,uint64_t cap,uint64_t* statistics){
    if(!handle||width<1||width>4096||!targets||!active||!x||!u||!known||!labels||!uncertain||
       !statistics||!ns||ns>3600000000000ULL)return 4;
    auto* c=static_cast<Context*>(handle);c->operations=0;c->cap=cap;c->deadline=Clock::now()+std::chrono::nanoseconds(ns);
    std::fill(statistics,statistics+4,0);
    for(int i=0;i<c->s/2;++i){if(known[i]<-1||known[i]>1)return 4;labels[i]=known[i];}
    for(int q=0;q<width;++q){if(targets[q]<0||targets[q]>=c->s/2||(active[q]!=0&&active[q]!=1))return 4;uncertain[q]=0;}
    try{
        bool environment=std::fegetround()==FE_TONEAREST && (_mm_getcsr()&((1u<<15)|(1u<<6)))==0;
        for(int q=0;q<width;++q){
            int target=targets[q];if(!active[q]||labels[target])continue;
            ++statistics[1];
            bool valid=true;
            for(int j=0;j<c->s;++j)valid=valid&&std::isfinite(u[size_t(q)*c->s+j]);
            if(!environment||!valid||!c->primal(x+size_t(q)*c->r)){uncertain[q]=1;++statistics[2];continue;}
            bool ambiguous=false;
            for(int i=0;i<c->s/2;++i){
                if(labels[i])continue;
                I p=c->y[2*i+1],n=c->y[2*i];
                if(p.lo>=.25)labels[i]=1;
                else if(c->opposite&&n.lo>=.25)labels[i]=-1;
                else if(p.hi>=.25||(c->opposite&&n.hi>=.25))ambiguous=true;
            }
            if(!labels[target]){
                I bound=c->dual(target,u+size_t(q)*c->s);
                if(finite(bound)&&bound.hi<.25){labels[target]=-1;++statistics[3];}
                else if(!(bound.lo>=.25))ambiguous=true;
            }
            if(ambiguous){uncertain[q]=1;++statistics[2];}
        }
        statistics[0]=c->operations;
        if(Clock::now()>c->deadline)throw 1;
        return 0;
    }catch(int code){statistics[0]=c->operations;return code;}catch(...){return 7;}
}
extern "C" void sp_interval_destroy(void* handle){delete static_cast<Context*>(handle);}
