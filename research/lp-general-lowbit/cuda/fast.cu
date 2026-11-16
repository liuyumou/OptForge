// SPEC-0045: unenclosed proposals, original-operator control and certificates.
#include "tensor.cu"

namespace fast {
__device__ void encode(double value, unsigned index, unsigned n, unsigned k,
    unsigned* codes, int* exponents, unsigned* flags) {
    unsigned lane=threadIdx.x%32, block=index/32;
    bool bad=index<n&&(!isfinite(value)||fabs(value)>0x1p40);
    bool invalid=__any_sync(0xffffffff,bad);
    if(!lane&&invalid)atomicOr(flags,1u);
    float v=invalid?0.f:__double2float_rn(value);
    for(unsigned h=0;h<k;h++){
        float largest=__uint_as_float(__reduce_max_sync(0xffffffff,__float_as_uint(fabsf(v))));
        int e=max(-48,int(__float_as_uint(largest)>>23)-129);
        if(largest>tensor::scale(6.f,e))++e;
        unsigned c=tensor::quant(tensor::scale(v,-e)), word=c;
        for(int d=1;d<8;d<<=1)word|=__shfl_down_sync(0xffffffff,word,d)<<(4*d);
        if(!(lane&7))codes[(block*k+h)*4+lane/8]=word;
        if(!lane)exponents[block*k+h]=e;
        v=__fsub_rn(v,tensor::scale(general::fp4(c),e));
    }
}

template<unsigned K>
__device__ __forceinline__ void tile_product(unsigned tile,const unsigned* columns,const unsigned* fragments,const int* me,
    const unsigned* vc,const int* ve,unsigned compact,float& sum0,float& sum1){
    unsigned lane=threadIdx.x%32;
    unsigned g=lane/4,q=lane%4,col=columns[tile],b[2]={0,0};
    if(g<K){
        #pragma unroll
        for(unsigned j=0;j<2;j++){
            #pragma unroll
            for(unsigned z=0;z<4;z++){
                unsigned pos=q*4+z+j*16,code=(vc[(col*K+g)*4+pos/8]>>((pos%8)*4))&15;
                b[j]|=code<<(2+z*8);
            }
        }
    }
    sum0=0;sum1=0;
    #pragma unroll
    for(unsigned h=0;h<K;h++){
        unsigned a[4];
        if(compact){const uint2 f=*reinterpret_cast<const uint2*>(fragments+(tile*K+h)*64+lane*2);
            a[0]=tensor::expand(f.x);a[1]=tensor::expand(f.x>>16);a[2]=tensor::expand(f.y);a[3]=tensor::expand(f.y>>16);}
        else {const uint4 f=*reinterpret_cast<const uint4*>(fragments+(tile*K+h)*128+lane*4);a[0]=f.x;a[1]=f.y;a[2]=f.z;a[3]=f.w;}
        float d[4];tensor::mma(d,a,b);
        // Each lane reconstructs only its own two component columns. Four-lane
        // reduction below forms each output once, rather than four identical copies.
        if(2*q<K){int e=me[tile*K+h]+ve[col*K+2*q];
            sum0=__fadd_rn(sum0,tensor::scale(d[0],e));sum1=__fadd_rn(sum1,tensor::scale(d[2],e));}
        if(2*q+1<K){int e=me[tile*K+h]+ve[col*K+2*q+1];
            sum0=__fadd_rn(sum0,tensor::scale(d[1],e));sum1=__fadd_rn(sum1,tensor::scale(d[3],e));}
    }
    for(int d=2;d;d>>=1){sum0=__fadd_rn(sum0,__shfl_down_sync(0xffffffff,sum0,d,4));sum1=__fadd_rn(sum1,__shfl_down_sync(0xffffffff,sum1,d,4));}
}

template<unsigned K>
__device__ void product(const unsigned* columns,const unsigned* fragments,const int* me,
    const unsigned* vc,const int* ve,float* partial,unsigned tiles,unsigned compact){
    unsigned lane=threadIdx.x%32,tile=(blockIdx.x*blockDim.x+threadIdx.x)/32;
    if(tile>=tiles)return;
    float a,b;tile_product<K>(tile,columns,fragments,me,vc,ve,compact,a,b);
    if(!(lane%4)){partial[tile*16+lane/4]=a;partial[tile*16+lane/4+8]=b;}
}

template<unsigned K>
__device__ void combined(const unsigned* offsets,const unsigned* indices,const float* values,
    const unsigned* to,const unsigned* tc,const unsigned* fragments,const int* me,const unsigned* vc,const int* ve,
    const double* input,const double* input_anchor,const float* input_delta,const double* reference,double* state,double* extra,
    const double* anchor,const double* lower,const double* upper,const double* objective,double* product,unsigned* flags,
    unsigned rows,unsigned direction,double scale,double toward,double back,unsigned incremental,unsigned fused,
    const double* output_anchor,unsigned* output_codes,int* output_exponents,float* output_delta,unsigned compact,unsigned adaptive){
    unsigned lane=threadIdx.x%32,warp=threadIdx.x/32,half=blockIdx.x*2+warp/4;
    float a=0,b=0;
    if(half<(rows+15)/16){
        for(unsigned tile=to[half]+warp%4;tile<to[half+1];tile+=4){
            float x,y;tile_product<K>(tile,tc,fragments,me,vc,ve,compact,x,y);
            a=__fadd_rn(a,x);b=__fadd_rn(b,y);
        }
    }
    __shared__ float partial[128];
    __shared__ float remainder[32];
    __shared__ double encoded[32];
    if(!(lane%4)){partial[warp*16+lane/4]=a;partial[warp*16+lane/4+8]=b;}
    __syncthreads();
    unsigned local=threadIdx.x/8,row=blockIdx.x*32+local;
    unsigned count=row<rows?offsets[row+1]-offsets[row]:0;
    bool long_group=!adaptive||__any_sync(0xffffffff,count>64);
    if(long_group){
        // Only groups containing a long row serialize their four full-warp
        // reductions. Projection remains parallel across all 32 outputs.
        #pragma unroll 1
        for(unsigned pass=0;pass<4;pass++){
            unsigned target=warp*4+pass,r=blockIdx.x*32+target;float sum=0;
            if(r<rows){
                for(unsigned j=offsets[r]+lane;j<offsets[r+1];j+=32){
                    sum=__fadd_rn(sum,__fmul_rn(values[j],input_delta[indices[j]]));
                }
            }
            for(int d=16;d;d>>=1)sum=__fadd_rn(sum,__shfl_down_sync(0xffffffff,sum,d));
            if(!lane)remainder[target]=sum;
        }
    }else{
        float sum=0;
        if(row<rows)for(unsigned j=offsets[row]+lane%8;j<offsets[row+1];j+=8){
            sum=__fadd_rn(sum,__fmul_rn(values[j],input_delta[indices[j]]));
        }
        for(int d=4;d;d>>=1)sum=__fadd_rn(sum,__shfl_down_sync(0xffffffff,sum,d,8));
        if(!(lane%8))remainder[local]=sum;
    }
    __syncthreads();
    if(!(lane%8)){
            unsigned base=(local/16)*64+local%16;
            float tiles=__fadd_rn(__fadd_rn(partial[base],partial[base+32]),__fadd_rn(partial[base+16],partial[base+48]));
            encoded[local]=0;
            if(row<rows){
                double value=double(__fadd_rn(remainder[local],tiles));if(incremental)value=__dadd_rn(value,reference[row]);
                if(direction==2){product[row]=value;if(!isfinite(value))atomicOr(flags,1u);}
                else {
                    double old=state[row],next,e=0;
                    if(direction==0){next=fmin(upper[row],fmax(lower[row],old-scale*(objective[row]-value)));e=2*next-old;}
                    else {double raw=old-scale*value;next=raw-fmin(-scale*lower[row],fmax(-scale*upper[row],raw));}
                    double blended=toward*next+back*anchor[row];if(direction==1)e=blended;
                    if(!isfinite(value)||!isfinite(blended)||!isfinite(e))atomicOr(flags,1u);
                    else {state[row]=blended;if(direction==0)extra[row]=e;encoded[local]=e;
                        output_delta[row]=__double2float_rn(incremental?__dsub_rn(e,output_anchor[row]):e);}
                }
            }
    }
    __syncthreads();
    if(fused&&direction!=2&&warp==0){
        unsigned row=blockIdx.x*32+lane;double v=encoded[lane];
        if(incremental&&row<rows)v=__dsub_rn(v,output_anchor[row]);
        encode(v,row,rows,K,output_codes,output_exponents,flags);
    }
}

template<unsigned MODE,unsigned LANES>
__device__ void step(const unsigned* offsets,const unsigned* indices,const double* original,const float* values,
    const unsigned* tile_offsets,const float* partial,const double* input,const double* input_anchor,const double* reference,
    double* state,double* extra,const double* anchor,const double* lower,const double* upper,const double* objective,
    double* product,unsigned* flags,unsigned rows,unsigned direction,double scale,double toward,double back,unsigned incremental,
    unsigned fused,unsigned k,const double* output_anchor,unsigned* output_codes,int* output_exponents,const float* input_delta,float* output_delta){
    unsigned thread=blockIdx.x*blockDim.x+threadIdx.x,row=thread/LANES,lane=threadIdx.x%LANES;
    unsigned begin=row<rows?offsets[row]:0,end=row<rows?offsets[row+1]:0;
    double ds=0;float fs=0;
    for(unsigned j=begin+lane;j<end;j+=LANES){
        if(MODE==0)ds=__dadd_rn(ds,__dmul_rn(original[j],input[indices[j]]));
        else fs=__fadd_rn(fs,__fmul_rn(values[j],input_delta[indices[j]]));
    }
    if(MODE==2&&row<rows){
        for(unsigned tile=tile_offsets[row/16]+lane;tile<tile_offsets[row/16+1];tile+=LANES)
            fs=__fadd_rn(fs,partial[tile*16+row%16]);
    }
    #pragma unroll
    for(int d=LANES/2;d;d>>=1){
        if(MODE==0)ds=__dadd_rn(ds,__shfl_down_sync(0xffffffff,ds,d,LANES));
        else fs=__fadd_rn(fs,__shfl_down_sync(0xffffffff,fs,d,LANES));
    }
    double encoded=0;
    if(!lane&&row<rows){
        double value=MODE?double(fs):ds;
        if(MODE&&incremental)value=__dadd_rn(value,reference[row]);
        if(direction==2){product[row]=value;if(!isfinite(value))atomicOr(flags,1u);}
        else {
            double old=state[row],next;
            if(direction==0){next=fmin(upper[row],fmax(lower[row],old-scale*(objective[row]-value)));encoded=2*next-old;}
            else {double raw=old-scale*value;
                // Positive scale: project in scaled coordinates, avoiding a
                // full correctly-rounded FP64 division per output. This is a
                // search proposal; original-model checks remain authoritative.
                next=raw-fmin(-scale*lower[row],fmax(-scale*upper[row],raw));}
            double blended=toward*next+back*anchor[row];
            if(direction==1)encoded=blended;
            bool bad=!isfinite(value)||!isfinite(blended)||!isfinite(encoded);
            if(bad)atomicOr(flags,1u);
            else {state[row]=blended;if(direction==0)extra[row]=encoded;
                if(MODE)output_delta[row]=__double2float_rn(incremental?__dsub_rn(encoded,output_anchor[row]):encoded);}
        }
    }
    if constexpr(MODE==2&&LANES<=8){
        if(fused&&direction!=2){
            __shared__ double output[256/LANES];
            if(!lane)output[threadIdx.x/LANES]=encoded;
            __syncthreads();
            if(threadIdx.x<256/LANES){
                unsigned i=blockIdx.x*(256/LANES)+threadIdx.x;
                if(i/32<(rows+31)/32){
                    double v=i<rows?output[threadIdx.x]:0.;
                    if(incremental&&i<rows)v=__dsub_rn(v,output_anchor[i]);
                    encode(v,i,rows,k,output_codes,output_exponents,flags);
                }
            }
        }
    }
}
}
extern "C" __global__ void fast_encode(const double* input,const double* anchor,unsigned incremental,
    unsigned* codes,int* ex,unsigned* flags,unsigned n,unsigned k){
    unsigned i=blockIdx.x*blockDim.x+threadIdx.x;
    if(i/32>=(n+31)/32)return;
    double value=i<n?input[i]:0.;if(incremental&&i<n)value=__dsub_rn(value,anchor[i]);
    fast::encode(value,i,n,k,codes,ex,flags);
}
#define PRODUCT(K) extern "C" __global__ void fast_product_##K(const unsigned* c,const unsigned* f,const int* me,const unsigned* vc,const int* ve,float* p,unsigned n,unsigned compact){fast::product<K>(c,f,me,vc,ve,p,n,compact);}
PRODUCT(1) PRODUCT(2) PRODUCT(3) PRODUCT(4)
#define STEP(M,L) extern "C" __global__ void fast_step_##M##_##L(const unsigned* o,const unsigned* i,const double* a,const float* v,const unsigned* t,const float* p,const double* x,const double* xa,const double* r,double* s,double* e,const double* an,const double* lo,const double* hi,const double* c,double* out,unsigned* flags,unsigned n,unsigned dir,double scale,double toward,double back,unsigned inc,unsigned fused,unsigned k,const double* oa,unsigned* oc,int* oe,const float* id,float* od){fast::step<M,L>(o,i,a,v,t,p,x,xa,r,s,e,an,lo,hi,c,out,flags,n,dir,scale,toward,back,inc,fused,k,oa,oc,oe,id,od);}
STEP(0,1) STEP(0,4) STEP(0,8) STEP(0,32)
STEP(1,1) STEP(1,4) STEP(1,8) STEP(1,32)
STEP(2,1) STEP(2,4) STEP(2,8) STEP(2,32)
#define COMBINED(K) extern "C" __global__ void fast_combined_##K(const unsigned* o,const unsigned* i,const double* unused_a,const float* v,const unsigned* t,const float* unused_p,const double* x,const double* xa,const double* r,double* s,double* e,const double* an,const double* lo,const double* hi,const double* c,double* out,unsigned* flags,unsigned n,unsigned dir,double scale,double toward,double back,unsigned inc,unsigned fused,unsigned unused_k,const double* oa,unsigned* oc,int* oe,const float* id,float* od,const unsigned* tc,const unsigned* fragments,const int* me,const unsigned* vc,const int* ve,unsigned compact,unsigned adaptive){fast::combined<K>(o,i,v,t,tc,fragments,me,vc,ve,x,xa,id,r,s,e,an,lo,hi,c,out,flags,n,dir,scale,toward,back,inc,fused,oa,oc,oe,od,compact,adaptive);}
COMBINED(1) COMBINED(2) COMBINED(3) COMBINED(4)
