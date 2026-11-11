// SPEC-0030: one CTA owns a coupled LP, with one warp per 32 output coordinates.
#include "helpers.cuh"
namespace integrated {
__device__ Pair pair(double v) { float h=float(v);return {h,float(v-double(h))}; }
__device__ float magnitude(Pair v) {return fabsf(v.h)+fabsf(v.l);}
__device__ Pair clamp_pair(Pair v,double lo,double hi,unsigned* ambiguous) {
    if(lo!=hi) {
        if(isfinite(lo)) {Pair d=add(v,neg(pair(lo)));if(magnitude(d)>0 && magnitude(d)<0x1p-43f*(1+magnitude(v))) *ambiguous=1;}
        if(isfinite(hi)) {Pair d=add(v,neg(pair(hi)));if(magnitude(d)>0 && magnitude(d)<0x1p-43f*(1+magnitude(v))) *ambiguous=1;}
    }
    if(isfinite(lo) && less(v,pair(lo)))v=pair(lo);
    if(isfinite(hi) && less(pair(hi),v))v=pair(hi);
    return v;
}
template<int F,int K> __device__ void body(
    const unsigned* matrix,const int* me,const unsigned* fragments,const unsigned* masks,
    const double* original,const double* params,unsigned* state,int* ex,double* raw,
    unsigned* flags,float* metrics,unsigned n,unsigned m,unsigned blocks,unsigned op,unsigned count,
    unsigned shift,double limit) {
    int tid=threadIdx.x,t=tid&31,w=tid/32,p=blocks*32;
    constexpr int stride=K*512*(F==16?2:1);
    __shared__ unsigned sc[5*4*K*F], status[4];
    __shared__ int se[5*4*K];
    __shared__ Pair dot[128];
    __shared__ float norms[8], terms[4][7];
    for(int i=tid;i<int(5*blocks*K*F);i+=blockDim.x)sc[i]=state[i];
    for(int i=tid;i<int(5*blocks*K);i+=blockDim.x)se[i]=ex[i];
    if(t==0)status[w]=flags[w];
    for(int i=t;i<7;i+=32)terms[w][i]=0;
    __syncthreads();
    if(op==0)for(int v=0;v<5;v++) {
        double x=raw[v*p+tid];
        fast::encode<F,K,true,true>(pair(x),sc+(v*blocks+w)*K*F,se+(v*blocks+w)*K,status+w);
    }
    if(op==3 || op==4) {
        bool tr=op==3;Pair acc={0,0};int v=tr?1:2;
        for(int b=0;b<int(blocks);b++) {int tile=tr?b*blocks+w:w*blocks+b;
            fast::product<F,K,8>(matrix+tile*K*32*F,me+tile*K,sc+(v*blocks+b)*K*F,
                se+(v*blocks+b)*K,tr,dot+w*32,fragments+tile*stride,masks[tile]);
            acc=add(acc,dot[tid]);__syncwarp();
        }
        raw[tid]=double(acc.h)+double(acc.l);
    }
    if(op==1)for(unsigned step=0;step<count;step++) {
        unsigned bad=0;for(int b=0;b<int(blocks);b++)bad|=status[b];
        if(bad)break;
        Pair old=fast::unpack<F,K>(sc+w*K*F,se+w*K,t);
        Pair y=fast::unpack<F,K>(sc+(blocks+w)*K*F,se+(blocks+w)*K,t);
        float yn=magnitude(y);yn=__uint_as_float(__reduce_max_sync(0xffffffff,__float_as_uint(yn)));
        if(t==0)norms[w]=yn;__syncthreads();
        float ynorm=0;for(int b=0;b<int(blocks);b++)ynorm=fmaxf(ynorm,norms[b]);
        Pair at={0,0};
        for(int b=0;b<int(blocks);b++) {
            int tile=b*blocks+w;
            fast::product<F,K,8>(matrix+tile*K*32*F,me+tile*K,sc+(blocks+b)*K*F,
                se+(blocks+b)*K,true,dot+w*32,fragments+tile*stride,masks[tile]);
            at=add(at,dot[tid]);__syncwarp();
        }
        unsigned ambiguous=0;
        Pair x=tid<int(n)?clamp_pair(add(old,fast::power(add(at,neg(pair(params[tid]))),-int(shift))),
                                                params[p+tid],params[2*p+tid],&ambiguous):Pair{0,0};
        Pair bar=add(fast::power(x,1),neg(old));
        fast::encode<F,K,true,true>(x,sc+w*K*F,se+w*K,status+w);
        Pair sx=fast::unpack<F,K>(sc+w*K*F,se+w*K,t);
        float encoding_x=magnitude(add(x,neg(sx)));
        fast::encode<F,K,true,true>(bar,sc+(2*blocks+w)*K*F,se+(2*blocks+w)*K,status+w);
        Pair sb=fast::unpack<F,K>(sc+(2*blocks+w)*K*F,se+(2*blocks+w)*K,t);
        float encoding_bar=magnitude(add(bar,neg(sb)));
        float bn=magnitude(sb);bn=__uint_as_float(__reduce_max_sync(0xffffffff,__float_as_uint(bn)));
        if(t==0)norms[4+w]=bn;__syncthreads();
        float bnorm=0;for(int b=0;b<int(blocks);b++)bnorm=fmaxf(bnorm,norms[4+b]);
        Pair ab={0,0};
        for(int b=0;b<int(blocks);b++) {
            int tile=w*blocks+b;
            fast::product<F,K,8>(matrix+tile*K*32*F,me+tile*K,sc+(2*blocks+b)*K*F,
                se+(2*blocks+b)*K,false,dot+w*32,fragments+tile*stride,masks[tile]);
            ab=add(ab,dot[tid]);__syncwarp();
        }
        Pair v=add(y,neg(fast::power(ab,-int(shift))));
        double tau=ldexp(1.,-int(shift));
        Pair clipped=clamp_pair(v,-tau*params[4*p+tid],-tau*params[3*p+tid],&ambiguous);
        v=tid<int(m)?add(v,neg(clipped)):Pair{0,0};
        fast::encode<F,K,true,true>(v,sc+(blocks+w)*K*F,se+(blocks+w)*K,status+w);
        Pair sy=fast::unpack<F,K>(sc+(blocks+w)*K*F,se+(blocks+w)*K,t);
        float encoding_y=magnitude(add(v,neg(sy)));
        float dt=ldexpf(1.f,-int(shift)), na=float(params[5*p]);
        float local[7];
        // Operational estimates; instruction zero is admitted empirical evidence,
        // never a claim of a proved global error enclosure. No pairs are discarded.
        local[0]=dt*(float(params[5*p+3])*ynorm*(1+2*dt*na)+float(params[5*p+2])*bnorm);
        local[1]=0;
        local[2]=0x1p-42f*(1+magnitude(at)+magnitude(ab)+magnitude(old)+magnitude(y))*(1+2*dt*na);
        local[3]=float(params[5*p+4])*dt*(1+2*dt*na);
        local[4]=float(params[5*p+4])*4;
        local[5]=encoding_x*(1+2*dt*na)+encoding_y+dt*na*encoding_bar;
        local[6]=0;
        float total=0;
        for(int j=0;j<7;j++) {
            float worst=__uint_as_float(__reduce_max_sync(0xffffffff,__float_as_uint(local[j])));
            if(t==0)terms[w][j]=fmaxf(terms[w][j],worst);
            total+=worst;
        }
        if(t==0 && status[w]==0 && (!isfinite(total)||total>float(limit)))status[w]=3;
        if(__any_sync(0xffffffff,ambiguous!=0))if(t==0 && status[w]==0)status[w]=5;
        __syncthreads();
        if(tid==0)flags[4]++;
        __syncthreads();
    }
    __syncthreads();
    if(op==2)for(int v=0;v<5;v++) {
        Pair x=fast::unpack<F,K>(sc+(v*blocks+w)*K*F,se+(v*blocks+w)*K,t);
        raw[v*p+tid]=double(x.h)+double(x.l);
    }
    for(int i=tid;i<int(5*blocks*K*F);i+=blockDim.x)state[i]=sc[i];
    for(int i=tid;i<int(5*blocks*K);i+=blockDim.x)ex[i]=se[i];
    if(t==0) {flags[w]=status[w];for(int j=0;j<7;j++)metrics[w*7+j]=terms[w][j];}
}
__device__ void native(const double* a,const double* cb,double* raw,unsigned* flags,
                      unsigned n,unsigned m,unsigned blocks,unsigned op,unsigned count,unsigned shift) {
    int i=threadIdx.x,p=blocks*32;
    __shared__ double s[5*128];
    int nnz=int(cb[5*p+5]);
    const double *rows=a+p*p, *cols=rows+p+1+2*nnz;
    const double *ri=rows+p+1,*rv=ri+nnz,*ci=cols+p+1,*cv=ci+nnz;
    for(int v=0;v<5;v++)s[v*p+i]=raw[v*p+i];
    __syncthreads();
    if(op==1)for(unsigned step=0;step<count;step++) {
        double dot=0;for(int j=int(cols[i]);j<int(cols[i+1]);j++)dot+=cv[j]*s[p+int(ci[j])];
        double old=s[i],u=i<int(n)?fmin(cb[2*p+i],fmax(cb[p+i],old+ldexp(dot-cb[i],-int(shift)))):0;
        __syncthreads();s[i]=u;s[2*p+i]=2*u-old;__syncthreads();
        dot=0;for(int j=int(rows[i]);j<int(rows[i+1]);j++)dot+=rv[j]*s[2*p+int(ri[j])];
        double v=s[p+i]-ldexp(dot,-int(shift));
        s[p+i]=i<int(m)?v-fmin(-ldexp(cb[3*p+i],-int(shift)),fmax(-ldexp(cb[4*p+i],-int(shift)),v)):0;
        if(__any_sync(0xffffffff,!isfinite(s[i])||!isfinite(s[p+i])))if((i&31)==0)flags[i/32]=1;
        __syncthreads();if(i==0)flags[4]++;__syncthreads();
    }
    for(int v=0;v<5;v++)raw[v*p+i]=s[v*p+i];
    if(op==3||op==4) {double dot=0;bool tr=op==3;
        const double *offset=tr?cols:rows,*index=tr?ci:ri,*value=tr?cv:rv;
        for(int j=int(offset[i]);j<int(offset[i+1]);j++)dot+=value[j]*s[(tr?1:2)*p+int(index[j])];raw[i]=dot;}

}
}
#define IPARAM const unsigned* a,const int* ae,const unsigned* fr,const unsigned* masks,const double* orig,const double* cb,unsigned* s,int* se,double* raw,unsigned* flags,float* metrics,unsigned n,unsigned m,unsigned blocks,unsigned op,unsigned count,unsigned shift,double limit
#define IK(F,K) extern "C" __global__ void integrate_##F##_##K(IPARAM) {integrated::body<F,K>(a,ae,fr,masks,orig,cb,s,se,raw,flags,metrics,n,m,blocks,op,count,shift,limit);}
IK(4,2)
IK(4,4)
IK(4,8)
IK(8,4)
IK(16,2)
extern "C" __global__ void integrate_64_1(IPARAM) {integrated::native(orig,cb,raw,flags,n,m,blocks,op,count,shift);}
#define PREPARE(F,K) extern "C" __global__ void iprepare_##F##_##K(const unsigned* a,unsigned* f,unsigned* m) {fast::prepare<F,K>(a,f,m);}
PREPARE(4,2)
PREPARE(4,4)
PREPARE(4,8)
PREPARE(8,4)
PREPARE(16,2)
extern "C" __global__ void checkpoint(const unsigned* cs,const int* ce,const double* cr,
 unsigned* s,int* e,double* r,unsigned ns,unsigned ne,unsigned nr) {
 unsigned i=blockIdx.x*blockDim.x+threadIdx.x;
 if(i<ns)s[i]=cs[i];if(i<ne)e[i]=ce[i];if(i<nr)r[i]=cr[i];
}
