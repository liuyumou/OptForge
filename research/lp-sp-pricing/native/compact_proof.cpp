// Streaming outward-rounded proposal checks. No matrix is retained.
#include <algorithm>
#include <cfenv>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <limits>
#include <vector>
#include <xmmintrin.h>
namespace {
struct I {double lo=0,hi=0;};
double down(double x){return std::nextafter(x,-std::numeric_limits<double>::infinity());}
double up(double x){return std::nextafter(x,std::numeric_limits<double>::infinity());}
bool finite(I x){return std::isfinite(x.lo)&&std::isfinite(x.hi)&&x.lo<=x.hi;}
I add(I a,I b){if(a.lo==0&&a.hi==0)return b;if(b.lo==0&&b.hi==0)return a;return {down(a.lo+b.lo),up(a.hi+b.hi)};}
I mul(I a,double b){if(!b||(a.lo==0&&a.hi==0))return {};return b>0?I{down(a.lo*b),up(a.hi*b)}:I{down(a.hi*b),up(a.lo*b)};}
I absval(I a){if(a.lo>=0)return a;if(a.hi<=0)return {-a.hi,-a.lo};return {0,std::max(-a.lo,a.hi)};}
I positive(I a,I b){return {std::max(0.,down(a.lo*b.lo)),up(a.hi*b.hi)};}
using Clock=std::chrono::steady_clock;
struct Proof {
    int r,s,target=0,row0=-1,nr=0;I h,eps,bound;bool opposite,uncertain=false,environment=false;
    const double *x=nullptr,*u=nullptr;std::vector<I> y,residual;
    uint64_t operations=0,cap=0;Clock::time_point deadline;
    Proof(int r_,int s_,I h_,I eps_,bool opposite_):r(r_),s(s_),h(h_),eps(eps_),opposite(opposite_),y(s_){}
    void tick(){if(++operations>cap)throw 2;if((operations&1023)==0&&Clock::now()>deadline)throw 1;}
};
}
extern "C" int sp_compact_proof_create(int r,int s,double hl,double hh,double el,double eh,int opposite,void** out){
    if(!out)return 4;*out=nullptr;
    if(r<1||s<2||s%2||s>2000000||!finite({hl,hh})||!finite({el,eh})||hl<=0||el<=0||eh>=.25||(opposite!=0&&opposite!=1))return 4;
    try{*out=new Proof(r,s,{hl,hh},{el,eh},opposite);return 0;}catch(...){return 7;}}
extern "C" int sp_compact_proof_begin(void* handle,int target,const double* x,const double* u,uint64_t ns,uint64_t cap){
    if(!handle||!x||!u||!ns||ns>3600000000000ULL)return 4;auto* p=static_cast<Proof*>(handle);
    if(target<0||target>=p->s/2)return 4;p->target=target;p->x=x;p->u=u;p->operations=0;p->cap=cap;
    p->deadline=Clock::now()+std::chrono::nanoseconds(ns);p->uncertain=false;p->row0=-1;
    p->environment=std::fegetround()==FE_TONEAREST&&(_mm_getcsr()&((1u<<15)|(1u<<6)))==0;
    for(int i=0;i<p->r;++i)if(!std::isfinite(x[i])||std::abs(x[i])>p->h.lo)p->environment=false;
    for(int j=0;j<p->s;++j)if(!std::isfinite(u[j]))p->environment=false;
    std::fill(p->y.begin(),p->y.end(),I{});p->bound={};return 0;}
extern "C" int sp_compact_proof_tile(void* handle,int phase,int row,int col,int nr,int nc,const double* lo,const double* hi){
    if(!handle||!lo||!hi||(phase!=0&&phase!=1)||nr<1||nc<1)return 4;auto* p=static_cast<Proof*>(handle);
    if(row<0||col<0||row+nr>p->r||col+nc>p->s)return 4;
    if(!p->environment)return 0;
    try{
        if(phase&&p->row0!=row){
            if(p->row0>=0)for(I a:p->residual)p->bound=add(p->bound,positive(absval(a),p->h));
            p->row0=row;p->nr=nr;p->residual.assign(nr,I{});
        }
        if(phase&&p->nr!=nr)return 4;
        for(int i=0;i<nr;++i)for(int j=0;j<nc;++j){I a{lo[size_t(i)*nc+j],hi[size_t(i)*nc+j]};
            if(!finite(a))return 4;if(a.lo==0&&a.hi==0)continue;
            if(!phase)p->y[col+j]=add(p->y[col+j],mul(a,p->x[row+i]));
            else {if(col+j==2*p->target+1)p->residual[i]=add(p->residual[i],a);
                p->residual[i]=add(p->residual[i],mul(a,-p->u[col+j]));}p->tick();}
        return 0;
    }catch(int c){return c;}catch(...){return 7;}}
extern "C" int sp_compact_proof_finish(void* handle,int phase,int* labels,int* uncertain,uint64_t* operations){
    if(!handle||!labels||!uncertain||!operations||(phase!=0&&phase!=1))return 4;auto* p=static_cast<Proof*>(handle);
    for(int i=0;i<p->s/2;++i)if(labels[i]<-1||labels[i]>1)return 4;
    try{
        if(!p->environment)p->uncertain=true;
        else if(!phase){
            I scale{1,1};
            for(I a:p->y){if(!finite(a)){p->uncertain=true;break;}
                if(a.hi>2)scale.lo=std::min(scale.lo,std::max(0.,down(2/a.hi)));
                if(a.lo>2)scale.hi=std::min(scale.hi,up(2/a.lo));
                if(a.lo < -p->eps.lo)scale.lo=std::min(scale.lo,std::max(0.,down(p->eps.lo/-a.lo)));
                if(a.hi < -p->eps.hi)scale.hi=std::min(scale.hi,up(p->eps.hi/-a.hi));p->tick();}
            if(!p->uncertain){
                for(auto& a:p->y){
                    if(a.lo>=0)a=positive(a,scale);
                    else if(a.hi<=0){auto v=positive({-a.hi,-a.lo},scale);a={-v.hi,-v.lo};}
                    else a={down(a.lo*scale.hi),up(a.hi*scale.hi)};
                    if(!finite(a))p->uncertain=true;
                }
                // A nonfinite product never establishes a label.
                if(!p->uncertain)for(int i=0;i<p->s/2;++i){if(labels[i])continue;
                    I positive=p->y[2*i+1],negative=p->y[2*i];
                    if(positive.lo>=.25)labels[i]=1;
                    else if(p->opposite&&negative.lo>=.25)labels[i]=-1;
                    else if(positive.hi>=.25||(p->opposite&&negative.hi>=.25))p->uncertain=true;}
            }
        }else{
            if(p->row0>=0)for(I a:p->residual)p->bound=add(p->bound,positive(absval(a),p->h));
            p->row0=-1;
            for(int j=0;j<p->s;++j){double u=p->u[j];p->bound=add(p->bound,u>=0?mul({2,2},u):mul(p->eps,-u));p->tick();}
            if(finite(p->bound)&&p->bound.hi<.25)labels[p->target]=-1;
            else if(!(p->bound.lo>=.25))p->uncertain=true;
        }
        *uncertain=p->uncertain;*operations=p->operations;
        if(Clock::now()>p->deadline)return 1;return 0;
    }catch(int c){*operations=p->operations;return c;}catch(...){return 7;}}
extern "C" int sp_compact_proof_sparse(void* handle,int phase,int row,int col,int nr,int nc,int nnz,
    const int* offsets,const int* indices,const double* lo,const double* hi){
    if(!handle||!offsets||!indices||!lo||!hi||(phase!=0&&phase!=1)||nr<1||nc<1||nnz<0||nnz>131072)return 4;
    auto* p=static_cast<Proof*>(handle);
    if(row<0||col<0||row+nr>p->r||col+nc>p->s||offsets[0]!=0||offsets[nr]!=nnz)return 4;
    for(int i=0;i<nr;++i)if(offsets[i]<0||offsets[i]>offsets[i+1])return 4;
    if(!p->environment)return 0;
    try{
        if(phase&&p->row0!=row){
            if(p->row0>=0)for(I a:p->residual)p->bound=add(p->bound,positive(absval(a),p->h));
            p->row0=row;p->nr=nr;p->residual.assign(nr,I{});
        }
        if(phase&&p->nr!=nr)return 4;
        for(int i=0;i<nr;++i)for(int k=offsets[i];k<offsets[i+1];++k){
            int j=indices[k];I a{lo[k],hi[k]};if(j<0||j>=nc||!finite(a))return 4;
            if(!phase)p->y[col+j]=add(p->y[col+j],mul(a,p->x[row+i]));
            else{if(col+j==2*p->target+1)p->residual[i]=add(p->residual[i],a);
                p->residual[i]=add(p->residual[i],mul(a,-p->u[col+j]));}p->tick();
        }
        return 0;
    }catch(int c){return c;}catch(...){return 7;}}
extern "C" void sp_compact_proof_destroy(void* handle){delete static_cast<Proof*>(handle);}
