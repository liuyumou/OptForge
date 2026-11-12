// SPEC-0031: FP4 tensor products with explicitly retained FP32-pair corrections.
#include "helpers.cuh"
namespace accel {
constexpr int N=512, B=N/32;
__device__ Pair pair(double x) {float h=float(x);return {h,float(x-double(h))};}
__device__ float mag(Pair x) {return fabsf(x.h)+fabsf(x.l);}
__device__ Pair mul(Pair a,Pair b) {
    float h=__fmul_rn(a.h,b.h);
    float l=__fmaf_rn(a.h,b.h,-h);
    l=__fmaf_rn(a.h,b.l,l);l=__fmaf_rn(a.l,b.h,l);l=__fmaf_rn(a.l,b.l,l);
    return add({h,0},{l,0});
}
__device__ Pair clip(Pair x,double lo,double hi,unsigned* ambiguous) {
    if(lo!=hi)for(int k=0;k<2;k++) {
        double v=k?hi:lo;
        if(isfinite(v)) {Pair d=add(x,neg(pair(v)));
            if(mag(d)>0 && mag(d)<0x1p-43f*(1+mag(x))) *ambiguous=1;
        }
    }
    if(isfinite(lo)&&less(x,pair(lo)))x=pair(lo);
    if(isfinite(hi)&&less(pair(hi),x))x=pair(hi);
    return x;
}
template<int K,bool Recenter=false> __device__ Pair product(bool tr,int i,int p,int blocks,
 const unsigned* a,const int* ae,const unsigned* fr,const unsigned* masks,
 const Pair* original,const Pair* error,bool has_error,const unsigned* sc,const int* se,
 const Pair* q,const Pair* rem,Pair* dot) {
    int w=i/32;Pair value={0,0};
    for(int b=0;b<blocks;b++) {
        int tile=tr?b*blocks+w:w*blocks+b;
        fast::product<4,K,8>(a+tile*K*128,ae+tile*K,sc+b*K*4,se+b*K,tr,
                            dot+w*32,fr+tile*K*512,masks[tile]);
        value=add(value,dot[i]);__syncwarp();
    }
    if constexpr(Recenter)return add(value,q[i]);
    else {
        Pair correction={0,0};int offset=tr?p*p:0;
        for(int j=0;j<p;j++) {
            correction=add(correction,mul(original[offset+j*p+i],rem[j]));
            if(has_error)correction=add(correction,mul(error[offset+j*p+i],q[j]));
        }
        return add(value,correction);
    }
}
template<int K,bool Recenter=false> __device__ void body(const unsigned* a,const int* ae,const unsigned* fr,
 const unsigned* masks,const Pair* original,const Pair* error,const double* exact,const double* cb,
 unsigned* state,int* ex,Pair* values,double* raw,unsigned* flags,float* metrics,
 unsigned n,unsigned m,unsigned blocks,unsigned op,unsigned count,unsigned shift,
 double limit,unsigned has_error) {
    int i=threadIdx.x,t=i&31,w=i/32,p=blocks*32;
    __shared__ unsigned sc[3*B*K*4],status[B];
    __shared__ int se[3*B*K];
    __shared__ Pair v[3*N],q[2*N],rem[2*N],dot[N];
    __shared__ float terms[B][8];
    __shared__ float norms[4*B];
    for(int j=i;j<int(3*blocks*K*4);j+=blockDim.x)sc[j]=state[j];
    for(int j=i;j<int(3*blocks*K);j+=blockDim.x)se[j]=ex[j];
    for(int j=0;j<3;j++)v[j*p+i]=values[j*p+i];
    if(t==0)status[w]=0;
    for(int j=t;j<8;j+=32)terms[w][j]=0;
    __syncthreads();
    if(op==0)for(int j=0;j<5;j++) {
        Pair x=pair(raw[j*p+i]);values[j*p+i]=x;
        if(j<3) {v[j*p+i]=x;fast::encode<4,K,true,true>(x,sc+(j*blocks+w)*K*4,se+(j*blocks+w)*K,status+w);}
    }
    for(int j=0;j<2;j++) {
        q[j*p+i]=fast::unpack<4,K>(sc+((j+1)*blocks+w)*K*4,se+((j+1)*blocks+w)*K,t);
        rem[j*p+i]=add(v[(j+1)*p+i],neg(q[j*p+i]));
    }
    __syncthreads();
    if constexpr(Recenter)if(op==1||op==3||op==4) {
        // One original-coefficient FP64 reference pair per <=32-update window.
        // Ordinary updates apply FP4 to increments about these resident anchors.
        double at=0,ax=0;
        for(int j=0;j<p;j++) {
            at+=exact[p*p+j*p+i]*(double(v[p+j].h)+double(v[p+j].l));
            ax+=exact[j*p+i]*(double(v[j].h)+double(v[j].l));
        }
        q[i]=pair(at);q[p+i]=pair(ax);rem[i]=v[p+i];rem[p+i]=v[i];
        fast::encode<4,K,true,true>(Pair{0,0},sc+(blocks+w)*K*4,se+(blocks+w)*K,status+w);
        fast::encode<4,K,true,true>(add(v[2*p+i],neg(rem[p+i])),sc+(2*blocks+w)*K*4,se+(2*blocks+w)*K,status+w);
        __syncthreads();
    }
    if(op==3||op==4) {
        int j=op==3?0:1;
        Pair d=product<K,Recenter>(op==3,i,p,blocks,a,ae,fr,masks,original,error,has_error,
                         sc+(j+1)*blocks*K*4,se+(j+1)*blocks*K,q+j*p,rem+j*p,dot);
        raw[i]=double(d.h)+double(d.l);
    }
    if(op==1)for(unsigned step=0;step<count;step++) {
        unsigned bad=0;for(int b=0;b<int(blocks);b++)bad|=status[b];if(bad)break;
        Pair old=v[i],y=v[p+i];
        Pair dy=Recenter?add(y,neg(rem[i])):Pair{0,0};
        float ey=Recenter?mag(add(dy,neg(fast::unpack<4,K>(sc+(blocks+w)*K*4,se+(blocks+w)*K,t)))):0;
        Pair at=product<K,Recenter>(true,i,p,blocks,a,ae,fr,masks,original,error,has_error,
                          sc+blocks*K*4,se+blocks*K,q,rem,dot);
        unsigned ambiguous=0;
        Pair x=i<int(n)?clip(add(old,fast::power(add(at,neg(pair(cb[i]))),-int(shift))),cb[p+i],cb[2*p+i],&ambiguous):Pair{0,0};
        Pair bar=add(fast::power(x,1),neg(old));v[i]=x;v[2*p+i]=bar;
        if constexpr(!Recenter)fast::encode<4,K,true,true>(x,sc+w*K*4,se+w*K,status+w);
        Pair db=Recenter?add(bar,neg(rem[p+i])):bar;
        fast::encode<4,K,true,true>(db,sc+(2*blocks+w)*K*4,se+(2*blocks+w)*K,status+w);
        Pair qb=fast::unpack<4,K>(sc+(2*blocks+w)*K*4,se+(2*blocks+w)*K,t);
        float eb=mag(add(db,neg(qb)));
        if constexpr(!Recenter) {q[p+i]=qb;rem[p+i]=add(bar,neg(qb));}
        __syncthreads();
        Pair ab=product<K,Recenter>(false,i,p,blocks,a,ae,fr,masks,original,error,has_error,
                          sc+2*blocks*K*4,se+2*blocks*K,q+p,rem+p,dot);
        Pair ny=add(y,neg(fast::power(ab,-int(shift))));double dt=ldexp(1.,-int(shift));
        ny=i<int(m)?add(ny,neg(clip(ny,-dt*cb[4*p+i],-dt*cb[3*p+i],&ambiguous))):Pair{0,0};
        // Finish every read of the previous y before replacing its representation.
        __syncthreads();v[p+i]=ny;
        fast::encode<4,K,true,true>(Recenter?add(ny,neg(rem[i])):ny,sc+(blocks+w)*K*4,se+(blocks+w)*K,status+w);
        if constexpr(!Recenter){q[i]=fast::unpack<4,K>(sc+(blocks+w)*K*4,se+(blocks+w)*K,t);rem[i]=add(ny,neg(q[i]));}
        float na=fmaxf(float(cb[5*p]),float(cb[5*p+1])),d=float(dt);
        float tail=fmaxf(mag(rem[i]),mag(rem[p+i]));
        // Operational estimates; correction terms are included, never global proofs.
        float local[8]={0x1p-43f*d*(na*tail+float(cb[5*p+3])*(mag(q[i])+mag(q[p+i]))),0,
            0x1p-42f*(1+mag(at)+mag(ab)+mag(old)+mag(y))*(1+2*d*na),
            float(cb[5*p+2])*d*(1+2*d*na),float(cb[5*p+2])*4,0,0,tail};
        if constexpr(Recenter) {
            float local_norm[4]={mag(dy),mag(db),ey,eb};
            for(int j=0;j<4;j++) {float worst=__uint_as_float(__reduce_max_sync(0xffffffff,__float_as_uint(local_norm[j])));if(t==0)norms[j*blocks+w]=worst;}
            __syncthreads();float global[4]={0,0,0,0};
            for(int j=0;j<4;j++)for(int b=0;b<int(blocks);b++)global[j]=fmaxf(global[j],norms[j*blocks+b]);
            local[0]=d*float(cb[5*p+3])*(global[0]*(1+2*d*na)+global[1]);
            local[5]=d*na*(global[2]*(1+2*d*na)+global[3]);
            local[7]=fmaxf(global[2],global[3]);
            __syncthreads();
        }
        float total=0;
        for(int j=0;j<8;j++) {
            float worst=__uint_as_float(__reduce_max_sync(0xffffffff,__float_as_uint(local[j])));
            if(t==0)terms[w][j]=fmaxf(terms[w][j],worst);
            if(j<7)total+=worst;
        }
        if(t==0 && status[w]==0 && (!isfinite(total)||total>float(limit)))status[w]=3;
        if(__any_sync(0xffffffff,ambiguous!=0))if(t==0&&status[w]==0)status[w]=5;
        __syncthreads();if(i==0)flags[blocks]++;__syncthreads();
    }
    __syncthreads();
    if constexpr(Recenter)for(int j=0;j<3;j++)fast::encode<4,K,true,true>(v[j*p+i],sc+(j*blocks+w)*K*4,se+(j*blocks+w)*K,status+w);
    // Canonical encoding is warp-owned; striped export reads other warps.
    __syncthreads();
    for(int j=0;j<3;j++)values[j*p+i]=v[j*p+i];
    if(op==2)for(int j=0;j<5;j++) {Pair x=values[j*p+i];raw[j*p+i]=double(x.h)+double(x.l);}
    for(int j=i;j<int(3*blocks*K*4);j+=blockDim.x)state[j]=sc[j];
    for(int j=i;j<int(3*blocks*K);j+=blockDim.x)ex[j]=se[j];
    if(t==0) {flags[w]=status[w];for(int j=0;j<8;j++)metrics[w*8+j]=terms[w][j];}
}
__device__ void native(const double* a,const double* cb,double* raw,unsigned* flags,
 unsigned n,unsigned m,unsigned blocks,unsigned op,unsigned count,unsigned shift,unsigned dense) {
    int i=threadIdx.x,p=blocks*32,nnz=int(cb[5*p+4]);
    const double* rows=a+2*p*p,*ri=rows+p+1,*rv=ri+nnz;
    const double* cols=rv+nnz,*ci=cols+p+1,*cv=ci+nnz;
    __shared__ double s[5*N];for(int j=0;j<5;j++)s[j*p+i]=raw[j*p+i];__syncthreads();
    if(op==1)for(unsigned step=0;step<count;step++) {
        double dot=0;
        if(dense)for(int j=0;j<p;j++)dot+=a[p*p+j*p+i]*s[p+j];
        else for(int j=int(cols[i]);j<int(cols[i+1]);j++)dot+=cv[j]*s[p+int(ci[j])];
        double old=s[i],u=i<int(n)?fmin(cb[2*p+i],fmax(cb[p+i],old+ldexp(dot-cb[i],-int(shift)))):0;
        __syncthreads();s[i]=u;s[2*p+i]=2*u-old;__syncthreads();dot=0;
        if(dense)for(int j=0;j<p;j++)dot+=a[j*p+i]*s[2*p+j];
        else for(int j=int(rows[i]);j<int(rows[i+1]);j++)dot+=rv[j]*s[2*p+int(ri[j])];
        double v=s[p+i]-ldexp(dot,-int(shift));
        s[p+i]=i<int(m)?v-fmin(-ldexp(cb[3*p+i],-int(shift)),fmax(-ldexp(cb[4*p+i],-int(shift)),v)):0;
        if(__any_sync(0xffffffff,!isfinite(s[i])||!isfinite(s[p+i])))if((i&31)==0)flags[i/32]=1;
        __syncthreads();if(i==0)flags[blocks]++;__syncthreads();
    }
    for(int j=0;j<5;j++)raw[j*p+i]=s[j*p+i];
    if(op==3||op==4) {double dot=0;bool tr=op==3;
        for(int j=0;j<p;j++)dot+=a[(tr?p*p:0)+j*p+i]*s[(tr?1:2)*p+j];raw[i]=dot;}
}
}
#define ARGS const unsigned* a,const int* ae,const unsigned* fr,const unsigned* masks,const Pair* orig,const Pair* err,const double* native,const double* cb,unsigned* s,int* se,Pair* v,double* raw,unsigned* flags,float* metrics,unsigned n,unsigned m,unsigned blocks,unsigned op,unsigned count,unsigned shift,double limit,unsigned extra
#define KERNEL(K) extern "C" __global__ __launch_bounds__(512,1) void accel_4_##K(ARGS) {accel::body<K,true>(a,ae,fr,masks,orig,err,native,cb,s,se,v,raw,flags,metrics,n,m,blocks,op,count,shift,limit,extra);} \
extern "C" __global__ __launch_bounds__(512,1) void accel_scalar_4_##K(ARGS) {accel::body<K,false>(a,ae,fr,masks,orig,err,native,cb,s,se,v,raw,flags,metrics,n,m,blocks,op,count,shift,limit,extra);}
KERNEL(2)
KERNEL(4)
extern "C" __global__ void accel_64_1(ARGS) {accel::native(native,cb,raw,flags,n,m,blocks,op,count,shift,extra);}
#define PREP(K) extern "C" __global__ void prepare_4_##K(const unsigned* a,unsigned* f,unsigned* m) {fast::prepare<4,K>(a,f,m);}
PREP(2)
PREP(4)
extern "C" __global__ void export_pairs(const Pair* v,double* raw,unsigned n) {
 unsigned i=blockIdx.x*blockDim.x+threadIdx.x;if(i<n)raw[i]=double(v[i].h)+double(v[i].l);
}
extern "C" __global__ void checkpoint(const unsigned* a,const int* e,const Pair* v,const double* r,
 unsigned* oa,int* oe,Pair* ov,double* oraw,unsigned ns,unsigned ne,unsigned nv) {
 unsigned i=blockIdx.x*blockDim.x+threadIdx.x;
 if(i<ns)oa[i]=a[i];if(i<ne)oe[i]=e[i];if(i<nv){ov[i]=v[i];oraw[i]=r[i];}
}

#include "grid.cuh"
