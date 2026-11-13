// SPEC-0038. Explicit compilation only; bounded FP4 normal components and FP64 state.
#include "../../lp-fp4-accel/cuda/helpers.cuh"
namespace mixed {
constexpr int MAX=2048, B=MAX/32, W=8;
__device__ double upadd(double a,double b){return __dadd_ru(a,b);}
__device__ double upmul(double a,double b){return __dmul_ru(a,b);}
__device__ double warpmax(double a){for(int d=16;d;d>>=1)a=fmax(a,__shfl_xor_sync(0xffffffff,a,d));return a;}
__device__ bool stopped(const unsigned* f,int b){unsigned v=0;for(int j=0;j<b;j++)v|=f[j];return v!=0;}
__device__ unsigned quant32(float x){
    bool negative=x<0;x=fabsf(x);unsigned c=0;
    const float mid[6]={.5f,1.25f,1.75f,2.5f,3.5f,5.f};
    for(int j=0;j<6;j++){unsigned next=j+2;if(x>mid[j]||(x==mid[j]&&next!=2&&!(next&1)))c=next;}
    return c|((negative&&c)?8:0);
}
__device__ double maximum_up(double x){
    // Nonnegative upward conversion makes a conservative summary; integer warp
    // reduction preserves the total ordering of nonnegative IEEE FP32 values.
    unsigned word=__float_as_uint(__double2float_ru(x));
    return double(__uint_as_float(__reduce_max_sync(0xffffffff,word)));
}
template<int K> __device__ unsigned encode(double value,double anchor,unsigned* c,int* ex,double* norms){
    int t=threadIdx.x&31;unsigned status=0;
    double delta=__dsub_rn(value,anchor),absolute=0,decoded=0;
    bool bad=!isfinite(delta)||fabs(delta)>ldexp(6.,48);
    if(__any_sync(0xffffffff,bad))status=2;
    float proposal=bad?0.f:__double2float_rn(delta);
    for(int h=0;h<K;h++){
        float largest=__uint_as_float(__reduce_max_sync(0xffffffff,__float_as_uint(fabsf(proposal))));
        int e=max(-48,int(__float_as_uint(largest)>>23)-129);
        if(largest>fast::scale(6.f,e))++e;
        unsigned code=quant32(fast::scale(proposal,-e));
        unsigned word=code;
        for(int d=1;d<8;d<<=1)word|=__shfl_down_sync(0xffffffff,word,d)<<(4*d);
        if(!(t&7))c[h*4+t/8]=word;
        if(!t)ex[h]=e;
        float part=fast::scale(fast::decode<4>(code),e);
        proposal=__fsub_rn(proposal,part);
        decoded=__dadd_rn(decoded,double(part));absolute=upadd(absolute,fabs(double(part)));
    }
    // Enclose the error of the actual decoded components against the original
    // FP64 difference. The FP32 proposal need not be a nearest FP64 quantization.
    double round=upadd(upmul(0x1p-48,upadd(upadd(fabs(value),fabs(anchor)),absolute)),0x1p-1068);
    double err=maximum_up(upadd(fabs(__dsub_rn(delta,decoded)),round));
    double mag=maximum_up(upadd(fabs(delta),upadd(upmul(0x1p-52,upadd(fabs(value),fabs(anchor))),0x1p-1073)));
    absolute=maximum_up(absolute);double anc=maximum_up(fabs(anchor));
    if(!t){norms[0]=mag;norms[1]=err;norms[2]=absolute;norms[3]=anc;}
    return status;
}
// An unscaled component dot is a sum of 32 quarter-integers in [-1152,1152].
// Inputs exclude FP4 subnormals; every intermediate sum is exactly FP32 representable.
template<int K> __device__ void product(const unsigned* matrix,const int* me,const unsigned* fr,unsigned mask,
    const unsigned* vec,const int* ve,bool tr,float* out){
    const int t=threadIdx.x&31,g=t/4,q=t%4;
    for(int half=0;half<2;half++){
        float sum[2]={0,0};
        for(int h=0;h<K;h++)if(mask&(1u<<h)){
            unsigned a[4],b[2];
            const uint4 x=*reinterpret_cast<const uint4*>(fr+((int(tr)*K+h)*2+half)*128+t*4);
            a[0]=x.x;a[1]=x.y;a[2]=x.z;a[3]=x.w;
            for(int j=0;j<2;j++){
                unsigned packed=0;
                if(g<K)for(int z=0;z<4;z++)packed|=((get(vec+g*4,q*4+z+j*16,4)<<2)<<(z*8));
                b[j]=packed;
            }
            float d[4]={0,0,0,0};mma<4>(d,a,b);
            for(int s=0;s<K;s++){
                float x0=__shfl_sync(0xffffffff,d[s%2],g*4+s/2);
                float x1=__shfl_sync(0xffffffff,d[2+s%2],g*4+s/2);
                sum[0]=__fadd_rn(sum[0],fast::scale(x0,me[h]+ve[s]));
                sum[1]=__fadd_rn(sum[1],fast::scale(x1,me[h]+ve[s]));
            }
        }
        if(q==0){out[half*16+g]=sum[0];out[half*16+g+8]=sum[1];}
        __syncwarp();
    }
}
__device__ double enclosure(int i,int p,int k,const double* a,const double* vn,double ref,double inc){
    double an=a[i],er=a[p+i],cn=a[2*p+i];
    double e=upmul(upmul((2*p+32)*0x1p-52,an),vn[3]);
    e=upadd(e,upmul(er,vn[0]));
    e=upadd(e,upmul(cn,vn[1]));
    e=upadd(e,upmul(upmul((4*(p/32)*k*k+32)*0x1p-23,cn),vn[2]));
    e=upadd(e,upmul(0x1p-52,upadd(fabs(ref),fabs(inc))));
    return upadd(e,0x1p-1000);
}
#define ARGS const unsigned* a,const int* ae,const unsigned* fr,const unsigned* masks,const double* exact,const double* cb,const double* an,unsigned* codes,int* ex,double* raw,unsigned* flags,double* refs,double* norms,unsigned* pending,double* errors,double* products,unsigned n,unsigned m,unsigned blocks,unsigned shift,double limit,unsigned op
#define PASS a,ae,fr,masks,exact,cb,an,codes,ex,raw,flags,refs,norms,pending,errors,products,n,m,blocks,shift,limit,op
// Native and tensor lanes use the same grid, projection arithmetic and FP64 state.
template<int K> __device__ void body(ARGS){
    int t=threadIdx.x&31,warp=threadIdx.x/32,w=blockIdx.x,i=w*32+t,p=blocks*32;
    __shared__ double partial[W*32],vn[4];
    __shared__ float scratch[W*32],partial32[W*32];
    __shared__ unsigned sc[B*K*4+1];__shared__ int se[B*K+1];__shared__ bool stop;
    if(!threadIdx.x)stop=(op==0||op==6)?false:stopped(flags,blocks);__syncthreads();if(stop)return;
    if(op==0 || op==6){
        // Reference products use the same multiply/add tree as the native control.
        for(int tr=0;tr<2;tr++){
            double dot=0;
            if(op==0)for(int j=warp;j<p;j+=W)dot+=exact[(tr?p*p:0)+j*p+i]*raw[(tr?1:2)*p+j];
            partial[threadIdx.x]=dot;__syncthreads();
            if(warp==0){dot=0;for(int h=0;h<W;h++)dot+=partial[h*32+t];refs[tr*p+i]=dot;
                refs[(tr?3:2)*p+i]=op==0?raw[(tr?1:2)*p+i]:0;}
            __syncthreads();
        }
        if(warp==0 && K){
            unsigned st=encode<K>(raw[p+i],refs[3*p+i],codes+w*K*4,ex+w*K,norms+w*4);
            st|=encode<K>(raw[2*p+i],refs[2*p+i],codes+(blocks+w)*K*4,ex+(blocks+w)*K,norms+(blocks+w)*4);
            if(!t)flags[w]=st;
        }
        return;
    }
    bool debug=op>=4,tr=(op&1);int direction=tr?0:1;
    double dot=0;float dot32=0;
    if constexpr(K==0){
        for(int j=warp;j<p;j+=W)dot+=exact[(tr?p*p:0)+j*p+i]*raw[(tr?1:2)*p+j];
    }else{
        for(int j=threadIdx.x;j<int(blocks)*K*4;j+=blockDim.x)sc[j]=codes[direction*blocks*K*4+j];
        for(int j=threadIdx.x;j<int(blocks)*K;j+=blockDim.x)se[j]=ex[direction*blocks*K+j];
        if(warp==0 && op<12)for(int q=0;q<4;q++){
            float v=0;for(int j=t;j<blocks;j+=32)v=fmaxf(v,float(norms[(direction*blocks+j)*4+q]));
            v=__uint_as_float(__reduce_max_sync(0xffffffff,__float_as_uint(v)));
            if(!t)vn[q]=double(v);
        }
        __syncthreads();
        for(int j=warp;j<blocks;j+=W){
            int tile=tr?j*blocks+w:w*blocks+j;
            product<K>(a+tile*K*128,ae+tile*K,fr+tile*K*512,masks[tile],sc+j*K*4,se+j*K,tr,scratch+warp*32);
            dot32=__fadd_rn(dot32,scratch[warp*32+t]);__syncwarp();
        }
    }
    if constexpr(K==0)partial[threadIdx.x]=dot;else partial32[threadIdx.x]=dot32;
    __syncthreads();if(warp)return;
    if constexpr(K==0){dot=0;for(int h=0;h<W;h++)dot=__dadd_rn(dot,partial[h*32+t]);}
    else{dot32=0;for(int h=0;h<W;h++)dot32=__fadd_rn(dot32,partial32[h*32+t]);dot=double(dot32);}
    double bound=0;
    if constexpr(K!=0){
        double ref=refs[(tr?1:0)*p+i];if(op<12)bound=enclosure(i,p,K,an+(tr?3*p:0),vn,ref,dot);dot=__dadd_rn(ref,dot);
    }
    if(debug){products[i]=dot;products[p+i]=bound;return;}
    double tau=__longlong_as_double(uint64_t(1023-shift)<<52);
    double value;
    if(tr){double old=raw[i];value=i<n?fmin(cb[2*p+i],fmax(cb[p+i],old+__dmul_rn(dot-cb[i],tau))):0;raw[i]=value;raw[2*p+i]=2*value-old;}
    else{double v=raw[p+i]-__dmul_rn(dot,tau);value=i<m?v-fmin(-__dmul_rn(cb[3*p+i],tau),fmax(-__dmul_rn(cb[4*p+i],tau),v)):0;raw[p+i]=value;}
    unsigned status=__any_sync(0xffffffff,!isfinite(value)||!isfinite(dot)||!isfinite(bound)||(tr&&!isfinite(raw[2*p+i])))?1:0;
    double local=warpmax(upmul(tau,bound));
    if(!status&&local>limit)status=3;
    if constexpr(K!=0){
        int target=tr?1:0;
        unsigned conversion=encode<K>(tr?raw[2*p+i]:value,refs[(tr?2:3)*p+i],codes+(target*blocks+w)*K*4,ex+(target*blocks+w)*K,norms+(target*blocks+w)*4);
        if(conversion)status=2;
    }
    if(!t){pending[(tr?0:blocks)+w]=status;errors[(tr?0:blocks)+w]=fmax(errors[(tr?0:blocks)+w],local);}
}
}
extern "C" __global__ void mixed_native(ARGS){mixed::body<0>(PASS);}
extern "C" __global__ void mixed_2(ARGS){mixed::body<2>(PASS);}
extern "C" __global__ void mixed_4(ARGS){mixed::body<4>(PASS);}
extern "C" __global__ void mixed_guard(unsigned* flags,const unsigned* pending,unsigned b){
    __shared__ bool stop;if(!threadIdx.x)stop=mixed::stopped(flags,b);__syncthreads();if(stop)return;
    for(int j=threadIdx.x;j<b;j+=blockDim.x){unsigned x=pending[j],y=pending[b+j];flags[j]=(x==1||y==1)?1:(x==2||y==2)?2:(x||y)?3:0;};
    if(!threadIdx.x)flags[b]++;
}
extern "C" __global__ void mixed_copy(const double* source,double* target,unsigned n){unsigned i=blockIdx.x*blockDim.x+threadIdx.x;if(i<n)target[i]=source[i];}
extern "C" __global__ void prepare_4_2(const unsigned* a,unsigned* fr,unsigned* masks){fast::prepare<4,2>(a,fr,masks);}
extern "C" __global__ void prepare_4_4(const unsigned* a,unsigned* fr,unsigned* masks){fast::prepare<4,4>(a,fr,masks);}
