// Stream-ordered, multi-CTA version of the same centered recurrence.
// No inter-CTA spin barrier: x, y and guard are separate launches.
namespace grid_accel {
constexpr int WARPS=8;
template<int K> __device__ Pair unpack(const unsigned* words,const int* ex,unsigned lane) {
    Pair result={0,0};
    for(int k=0;k<K;k++) {
        unsigned code,base=unsigned(__cvta_generic_to_shared(words+4*k));
        // Explicit word alignment avoids the CUDA 13 packed-read lowering
        // observed as base+lane/2 rather than base+4*(lane/8) in this context.
        asm volatile("{ .reg .u32 word, offset, address; shr.u32 word, %2, 3; shl.b32 offset, word, 2; add.u32 address, %1, offset; ld.shared.u32 %0, [address]; }"
                     : "=r"(code) : "r"(base), "r"(lane));
        code=(code>>((lane&7)*4))&15;
        result=add(result,{fast::scale(fast::decode<4>(code),ex[k]),0});
    }return result;
}
__device__ bool stopped(const unsigned* flags,int blocks) {
    unsigned bad=0;for(int b=0;b<blocks;b++)bad|=flags[b];return bad!=0;
}
template<int K> __device__ Pair dot(bool tr,int w,int t,int blocks,
 const unsigned* a,const int* ae,const unsigned* fr,const unsigned* masks,
 const unsigned* sc,const int* se,Pair* scratch) {
    Pair value={0,0};
    for(int b=threadIdx.x/32;b<blocks;b+=WARPS) {
        int tile=tr?b*blocks+w:w*blocks+b;
        fast::product<4,K,8>(a+tile*K*128,ae+tile*K,sc+b*K*4,se+b*K,tr,
                            scratch,fr+tile*K*512,masks[tile]);
        value=add(value,scratch[t]);__syncwarp();
    }return value;
}
template<int K> __device__ void body(const unsigned* a,const int* ae,const unsigned* fr,const unsigned* masks,
 const double* exact,const double* cb,unsigned* state,int* ex,Pair* v,unsigned* flags,float* metrics,
 Pair* refs,float* norms,unsigned* pending,int n,int m,int blocks,int shift,double limit,int op) {
    int thread=threadIdx.x,t=thread&31,warp=thread/32,w=blockIdx.x,i=w*32+t,p=blocks*32;
    __shared__ unsigned sc[accel::B*K*4], own[K*4],status;
    __shared__ int se[accel::B*K], oe[K];
    __shared__ Pair scratch[WARPS*32],partial[WARPS*32];
    __shared__ double reference[2*WARPS*32];
    if(thread==0)status=0;__syncthreads();
    if(op==0) {
        double at=0,ax=0;
        for(int j=warp;j<p;j+=WARPS) {
            at+=exact[p*p+j*p+i]*(double(v[p+j].h)+double(v[p+j].l));
            ax+=exact[j*p+i]*(double(v[j].h)+double(v[j].l));
        }
        reference[thread]=at;reference[WARPS*32+thread]=ax;__syncthreads();
        if(warp)return;at=0;ax=0;for(int h=0;h<WARPS;h++){at+=reference[h*32+t];ax+=reference[WARPS*32+h*32+t];}
        refs[i]=accel::pair(at);refs[p+i]=accel::pair(ax);refs[2*p+i]=v[p+i];refs[3*p+i]=v[i];
        fast::encode<4,K,true,true>(Pair{0,0},own,oe,&status);
        for(int j=t;j<K*4;j+=32)state[(blocks+w)*K*4+j]=own[j];
        if(t<K)ex[(blocks+w)*K+t]=oe[t];
        if(t==0) {norms[w]=0;norms[3*blocks+w]=0;pending[w]=status;}
        return;
    }
    if(op==3) {
        if(warp)return;
        for(int j=0;j<3;j++) {
            fast::encode<4,K,true,true>(v[j*p+i],own,oe,&status);
            for(int h=t;h<K*4;h+=32)state[(j*blocks+w)*K*4+h]=own[h];
            if(t<K)ex[(j*blocks+w)*K+t]=oe[t];
            __syncwarp();
        }
        if(t==0&&flags[w]==0&&status)flags[w]=status;return;
    }
    if(stopped(flags,blocks))return;
    bool tr=op==1;int vec=tr?1:2;
    for(int j=thread;j<blocks*K*4;j+=blockDim.x)sc[j]=state[vec*blocks*K*4+j];
    for(int j=thread;j<blocks*K;j+=blockDim.x)se[j]=ex[vec*blocks*K+j];
    __syncthreads();
    partial[thread]=dot<K>(tr,w,t,blocks,a,ae,fr,masks,sc,se,scratch+warp*32);__syncthreads();
    if(warp)return;Pair product={0,0};for(int h=0;h<WARPS;h++)product=add(product,partial[h*32+t]);
    product=add(product,refs[(tr?0:p)+i]);
    unsigned ambiguous=0;
    Pair old=v[i],y=v[p+i],delta;
    double dt=ldexp(1.,-shift);
    if(tr) {
        Pair x=i<n?accel::clip(add(old,fast::power(add(product,neg(accel::pair(cb[i]))),-shift)),cb[p+i],cb[2*p+i],&ambiguous):Pair{0,0};
        Pair bar=add(fast::power(x,1),neg(old));v[i]=x;v[2*p+i]=bar;
        delta=add(bar,neg(refs[3*p+i]));
    } else {
        Pair ny=add(y,neg(fast::power(product,-shift)));
        ny=i<m?add(ny,neg(accel::clip(ny,-dt*cb[4*p+i],-dt*cb[3*p+i],&ambiguous))):Pair{0,0};
        v[p+i]=ny;delta=add(ny,neg(refs[2*p+i]));
    }
    fast::encode<4,K,true,true>(delta,own,oe,&status);
    Pair decoded=unpack<K>(own,oe,t);
    // y norms for the product just consumed must survive until the guard.
    int nv=tr?2:1;
    for(int j=t;j<K*4;j+=32)state[(nv*blocks+w)*K*4+j]=own[j];
    if(t<K)ex[(nv*blocks+w)*K+t]=oe[t];
    float vals[3]={accel::mag(delta),accel::mag(add(delta,neg(decoded))),
        0x1p-42f*(1+accel::mag(product)+accel::mag(old)+accel::mag(y))*(1+2*float(dt)*fmaxf(float(cb[5*p]),float(cb[5*p+1])))};
    for(int j=0;j<3;j++)vals[j]=__uint_as_float(__reduce_max_sync(0xffffffff,__float_as_uint(vals[j])));
    unsigned any=__any_sync(0xffffffff,ambiguous!=0);
    if(t==0) {
        int offset=tr?blocks:4*blocks;
        norms[offset+w]=vals[0];norms[offset+blocks+w]=vals[1];
        // x stores bar magnitude/error at [b,2b]; y stores next-y at [4b,5b].
        norms[(tr?6:7)*blocks+w]=vals[2];
        pending[(tr?0:blocks)+w]=status?status:(any?5:0);
    }
}
__device__ void guard(const double* cb,unsigned* flags,float* metrics,float* norms,const unsigned* pending,
 int blocks,int shift,double limit,bool native) {
    int w=threadIdx.x;if(w>=blocks)return;
    if(stopped(flags,blocks))return;
    float local[8]={0,0,0,0,0,0,0,0};unsigned status=0;
    if(!native) {
        int p=blocks*32;float na=fmaxf(float(cb[5*p]),float(cb[5*p+1])),d=ldexpf(1.f,-shift);
        float dy=0,db=0,ey=0,eb=0;
        for(int b=0;b<blocks;b++) {
            dy=fmaxf(dy,norms[b]);db=fmaxf(db,norms[blocks+b]);
            ey=fmaxf(ey,norms[3*blocks+b]);eb=fmaxf(eb,norms[2*blocks+b]);
        }
        local[0]=d*float(cb[5*p+3])*(dy*(1+2*d*na)+db);
        local[2]=norms[6*blocks+w]+norms[7*blocks+w];
        local[3]=float(cb[5*p+2])*d*(1+2*d*na);local[4]=float(cb[5*p+2])*4;
        local[5]=d*na*(ey*(1+2*d*na)+eb);local[7]=fmaxf(ey,eb);
        float total=0;for(int j=0;j<7;j++)total+=local[j];
        status=pending[w]?pending[w]:pending[blocks+w];
        if(!status&&(!isfinite(total)||total>float(limit)))status=3;
    }else status=pending[w]|pending[blocks+w];
    // All threads read the previous flags before any writes.
    __syncwarp();flags[w]=status;
    for(int j=0;j<8;j++)metrics[w*8+j]=fmaxf(metrics[w*8+j],local[j]);
    if(!native){norms[w]=norms[4*blocks+w];norms[3*blocks+w]=norms[5*blocks+w];}
    if(w==0)flags[blocks]++;
}
__device__ void native(const double* a,const double* cb,double* raw,const unsigned* flags,unsigned* pending,
 int n,int m,int blocks,int shift,int op) {
    int t=threadIdx.x&31,warp=threadIdx.x/32,i=blockIdx.x*32+t,p=blocks*32;if(stopped(flags,blocks))return;
    __shared__ double partial[WARPS*32];
    bool tr=op==1;double dot=0;
    for(int j=warp;j<p;j+=WARPS)dot+=a[(tr?p*p:0)+j*p+i]*raw[(tr?1:2)*p+j];
    partial[threadIdx.x]=dot;__syncthreads();if(warp)return;dot=0;for(int h=0;h<WARPS;h++)dot+=partial[h*32+t];
    double value;
    if(tr){double old=raw[i];value=i<n?fmin(cb[2*p+i],fmax(cb[p+i],old+ldexp(dot-cb[i],-shift))):0;raw[i]=value;raw[2*p+i]=2*value-old;}
    else {double v=raw[p+i]-ldexp(dot,-shift);value=i<m?v-fmin(-ldexp(cb[3*p+i],-shift),fmax(-ldexp(cb[4*p+i],-shift),v)):0;raw[p+i]=value;}
    if(threadIdx.x==0)pending[(tr?0:blocks)+blockIdx.x]=0;
    __syncwarp();if(__any_sync(0xffffffff,!isfinite(value)))if(threadIdx.x==0)pending[(tr?0:blocks)+blockIdx.x]=1;
}
}
#define GRID_ARGS const unsigned* a,const int* ae,const unsigned* fr,const unsigned* masks,const double* exact,const double* cb,unsigned* state,int* ex,Pair* v,double* raw,unsigned* flags,float* metrics,Pair* refs,float* norms,unsigned* pending,unsigned n,unsigned m,unsigned blocks,unsigned shift,double limit,unsigned op
#define GRID(K) extern "C" __global__ void grid_4_##K(GRID_ARGS) {grid_accel::body<K>(a,ae,fr,masks,exact,cb,state,ex,v,flags,metrics,refs,norms,pending,n,m,blocks,shift,limit,op);}
GRID(2)
GRID(4)
extern "C" __global__ void grid_native(GRID_ARGS) {grid_accel::native(exact,cb,raw,flags,pending,n,m,blocks,shift,op);}
extern "C" __global__ void grid_guard(GRID_ARGS) {grid_accel::guard(cb,flags,metrics,norms,pending,blocks,shift,limit,op==4);}
