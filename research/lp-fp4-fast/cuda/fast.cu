// SPEC-0028. Immutable reference exports are compiled alongside each ablation.
#include "../../lp-fp4-gpu-pilot/cuda/pilot_v3.cu"
#include <cuda_fp4.h>
namespace fast {
__device__ float scale(float x, int e) {
    // The admitted exponent sums are in [-96,96]; the multiplier is normal.
    return __fmul_rn(x, __int_as_float((e+127)<<23));
}
__device__ Pair power(Pair x,int e) { return {scale(x.h,e),scale(x.l,e)}; }
template<int F> __device__ float decode(unsigned c) {
    if constexpr(F==4) {
        unsigned m=c&7, bits=m>=2?(m<<22)+0x3f000000u:(m?0x3f000000u:0u);
        return __uint_as_float(bits|((c&8)<<28));
    } else return ::decode<F>(c);
}
__device__ bool above(Pair a,float midpoint,unsigned lower) {
    return a.h>midpoint || (a.h==midpoint && (a.l>0 || (a.l==0 && (lower&1))));
}
template<int F> __device__ unsigned quant(Pair a) {
    if constexpr(F==4) {
        bool negative=a.h<0 || (a.h==0 && a.l<0); if(negative)a=neg(a);
        unsigned lo=above(a,1.75f,3)?4:0;
        lo+=above(a,lo?3.5f:.75f,lo+1)?2:0;
        float mid=lo==0?.25f:lo==2?1.25f:lo==4?2.5f:5.f;
        lo+=above(a,mid,lo)?1:0;
        return lo|((negative&&lo)?8:0);
    } else return ::quant<F>(a);
}
template<int F> __device__ unsigned hardware_quant(Pair a) {
    if constexpr(F==4) {
        float h=fabsf(a.h);
        bool midpoint=h==.25f || h==.75f || (h>=1.f && h<=5.f && ((__float_as_uint(h)&0x003fffff)==0x00200000));
        if(midpoint && a.l!=0) {
            unsigned bits=__float_as_uint(a.h);
            bits+=((a.h>0)==(a.l>0))?1u:0xffffffffu;
            a.h=__uint_as_float(bits);
        }
        unsigned c=__nv_cvt_float_to_fp4(a.h,__NV_E2M1,cudaRoundNearest);
        return (c&7)?c:0;
    } else return fast::quant<F>(a);
}
template<int F,int K> __device__ Pair unpack(const unsigned* c,const int* e,int i) {
    Pair v={0,0};for(int k=0;k<K;k++) {
        unsigned code;
        if constexpr(F==16) {
            // Explicit half-width shared load: the retained CUDA 13 image
            // incorrectly used a 32-bit load at base+2*lane in this path.
            unsigned address=unsigned(__cvta_generic_to_shared(c+k*F))+unsigned(i)*2;
            asm volatile("ld.shared.u16 %0, [%1];" : "=r"(code) : "r"(address));
        } else code=get(c+k*F,i,F);
        v=add(v,{scale(fast::decode<F>(code),e[k]),0});
    }return v;
}
template<int F,int K,bool Quick=false,bool Hardware=false> __device__ void encode(Pair value,unsigned* c,int* ex,unsigned* status) {
    const int t=threadIdx.x, width=32/F;
    __syncwarp();
    if constexpr(Hardware)if(__any_sync(0xffffffff,!isfinite(value.h)||!isfinite(value.l))) {if(t==0)*status=1;return;}
    for(int k=0;k<K;k++) {
        float largest=__fadd_rn(fabsf(value.h),fabsf(value.l));
        if constexpr(Hardware)largest=__uint_as_float(__reduce_max_sync(0xffffffff,__float_as_uint(largest)));
        else for(int d=16;d;d>>=1)largest=fmaxf(largest,__shfl_xor_sync(0xffffffff,largest,d));
        if(!Hardware && __any_sync(0xffffffff,!isfinite(value.h)||!isfinite(value.l))) {if(t==0)*status=1;return;}
        const float maximum=F==4?6.f:(F==8?448.f:65504.f);
        int e=-48;
        if(largest>scale(maximum,-48)) {
            e=int((__float_as_uint(largest)>>23)&255)-127-(F==4?2:F==8?8:15);
            if(largest>scale(maximum,e))e++;
            e=max(-48,e);
        }
        if(e>48) {if(t==0)*status=2;return;}
        unsigned code=Hardware?hardware_quant<F>(fast::power(value,-e)):fast::quant<F>(fast::power(value,-e));
        unsigned word=code;
        word|=__shfl_down_sync(0xffffffff,word,1)<<F;
        if constexpr(F<=8)word|=__shfl_down_sync(0xffffffff,word,2)<<(2*F);
        if constexpr(F==4)word|=__shfl_down_sync(0xffffffff,word,4)<<16;
        if(t%width==0)c[k*F+t/width]=word;
        if(t==0)ex[k]=e;
        float component=scale(fast::decode<F>(code),e);
        if constexpr(Quick) {
            // Nonzero nearest components satisfy Sterbenz with the normalized
            // high part; zero leaves it unchanged. The subtraction is exact.
            float h=__fsub_rn(value.h,component), v=__fadd_rn(h,value.l);
            value={v,__fadd_rn(__fsub_rn(h,v),value.l)};
        } else value=add(value,{-component,0});
        __syncwarp();
    }
}
template<int F,int K> __device__ void fragment(const unsigned* matrix,int p,int half,int slice,bool trans,unsigned* a) {
    int t=threadIdx.x,g=t/4,q=t%4;
    constexpr int pack=F==16?2:4,bits=F==16?16:8;
    for(int reg=0;reg<4;reg++) {
        a[reg]=0;
        for(int j=0;j<pack;j++) {
            int r=16*half+g+(reg%2)*8;
            int col=q*pack+j+(reg/2)*(4*pack)+slice*16;
            unsigned code=get(matrix+p*32*F,trans?col*32+r:r*32+col,F);
            if constexpr(F==4)code<<=2;
            a[reg]|=code<<(bits*j);
        }
    }
}
template<int F,int K> __device__ void prepare(const unsigned* matrix,unsigned* fragments,unsigned* masks) {
    constexpr int slices=F==16?2:1, stride=K*2*2*slices*32*4;
    int t=threadIdx.x; matrix+=blockIdx.x*K*32*F;fragments+=blockIdx.x*stride;
    unsigned mask=0;
    for(int p=0;p<K;p++) {
        unsigned nonzero=0;
        for(int i=t;i<32*F;i+=32)nonzero|=matrix[p*32*F+i];
        if(__any_sync(0xffffffff,nonzero!=0))mask|=1u<<p;
        for(int tr=0;tr<2;tr++)for(int h=0;h<2;h++)for(int sl=0;sl<slices;sl++) {
            unsigned a[4];fragment<F,K>(matrix,p,h,sl,tr,a);
            int offset=((((tr*K+p)*2+h)*slices+sl)*32+t)*4;
            for(int reg=0;reg<4;reg++)fragments[offset+reg]=a[reg];
        }
    }
    if(t==0)masks[blockIdx.x]=mask;
}
// M=0 encoding only, 1 exact-zero pruning, 2 prepacked A, 3 component columns.
template<int F,int K,int M> __device__ void product(const unsigned* matrix,const int* me,const unsigned* vector,const int* ve,bool trans,Pair* out,const unsigned* fragments,unsigned mask) {
    int t=threadIdx.x,g=t/4,q=t%4;
    constexpr int slices=F==16?2:1;
    for(int half=0;half<2;half++) {
        Pair acc0={0,0},acc1={0,0};
        for(int p=0;p<K;p++) {
            if constexpr(M>=1)if(!(mask&(1u<<p)))continue;
            for(int s0=0;s0<(M>=3?1:K);s0++) {
                float d[4]={0,0,0,0};
                for(int slice=0;slice<slices;slice++) {
                    unsigned a[4],b[2]={0,0};
                    constexpr int pack=F==16?2:4, bits=F==16?16:8;
                    if constexpr(M>=2 && M!=4) {
                        int offset=((((int(trans)*K+p)*2+half)*slices+slice)*32+t)*4;
                        if constexpr(M>=8) {
                            uint4 v=*reinterpret_cast<const uint4*>(fragments+offset);
                            a[0]=v.x;a[1]=v.y;a[2]=v.z;a[3]=v.w;
                        } else for(int reg=0;reg<4;reg++)a[reg]=fragments[offset+reg];
                    } else fragment<F,K>(matrix,p,half,slice,trans,a);
                    for(int reg=0;reg<2;reg++)for(int j=0;j<pack;j++) {
                        int r=q*pack+j+reg*(4*pack)+slice*16;
                        unsigned code=M>=3?(g<K?get(vector+g*F,r,F):0):(g==0?get(vector+s0*F,r,F):0);
                        if constexpr(F==4)code<<=2;
                        b[reg]|=code<<(bits*j);
                    }
                    mma<F>(d,a,b);
                }
                if constexpr(M>=3) {
                    for(int s=0;s<K;s++) {
                        float x=__shfl_sync(0xffffffff,(s&1)?d[1]:d[0],g*4+s/2);
                        float y=__shfl_sync(0xffffffff,(s&1)?d[3]:d[2],g*4+s/2);
                        int e=me[p]+ve[s];
                        acc0=add(acc0,{scale(x,e),0});acc1=add(acc1,{scale(y,e),0});
                    }
                } else {
                    int e=me[p]+ve[s0];
                    acc0=add(acc0,{scale(d[0],e),0});acc1=add(acc1,{scale(d[2],e),0});
                }
            }
        }
        if(q==0) {out[16*half+g]=acc0;out[16*half+g+8]=acc1;}
    }
    __syncwarp();
}
template<int F,int K,int M,bool Trans> __device__ void register_product(const unsigned* matrix,const int* me,const unsigned* vector,const int* ve,Pair* out,const unsigned* fragments,unsigned mask) {
    int t=threadIdx.x,g=t/4,q=t%4;
    constexpr int slices=F==16?2:1;
    
#pragma unroll
for(int half=0;half<2;half++) {
        Pair acc0={0,0},acc1={0,0};
        
#pragma unroll
for(int p=0;p<K;p++) {
            if constexpr(M>=1)if(!(mask&(1u<<p)))continue;
            
#pragma unroll
for(int s0=0;s0<(M>=3?1:K);s0++) {
                float d[4]={0,0,0,0};
                
#pragma unroll
for(int slice=0;slice<slices;slice++) {
                    unsigned a[4],b[2]={0,0};
                    constexpr int pack=F==16?2:4, bits=F==16?16:8;
                    if constexpr(M>=2 && M!=4) {
                        int offset=(((int(Trans)*K+p)*2+half)*slices+slice)*4;
                        
#pragma unroll
for(int reg=0;reg<4;reg++)a[reg]=fragments[offset+reg];
                    } else fragment<F,K>(matrix,p,half,slice,Trans,a);
                    
#pragma unroll
for(int reg=0;reg<2;reg++)for(int j=0;j<pack;j++) {
                        int r=q*pack+j+reg*(4*pack)+slice*16;
                        unsigned code=M>=3?(g<K?get(vector+g*F,r,F):0):(g==0?get(vector+s0*F,r,F):0);
                        if constexpr(F==4)code<<=2;
                        b[reg]|=code<<(bits*j);
                    }
                    mma<F>(d,a,b);
                }
                if constexpr(M>=3) {
                    
#pragma unroll
for(int s=0;s<K;s++) {
                        float x=__shfl_sync(0xffffffff,(s&1)?d[1]:d[0],g*4+s/2);
                        float y=__shfl_sync(0xffffffff,(s&1)?d[3]:d[2],g*4+s/2);
                        int e=me[p]+ve[s];
                        acc0=add(acc0,{scale(x,e),0});acc1=add(acc1,{scale(y,e),0});
                    }
                } else {
                    int e=me[p]+ve[s0];
                    acc0=add(acc0,{scale(d[0],e),0});acc1=add(acc1,{scale(d[2],e),0});
                }
            }
        }
        if(q==0) {out[16*half+g]=acc0;out[16*half+g+8]=acc1;}
    }
    __syncwarp();
}
template<int F,int K,int M> __device__ void run(const unsigned* matrix,const int* me,const double* original,const double* cb,unsigned* state,int* ex,double* raw,Pair* tmp,unsigned* flags,unsigned n,unsigned op,unsigned count,const unsigned* fragments,const unsigned* masks) {
    int t=threadIdx.x,b=blockIdx.x;
    fragments+=b*K*2*2*(F==16?2:1)*32*4;unsigned mask=masks[b];
    __shared__ unsigned packed_cache[M==4?K*32*F:1];
    unsigned registers[M==5?K*2*2*(F==16?2:1)*4:1];
    if constexpr(M==4) {
        for(int i=t;i<K*32*F;i+=32)packed_cache[i]=matrix[b*K*32*F+i];
        __syncwarp();
    }
    if constexpr(M==5) {
#pragma unroll
        for(int i=0;i<K*2*2*(F==16?2:1);i++) {
#pragma unroll
            for(int reg=0;reg<4;reg++)registers[i*4+reg]=fragments[(i*32+t)*4+reg];
        }
    }
    __shared__ unsigned sc[3*K*F];__shared__ int se[3*K];
    __shared__ Pair dot[32];__shared__ unsigned status;
    state+=b*3*K*F;ex+=b*3*K;matrix+=b*K*32*F;me+=b*K;
    raw+=b*96;tmp+=b*32;cb+=b*64;flags+=b*2;
    if constexpr(M==4)matrix=packed_cache;
    for(int i=t;i<3*K*F;i+=32)sc[i]=state[i];
    for(int i=t;i<3*K;i+=32)se[i]=ex[i];
    if(t==0)status=flags[0];__syncwarp();
    if(op==7) {if(t==0)flags[0]=4;return;}
    if(status)return;
    if(op==0)for(int v=0;v<3;v++) {
        double x=t<int(n)?raw[v*32+t]:0;float h=float(x);
        fast::encode<F,K,(M>=4),(M>=8)>({h,float(x-double(h))},sc+v*K*F,se+v*K,&status);
    }
    if(op==1 || op==3) {
        int v=op==1?1:2;if constexpr(M==5) {
            if(op==1)fast::register_product<F,K,M,true>(matrix,me,sc+v*K*F,se+v*K,dot,registers,mask);
            else fast::register_product<F,K,M,false>(matrix,me,sc+v*K*F,se+v*K,dot,registers,mask);
        }
        else fast::product<F,K,M>(matrix,me,sc+v*K*F,se+v*K,op==1,dot,fragments,mask);tmp[t]=dot[t];
    }
    if(op==2 || op==4)dot[t]=tmp[t];
    __syncwarp();
    unsigned long long cycles[4]={0,0,0,0}, stamp=0;
    for(unsigned step=0;step<(op==5?count:1);step++) {
        if constexpr(M==7)stamp=clock64();
        if(op==5) {if constexpr(M==5)fast::register_product<F,K,M,true>(matrix,me,sc+K*F,se+K,dot,registers,mask); else fast::product<F,K,M>(matrix,me,sc+K*F,se+K,true,dot,fragments,mask);}
        if constexpr(M==7){unsigned long long now=clock64();cycles[0]+=now-stamp;stamp=now;}
        if(op==2 || op==5) {
            Pair old=fast::unpack<F,K>(sc,se,t);
            Pair x=add(old,fast::power(add(dot[t],{-float(cb[t]),0}),-4));
            if constexpr(M>=4) {
                if(x.h < -1 || (x.h == -1 && x.l < 0))x={-1,0};
                if(x.h > 1 || (x.h == 1 && x.l > 0))x={1,0};
            } else x=project(x);
            if(t>=int(n))x={0,0};
            Pair bar=add(fast::power(x,1),neg(old));
            fast::encode<F,K,(M>=4),(M>=8)>(x,sc,se,&status);
            fast::encode<F,K,(M>=4),(M>=8)>(bar,sc+2*K*F,se+2*K,&status);
        }
        if constexpr(M==7){unsigned long long now=clock64();cycles[1]+=now-stamp;stamp=now;}
        if(op==5) {if constexpr(M==5)fast::register_product<F,K,M,false>(matrix,me,sc+2*K*F,se+2*K,dot,registers,mask); else fast::product<F,K,M>(matrix,me,sc+2*K*F,se+2*K,false,dot,fragments,mask);}
        if constexpr(M==7){unsigned long long now=clock64();cycles[2]+=now-stamp;stamp=now;}
        if(op==4 || op==5) {
            Pair y=add(fast::unpack<F,K>(sc+K*F,se+K,t),fast::power(add({float(cb[32+t]),0},neg(dot[t])),-4));
            if(t>=int(n))y={0,0};
            fast::encode<F,K,(M>=4),(M>=8)>(y,sc+K*F,se+K,&status);
            if(t==0)flags[1]++;
        }
        if constexpr(M==7)cycles[3]+=clock64()-stamp;
        __syncwarp();if(status)break;
    }
    if constexpr(M==7)if(op==5 && t==0)for(int i=0;i<4;i++)reinterpret_cast<unsigned long long*>(tmp)[i]=cycles[i];
    if(op==6)for(int v=0;v<3;v++){Pair x=fast::unpack<F,K>(sc+v*K*F,se+v*K,t);raw[v*32+t]=double(x.h)+double(x.l);}
    for(int i=t;i<3*K*F;i+=32)state[i]=sc[i];
    for(int i=t;i<3*K;i+=32)ex[i]=se[i];
    if(t==0)flags[0]=status;
}

} // namespace fast
#define FAST(F,K,M) extern "C" __global__ void fast_##F##_##K##_##M(const unsigned* fragments,const unsigned* masks,PARAM) {fast::run<F,K,M>(a,ae,orig,cb,s,se,raw,tmp,flags,n,op,count,fragments,masks);}
#define PREP(F,K) extern "C" __global__ void prepare_##F##_##K(const unsigned* a,unsigned* fragments,unsigned* masks) {fast::prepare<F,K>(a,fragments,masks);}
PREP(4,2)
FAST(4,2,0)
FAST(4,2,1)
FAST(4,2,2)
FAST(4,2,3)
PREP(4,4)
FAST(4,4,0)
FAST(4,4,1)
FAST(4,4,2)
FAST(4,4,3)
PREP(4,8)
FAST(4,8,0)
FAST(4,8,1)
FAST(4,8,2)
FAST(4,8,3)
PREP(8,4)
FAST(8,4,0)
FAST(8,4,1)
FAST(8,4,2)
FAST(8,4,3)
PREP(16,2)
FAST(16,2,0)
FAST(16,2,1)
FAST(16,2,2)
FAST(16,2,3)
FAST(4,2,4)
FAST(4,2,5)
FAST(4,2,6)
FAST(4,4,4)
FAST(4,4,5)
FAST(4,4,6)
FAST(4,8,4)
FAST(4,8,5)
FAST(4,8,6)
FAST(8,4,4)
FAST(8,4,5)
FAST(8,4,6)
FAST(16,2,4)
FAST(16,2,5)
FAST(16,2,6)

__device__ void native_cached(const double* a,const double* cb,double* raw,double* tmp,unsigned* flags,unsigned n,unsigned op,unsigned count) {
    int t=threadIdx.x,b=blockIdx.x;a+=b*1024;cb+=b*64;raw+=b*96;tmp+=b*32;flags+=b*2;
    double row[32],column[32];
#pragma unroll
    for(int j=0;j<32;j++){row[j]=a[t*32+j];column[j]=a[j*32+t];}
    __shared__ double state[96],dot[32];
    for(int v=0;v<3;v++)state[v*32+t]=raw[v*32+t];__syncwarp();
    if(op==7){if(t==0)flags[0]=4;return;}if(flags[0])return;
    if(op==1||op==3){double sum=0;
#pragma unroll
for(int j=0;j<32;j++)sum+=(op==1?column[j]:row[j])*state[(op==1?32:64)+j];tmp[t]=sum;}
    if(op==2||op==4)dot[t]=tmp[t];__syncwarp();
    for(unsigned step=0;step<(op==5?count:1);step++) {
        if(op==5){double sum=0;
#pragma unroll
for(int j=0;j<32;j++)sum+=column[j]*state[32+j];dot[t]=sum;__syncwarp();}
        if(op==2||op==5){double old=state[t];double x=t<int(n)?fmin(1.,fmax(-1.,old-(cb[t]-dot[t])/16.)):0;state[t]=x;state[64+t]=2*x-old;__syncwarp();}
        if(op==5){double sum=0;
#pragma unroll
for(int j=0;j<32;j++)sum+=row[j]*state[64+j];dot[t]=sum;__syncwarp();}
        if(op==4||op==5){state[32+t]=t<int(n)?state[32+t]+(cb[32+t]-dot[t])/16.:0;if(t==0)flags[1]++;__syncwarp();}
    }
    for(int v=0;v<3;v++)raw[v*32+t]=state[v*32+t];
    if(__any_sync(0xffffffff,!isfinite(state[t])||!isfinite(state[32+t])||!isfinite(state[64+t])))if(t==0)flags[0]=1;
}

extern "C" __global__ void native_cached_64_1(PARAM) {native_cached(orig,cb,raw,reinterpret_cast<double*>(tmp),flags,n,op,count);}
FAST(4,2,7)
FAST(4,4,7)
FAST(4,8,7)
FAST(4,2,8)
FAST(4,4,8)
FAST(4,8,8)
FAST(8,4,8)
FAST(16,2,8)
// Fresh prepared windows restore their complete checkpoint inside the device.
extern "C" __global__ void reset_checkpoint(
    const unsigned* cs,const int* ce,const double* cr,const unsigned* cf,
    unsigned* s,int* e,double* r,unsigned* f,
    unsigned ns,unsigned ne,unsigned nr,unsigned nf) {
    unsigned i=blockIdx.x*blockDim.x+threadIdx.x;
    if(i<ns)s[i]=cs[i];
    if(i<ne)e[i]=ce[i];
    if(i<nr)r[i]=cr[i];
    if(i<nf)f[i]=cf[i];
}
