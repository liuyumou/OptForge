// SPEC-0028. Immutable reference exports are compiled alongside each ablation.
#include "base.cuh"
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
    const int t=(threadIdx.x & 31), width=32/F;
    __syncwarp();
    if constexpr(Hardware)if(__any_sync(0xffffffff,!isfinite(value.h)||!isfinite(value.l))) {if(t==0 && *status==0)*status=1;return;}
    for(int k=0;k<K;k++) {
        float largest=__fadd_rn(fabsf(value.h),fabsf(value.l));
        if constexpr(Hardware)largest=__uint_as_float(__reduce_max_sync(0xffffffff,__float_as_uint(largest)));
        else for(int d=16;d;d>>=1)largest=fmaxf(largest,__shfl_xor_sync(0xffffffff,largest,d));
        if(!Hardware && __any_sync(0xffffffff,!isfinite(value.h)||!isfinite(value.l))) {if(t==0 && *status==0)*status=1;return;}
        const float maximum=F==4?6.f:(F==8?448.f:65504.f);
        int e=-48;
        if(largest>scale(maximum,-48)) {
            e=int((__float_as_uint(largest)>>23)&255)-127-(F==4?2:F==8?8:15);
            if(largest>scale(maximum,e))e++;
            e=max(-48,e);
        }
        if(e>48) {if(t==0 && *status==0)*status=2;return;}
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
    int t=(threadIdx.x & 31),g=t/4,q=t%4;
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
    int t=(threadIdx.x & 31); matrix+=blockIdx.x*K*32*F;fragments+=blockIdx.x*stride;
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
    int t=(threadIdx.x & 31),g=t/4,q=t%4;
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

} // namespace fast
