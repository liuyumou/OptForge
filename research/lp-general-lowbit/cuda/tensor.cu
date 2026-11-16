// SPEC-0045 actual SM120 normal-E2M1 MMA; sparse remainder, FP64 state.
#include "lowbit.cu"
namespace tensor {
__device__ float scale(float x,int e){return __fmul_rn(x,__int_as_float((e+127)<<23));}
__device__ unsigned quant(float v){
    bool neg=v<0;v=fabsf(v);unsigned c=0;
    const float mid[6]={.5f,1.25f,1.75f,2.5f,3.5f,5.f};
    for(int j=0;j<6;j++){unsigned next=j+2;if(v>mid[j]||(v==mid[j]&&next!=2&&!(next&1)))c=next;}
    return c|((neg&&c)?8:0);
}
__device__ double maxall(double x){for(int d=16;d;d>>=1)x=fmax(x,__shfl_xor_sync(0xffffffff,x,d));return x;}
__device__ unsigned expand(unsigned v){return ((v&15)<<2)|((v&0xf0)<<6)|((v&0xf00)<<10)|((v&0xf000)<<14);}
__device__ void mma(float* d,const unsigned* a,const unsigned* b){
    asm volatile("mma.sync.aligned.m16n8k32.row.col.kind::f8f6f4.f32.e2m1.e2m1.f32 {%0,%1,%2,%3},{%4,%5,%6,%7},{%8,%9},{%10,%11,%12,%13};"
    : "=f"(d[0]),"=f"(d[1]),"=f"(d[2]),"=f"(d[3])
    : "r"(a[0]),"r"(a[1]),"r"(a[2]),"r"(a[3]),"r"(b[0]),"r"(b[1]),"f"(0.f),"f"(0.f),"f"(0.f),"f"(0.f));
}
}
extern "C" __global__ void tensor_encode(const double* input,const double* anchor,unsigned incremental,unsigned* codes,int* ex,double* norms,unsigned n,unsigned k){
    unsigned lane=threadIdx.x%32,block=(blockIdx.x*blockDim.x+threadIdx.x)/32,i=block*32+lane;
    if(block>=((n+31)/32))return;
    double value=i<n?input[i]:0.,round=0.;
    if(incremental&&i<n){round=general::mul(0x1p-52,general::add(fabs(value),fabs(anchor[i])));value=__dsub_rn(value,anchor[i]);}
    bool bad=!isfinite(value)||fabs(value)>0x1p40;
    bool invalid=__any_sync(0xffffffff,bad);float v=invalid?0.f:__double2float_rn(value);
    double decoded=0.,absolute=0.;
    for(unsigned h=0;h<k;h++){
        float largest=__uint_as_float(__reduce_max_sync(0xffffffff,__float_as_uint(fabsf(v))));
        int e=max(-48,int(__float_as_uint(largest)>>23)-129);
        if(largest>tensor::scale(6.f,e))++e;
        unsigned c=tensor::quant(tensor::scale(v,-e));unsigned word=c;
        for(int d=1;d<8;d<<=1)word|=__shfl_down_sync(0xffffffff,word,d)<<(4*d);
        if(!(lane&7))codes[(block*k+h)*4+lane/8]=word;
        if(!lane)ex[block*k+h]=e;
        float part=tensor::scale(general::fp4(c),e);v=__fsub_rn(v,part);
        decoded=__dadd_rn(decoded,double(part));absolute=general::add(absolute,fabs(double(part)));
    }
    double err=general::add(fabs(__dsub_rn(value,decoded)),general::mul(0x1p-49,general::add(fabs(value),absolute)));
    double mag=tensor::maxall(general::add(fabs(value),round));err=tensor::maxall(general::add(err,round));absolute=tensor::maxall(absolute);
    if(!lane){norms[3*block]=invalid?INFINITY:mag;norms[3*block+1]=invalid?INFINITY:err;norms[3*block+2]=absolute;}
}
extern "C" __global__ void tensor_product(const unsigned* offsets,const unsigned* columns,const unsigned* fragments,
    const int* me,const double* meta,const unsigned* vc,const int* ve,const double* norms,double* products,double* bounds,unsigned rows,unsigned k,unsigned compact){
    unsigned lane=threadIdx.x%32,group=(blockIdx.x*blockDim.x+threadIdx.x)/32,g=lane/4,q=lane%4;
    if(group>=((rows+15)/16))return;
    float sum0=0,sum1=0;double error=0,magnitude=0;
    unsigned begin=offsets[group],end=offsets[group+1];
    for(unsigned tile=begin;tile<end;tile++){
        unsigned col=columns[tile];
        for(unsigned h=0;h<k;h++){
            unsigned a[4],b[2]={0,0};
            if(compact){const uint2 f=*reinterpret_cast<const uint2*>(fragments+(tile*k+h)*64+lane*2);
                a[0]=tensor::expand(f.x);a[1]=tensor::expand(f.x>>16);a[2]=tensor::expand(f.y);a[3]=tensor::expand(f.y>>16);}
            else {const uint4 f=*reinterpret_cast<const uint4*>(fragments+(tile*k+h)*128+lane*4);a[0]=f.x;a[1]=f.y;a[2]=f.z;a[3]=f.w;}
            if(g<k)for(unsigned j=0;j<2;j++)for(unsigned z=0;z<4;z++){
                unsigned pos=q*4+z+j*16;unsigned code=(vc[(col*k+g)*4+pos/8]>>((pos%8)*4))&15;
                b[j]|=code<<(2+z*8);
            }
            float d[4];tensor::mma(d,a,b);
            for(unsigned s=0;s<k;s++){
                float x0=__shfl_sync(0xffffffff,d[s%2],g*4+s/2);
                float x1=__shfl_sync(0xffffffff,d[2+s%2],g*4+s/2);
                sum0=__fadd_rn(sum0,tensor::scale(x0,me[tile*k+h]+ve[col*k+s]));
                sum1=__fadd_rn(sum1,tensor::scale(x1,me[tile*k+h]+ve[col*k+s]));
            }
        }
        if(lane<16){double er=meta[tile*32+2*lane],mag=meta[tile*32+2*lane+1];
            error=general::add(error,general::add(general::mul(er,norms[3*col]),general::mul(mag,norms[3*col+1])));
            magnitude=general::add(magnitude,general::mul(mag,norms[3*col+2]));}
    }
    float p0=__shfl_sync(0xffffffff,sum0,(lane%8)*4),p1=__shfl_sync(0xffffffff,sum1,(lane%8)*4);
    unsigned row=group*16+lane;
    if(lane<16&&row<rows){products[row]=lane<8?double(p0):double(p1);
        // Unscaled MMA sums are exact quarter-integers. Power-of-two scaling is
        // exact in the admitted range; only accumulation across components/tiles rounds.
        bounds[row]=begin==end?0.:general::add(error,general::mul(general::gamma(k*k*(end-begin)+1,0x1p-24),magnitude));}
}
extern "C" __global__ void tensor_step(const unsigned* offsets,const unsigned* indices,const double* original,
    const unsigned* ro,const unsigned* ri,const double* rv,const float* fpvalues,const double* fpmeta,
    const unsigned* covered,const double* tiles,const double* tilebounds,const double* input,const double* reference,const double* reference_error,const double* input_anchor,
    double* state,double* extra,const double* anchor,const double* lower,const double* upper,const double* objective,
    unsigned* flags,unsigned long long* work,double* product,double* bound,
    unsigned rows,unsigned mode,unsigned direction,double step,double toward,double back,double limit,unsigned incremental){
    unsigned row=blockIdx.x*8+threadIdx.x/32,lane=threadIdx.x%32;
    unsigned begin=row<rows?offsets[row]:0,end=row<rows?offsets[row+1]:0;
    unsigned lo=mode>=2?(row<rows?ro[row]:0):begin,hi=mode>=2?(row<rows?ro[row+1]:0):end;
    const unsigned* idx=mode>=2?ri:indices;const double* vals=mode>=2?rv:original;
    double sum=0,absolute=0,xmax=0,xerr=0,subtract_error=0;float fs=0,fa=0;
    for(unsigned j=lo+lane;j<hi;j+=32){double x=input[idx[j]],round=0.;
        if(incremental&&mode){round=general::mul(0x1p-52,general::add(fabs(x),fabs(input_anchor[idx[j]])));x=__dsub_rn(x,input_anchor[idx[j]]);}
        if(mode==1){float xf=__double2float_rn(x),af=fpvalues[j],p=__fmul_rn(af,xf);fs=__fadd_rn(fs,p);fa=__fadd_ru(fa,fabsf(p));
            xmax=fmax(xmax,general::add(fabs(x),round));xerr=fmax(xerr,general::add(fabs(__dsub_rn(x,double(xf))),round));}
        else {double a=vals[j];subtract_error=general::add(subtract_error,general::mul(fabs(a),round));double p=__dmul_rn(a,x);sum=__dadd_rn(sum,p);absolute=general::add(absolute,fabs(p));}
    }
    for(int d=16;d;d>>=1){sum=__dadd_rn(sum,__shfl_down_sync(0xffffffff,sum,d));absolute=general::add(absolute,__shfl_down_sync(0xffffffff,absolute,d));
        fs=__fadd_rn(fs,__shfl_down_sync(0xffffffff,fs,d));fa=__fadd_ru(fa,__shfl_down_sync(0xffffffff,fa,d));
        subtract_error=general::add(subtract_error,__shfl_down_sync(0xffffffff,subtract_error,d));
        xmax=fmax(xmax,__shfl_down_sync(0xffffffff,xmax,d));xerr=fmax(xerr,__shfl_down_sync(0xffffffff,xerr,d));}
    double value=sum,error=0;bool correct=false;
    if(!lane&&row<rows){
        error=general::add(general::mul(general::gamma(2*(hi-lo)+32,0x1p-52),absolute),0x1p-1000);
        error=general::add(error,subtract_error);
        if(mode==1){value=double(fs);error=general::add(general::mul(fpmeta[2*row],xmax),general::mul(fpmeta[2*row+1],xerr));
            error=general::add(error,general::mul(general::gamma(2*((end-begin+31)/32)+16,0x1p-24),double(fa)));
            error=general::add(error,general::mul(double(4*(end-begin)+32),0x1p-149));}
        if(mode>=2){value=__dadd_rn(value,tiles[row]);error=general::add(error,tilebounds[row]);
            error=general::add(error,general::mul(0x1p-52,general::add(fabs(sum),fabs(tiles[row]))));}
        if(incremental&&mode){error=general::add(error,reference_error[row]);error=general::add(error,general::mul(0x1p-52,general::add(fabs(value),fabs(reference[row]))));value=__dadd_rn(reference[row],value);}
        if(begin==end){value=0;error=0;}
        correct=mode&&(!isfinite(value)||!isfinite(error)||general::mul(step,error)>limit);
    }
    correct=__shfl_sync(0xffffffff,int(correct),0);
    if(correct){sum=0;absolute=0;for(unsigned j=begin+lane;j<end;j+=32){double p=__dmul_rn(original[j],input[indices[j]]);sum=__dadd_rn(sum,p);absolute=general::add(absolute,fabs(p));}
        for(int d=16;d;d>>=1){sum=__dadd_rn(sum,__shfl_down_sync(0xffffffff,sum,d));absolute=general::add(absolute,__shfl_down_sync(0xffffffff,absolute,d));}
        value=sum;error=general::add(general::mul(general::gamma(2*(end-begin)+32,0x1p-52),absolute),0x1p-1000);}
    if(!lane&&row<rows){
        if(direction==2){product[row]=value;bound[row]=error;return;}
        unsigned tc=mode>=2?covered[row]:0;work[4*row]+=tc;work[4*row+1]+=correct?0:tc;work[4*row+2]+=correct?(end-begin):0;work[4*row+3]+=end-begin;
        double old=state[row],next;
        if(direction==0){next=fmin(upper[row],fmax(lower[row],old-step*(objective[row]-value)));extra[row]=2*next-old;}
        else {double raw=old-step*value;next=raw-step*fmin(-lower[row],fmax(-upper[row],raw/step));}
        double blended=toward*next+back*anchor[row];bool bad=!isfinite(value)||!isfinite(blended)||(direction==0&&!isfinite(extra[row]));
        flags[row]|=bad?1:0;if(!bad)state[row]=blended;
    }
}
extern "C" __global__ void tensor_totals(const unsigned long long* work,unsigned long long* out,unsigned rows){
    __shared__ unsigned long long partial[8*4];unsigned lane=threadIdx.x%32,w=threadIdx.x/32;
    for(unsigned q=0;q<4;q++){unsigned long long sum=0;for(unsigned r=threadIdx.x;r<rows;r+=blockDim.x)sum+=work[4*r+q];
        for(int d=16;d;d>>=1)sum+=__shfl_down_sync(0xffffffff,sum,d);
        if(!lane)partial[4*w+q]=sum;__syncthreads();
        if(!threadIdx.x){sum=0;for(unsigned h=0;h<8;h++)sum+=partial[4*h+q];out[q]=sum;}__syncthreads();}
}

// Original-A anchors: lane depth, rather than full row length, bounds the fixed
// 32-lane tree. A doubled unit roundoff covers product/absolute-sum conversion.
extern "C" __global__ void tensor_reference(const unsigned* offsets,const unsigned* indices,const double* values,const double* x,double* out,double* error,unsigned rows){
    unsigned row=blockIdx.x*8+threadIdx.x/32,lane=threadIdx.x%32;
    unsigned begin=row<rows?offsets[row]:0,end=row<rows?offsets[row+1]:0;double sum=0,absolute=0;
    for(unsigned j=begin+lane;j<end;j+=32){double p=__dmul_rn(values[j],x[indices[j]]);sum=__dadd_rn(sum,p);absolute=general::add(absolute,fabs(p));}
    for(int d=16;d;d>>=1){sum=__dadd_rn(sum,__shfl_down_sync(0xffffffff,sum,d));absolute=general::add(absolute,__shfl_down_sync(0xffffffff,absolute,d));}
    if(!lane&&row<rows){out[row]=sum;error[row]=begin==end?0.:general::add(general::mul(general::gamma((end-begin+31)/32+8,0x1p-52),absolute),0x1p-1000);}
}
