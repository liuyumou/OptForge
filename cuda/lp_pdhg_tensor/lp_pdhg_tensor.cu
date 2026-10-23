// ADR-0042: separate image; all included historical source bodies remain exact.
#include "../lp_pdhg_quant_resident/lp_pdhg_quant_resident.cu"
#include <cuda_fp16.h>
#include <cuda_bf16.h>
#include "fragment_layout.h"
using TU=unsigned int;using TW=unsigned long long;
struct T128{TU w[4];};
__device__ void tadd(T128&a,const T128&b){TW c=0;
#pragma unroll
for(int j=0;j<4;j++){TW v=(TW)a.w[j]+b.w[j]+c;a.w[j]=(TU)v;c=v>>32;}}
__device__ void tneg(T128&a){TW c=1;
#pragma unroll
for(int j=0;j<4;j++){TW v=(TW)(~a.w[j])+c;a.w[j]=(TU)v;c=v>>32;}}
__device__ void tpartial(T128&a,int v,int shift){T128 b={{0,0,0,0}};TW m=v<0?(TW)(-(long long)v):(TW)v;int word=shift/32,rem=shift%32;b.w[word]=(TU)(m<<rem);if(word+1<4)b.w[word+1]=(TU)(m>>(32-rem));if(v<0)tneg(b);tadd(a,b);}
__device__ TU tword(const T128&a,int i){return i>=0&&i<4?a.w[i]:0;}
__device__ bool tbit(const T128&a,int k){return k>=0&&k<128&&((tword(a,k/32)>>(k%32))&1u);}
__device__ bool tbelow(const T128&a,int k){TU any=0;
#pragma unroll
for(int j=0;j<4;j++){int n=k-j*32;TU mask=n>=32?~0u:n<=0?0u:(1u<<n)-1;any|=a.w[j]&mask;}return any!=0;}
__device__ double tround(T128 a,int base,TU&bad){bool negative=(a.w[3]>>31)!=0;if(negative)tneg(a);int top=-1;
#pragma unroll
for(int j=0;j<4;j++)if(a.w[j])top=j*32+31-__clz(a.w[j]);if(top<0)return 0.;
int unit=max(base+top-52,-1074),shift=unit-base;TW q=0;
if(shift<0){if(-shift>=64){bad|=4;return 0.;}q=((TW)a.w[0]|((TW)a.w[1]<<32))<<(-shift);}else if(shift<128){int word=shift/32,rem=shift%32;TW lo=(TW)tword(a,word)|((TW)tword(a,word+1)<<32);q=(lo>>rem)|(rem?(TW)tword(a,word+2)<<(64-rem):0);}
q&=(1ull<<53)-1;if(tbit(a,shift-1)&&(tbelow(a,shift-1)||(q&1)))q++;if(q==(1ull<<53)){q>>=1;unit++;}if(unit>971||!q){bad|=4;return 0.;}TW bits=q<(1ull<<52)?q:((TW)(unit+1075)<<52)|(q&((1ull<<52)-1));return __longlong_as_double(bits|((TW)negative<<63));}
__device__ int texp(double x){TW bits=(TW)__double_as_longlong(fabs(x));int f=(int)(bits>>52);if(!bits)return -1074;return f?f-1022:64-__clzll(bits)-1074;}
__device__ double tunit(int e){if(e<-1074)return __longlong_as_double(1);if(e>1023)return INFINITY;return ldexp(1.,e);}
__device__ long long tencode(double x,int exponent,TU &bad){TW bits=(TW)__double_as_longlong(x),m=bits&((1ull<<52)-1);int f=(int)(bits>>52)&2047,e=-1074;if(f==2047){bad|=4;return 0;}if(f){m|=1ull<<52;e=f-1075;}int shift=e-exponent+56;TW q=shift>=0?(shift<64?m<<shift:0):(shift>-64?m>>(-shift):0);if(q>=(1ull<<56)||(m&&!q)){bad|=4;return 0;}return bits>>63?-(long long)q:(long long)q;}
extern "C" __global__ void tn_norm(const double*v,double*norm,TU*control,TU n,TU native){
 __shared__ double a[256];TU l=threadIdx.x;if(control[0]){if(l==0)norm[2]=0;return;}double m=0.;for(TU i=l;i<n;i+=256){if(!isfinite(v[i]))m=INFINITY;else m=fmax(m,fabs(v[i]));}a[l]=m;__syncthreads();for(TU k=128;k;k>>=1){if(l<k)a[l]=fmax(a[l],a[l+k]);__syncthreads();}if(l==0){norm[0]=a[0];norm[1]=native||a[0]==0?0:tunit(texp(a[0])-56);norm[2]=isfinite(a[0])?1:0;if(!isfinite(a[0]))atomicOr(control,2u);}}
extern "C" __global__ void tn_pack(const double*v,long long*q,int*exponents,const TU*active,TU*control,const double*norm,TU n,TU native){
 TU i=blockIdx.x*blockDim.x+threadIdx.x;if(i>=n||native||norm[2]==0||!active[i/32])return;TU block=i/32;double m=0;for(TU j=block*32;j<min(n,block*32+32);j++)m=fmax(m,fabs(v[j]));int e=texp(m);TU bad=0;q[i]=tencode(v[i],e,bad);if((i&31)==0)exponents[block]=e;if(bad)atomicOr(control,bad);}
__device__ int tdigit(long long v,int index,int bits,int limbs){TW m=v<0?(TW)(-v):(TW)v;int d=(int)((m>>((limbs-1-index)*bits))&((1u<<bits)-1));return v<0?-d:d;}
__device__ TU tpair(int a,int b,bool bf){if(bf)return (TU)__bfloat16_as_ushort(__float2bfloat16_rn((float)a))|((TU)__bfloat16_as_ushort(__float2bfloat16_rn((float)b))<<16);return (TU)__half_as_ushort(__float2half_rn((float)a))|((TU)__half_as_ushort(__float2half_rn((float)b))<<16);}
// A=row major, B=column major; one warp owns a 16x32 matrix half tile.
template<int Mode> __device__ void ttile(const long long*a,const int*ae,const TU*rows,const TU*columns,const long long*x,const int*xe,double*out,TU*tile_flags,TW*work,const double*norm,const TU*control,TU tiles,TU transpose,TU native){
 TU warp=(blockIdx.x*blockDim.x+threadIdx.x)/32,lane=threadIdx.x&31,tile=warp/2,half=warp&1;if(tile>=tiles||native||norm[2]==0||control[0])return;
 TU group=lane/4,thread=lane%4;int bits=Mode==2?4:7,limbs=Mode==2?14:8;TU xb=transpose?rows[tile]:columns[tile];T128 top={{0,0,0,0}},bottom=top;TW instructions=0;
 #pragma unroll 1
 for(int i=0;i<limbs;i++){
 #pragma unroll 1
 for(int bg=0;bg<(limbs+7)/8;bg++){
  int c[4]={0,0,0,0};float f[4]={0,0,0,0};
  for(int chunk=0;chunk<(Mode==0?1:2);chunk++){
   TU ar[4],br[2]={0,0};
#pragma unroll
   for(int r=0;r<4;r++){
    TU row=tensor_a_row(half,group,r);TU packed=0;
#pragma unroll
    for(int k=0;k<(Mode==0?4:2);k++){TU col=tensor_a_col(thread,Mode,r,chunk,k),rr=transpose?col:row,cc=transpose?row:col;int d=tdigit(a[tile*1024+rr*32+cc],i,bits,limbs);if(Mode==0)packed|=(TU)(unsigned char)(signed char)d<<(8*k);else if(k==0)packed=(TU)(Mode==2?__bfloat16_as_ushort(__float2bfloat16_rn((float)d)):__half_as_ushort(__float2half_rn((float)d)));else packed|=(TU)(Mode==2?__bfloat16_as_ushort(__float2bfloat16_rn((float)d)):__half_as_ushort(__float2half_rn((float)d)))<<16;}
    ar[r]=packed;
   }
#pragma unroll
   for(int r=0;r<2;r++){
    TU packed=0;int j=bg*8+group;
#pragma unroll
    for(int k=0;k<(Mode==0?4:2);k++){TU row=tensor_b_row(thread,Mode,r,chunk,k);int d=j<limbs?tdigit(x[xb*32+row],j,bits,limbs):0;if(Mode==0)packed|=(TU)(unsigned char)(signed char)d<<(8*k);else if(k==0)packed=(TU)(Mode==2?__bfloat16_as_ushort(__float2bfloat16_rn((float)d)):__half_as_ushort(__float2half_rn((float)d)));else packed|=(TU)(Mode==2?__bfloat16_as_ushort(__float2bfloat16_rn((float)d)):__half_as_ushort(__float2half_rn((float)d)))<<16;}
    br[r]=packed;
   }
   if constexpr(Mode==0){asm volatile("mma.sync.aligned.m16n8k32.row.col.s32.s8.s8.s32 {%0,%1,%2,%3}, {%4,%5,%6,%7}, {%8,%9}, {%0,%1,%2,%3};":"+r"(c[0]),"+r"(c[1]),"+r"(c[2]),"+r"(c[3]):"r"(ar[0]),"r"(ar[1]),"r"(ar[2]),"r"(ar[3]),"r"(br[0]),"r"(br[1]));}
   else if constexpr(Mode==1){asm volatile("mma.sync.aligned.m16n8k16.row.col.f32.f16.f16.f32 {%0,%1,%2,%3}, {%4,%5,%6,%7}, {%8,%9}, {%0,%1,%2,%3};":"+f"(f[0]),"+f"(f[1]),"+f"(f[2]),"+f"(f[3]):"r"(ar[0]),"r"(ar[1]),"r"(ar[2]),"r"(ar[3]),"r"(br[0]),"r"(br[1]));}
   else {asm volatile("mma.sync.aligned.m16n8k16.row.col.f32.bf16.bf16.f32 {%0,%1,%2,%3}, {%4,%5,%6,%7}, {%8,%9}, {%0,%1,%2,%3};":"+f"(f[0]),"+f"(f[1]),"+f"(f[2]),"+f"(f[3]):"r"(ar[0]),"r"(ar[1]),"r"(ar[2]),"r"(ar[3]),"r"(br[0]),"r"(br[1]));}
   instructions++;
  }
#pragma unroll
  for(int k=0;k<2;k++){int j=bg*8+thread*2+k;if(j<limbs){int shift=(2*limbs-2-i-j)*bits;tpartial(top,Mode==0?c[k]:(int)f[k],shift);tpartial(bottom,Mode==0?c[k+2]:(int)f[k+2],shift);}}
 }
 }
 // Sum the eight vector component columns across the four lanes owning a row.
#pragma unroll
 for(int offset=1;offset<4;offset*=2){T128 b,d;
#pragma unroll
  for(int j=0;j<4;j++){b.w[j]=__shfl_xor_sync(0xffffffffu,top.w[j],offset);d.w[j]=__shfl_xor_sync(0xffffffffu,bottom.w[j],offset);}tadd(top,b);tadd(bottom,d);}
 if(thread==0){TU bad=0;int e=ae[tile]+xe[xb]-112;out[tile*32+half*16+group]=tround(top,e,bad);out[tile*32+half*16+group+8]=tround(bottom,e,bad);tile_flags[tile*32+half*16+group]=bad;tile_flags[tile*32+half*16+group+8]=bad;}
 if(lane==0)work[warp]+=instructions;
}
#define TENTRY(Name,Mode) extern "C" __global__ void Name(const long long*a,const int*ae,const TU*r,const TU*c,const long long*x,const int*xe,double*out,TU*flags,TW*work,const double*norm,const TU*control,TU tiles,TU transpose,TU native){ttile<Mode>(a,ae,r,c,x,xe,out,flags,work,norm,control,tiles,transpose,native);}
TENTRY(tn_int8,0)
TENTRY(tn_fp16,1)
TENTRY(tn_bf16,2)
extern "C" __global__ void tn_simt(const long long*a,const int*ae,const TU*r,const TU*c,const long long*x,const int*xe,double*out,TU*flags,TW*work,const double*norm,const TU*control,TU tiles,TU transpose,TU native){
 TU i=blockIdx.x*blockDim.x+threadIdx.x,tile=i/32,row=i%32;if(tile>=tiles||native||norm[2]==0||control[0])return;TU xb=transpose?r[tile]:c[tile];T128 sum={{0,0,0,0}};
 for(TU k=0;k<32;k++){long long av=a[tile*1024+(transpose?k*32+row:row*32+k)],bv=x[xb*32+k];TW am=av<0?(TW)(-av):(TW)av,bm=bv<0?(TW)(-bv):(TW)bv,lo=am*bm,hi=__umul64hi(am,bm);T128 p={{(TU)lo,(TU)(lo>>32),(TU)hi,(TU)(hi>>32)}};if((av<0)!=(bv<0))tneg(p);tadd(sum,p);}TU bad=0;out[i]=tround(sum,ae[tile]+xe[xb]-112,bad);flags[i]=bad;if(row==0)work[tile*2]++;}
extern "C" __global__ void tn_product(const double*original,const TU*line,const TU*group,const TU*tiles,const TU*ids,const TU*inputs,const int*selected,const TU*promoted,const double*constants,double*bounds,const double*scales,const double*v,double*out,const double*norm,TU*control,TU*flags,TW*stats,const double*parts,const TU*part_flags,TU count,TU start){
 TU i=blockIdx.x*blockDim.x+threadIdx.x;if(i>=count||norm[2]==0)return;TU row=start+i;double total=0.;TU flag=0;TW low_count=0,high_count=0,nonzero=0;
 for(TU g=line[row];g<line[row+1];g++){TU tile=tiles[g];bool low=!promoted[tile];double sum=0.;if(low){TU at=(TU)selected[tile]*32+i%32;sum=parts[at];flag|=part_flags[at];if(control[0]&4)flag|=4;}
  for(TU k=group[g];k<group[g+1];k++){TU id=ids[k];double x=v[inputs[k]];if(low){low_count++;if(x!=0)nonzero++;}else{high_count++;double p=__dmul_rn(original[id],x);if(qbadmul(original[id],x,p))flag|=2;sum=__dadd_rn(sum,p);}}
 total=__dadd_rn(total,sum);if(!isfinite(total))flag|=low?4u:2u;}
 double bound=qa(qd(qa(qa(qm(constants[3*row],norm[0]),qm(constants[3*row+1],norm[1])),constants[3*row+2]),scales[row]),__longlong_as_double(1));if(!(bound<=1.e-7))flag|=1;out[i]=total;bounds[row]=bound;flags[row]=flag;if(flag){atomicOr(control,flag);atomicCAS(control+2,0u,start?1u:2u);}TW*s=stats+7*row;s[0]+=low_count;s[1]+=high_count;s[2]+=nonzero;if(bound<=1.e-7)s[3]++;else s[5]++;
}
extern "C" __global__ void tn_work_reset(TW*work,TU n){TU i=blockIdx.x*blockDim.x+threadIdx.x;if(i<n)work[i]=0;}
extern "C" __global__ void tn_work_collect(const TW*work,TW*out,TU n){__shared__ TW v[256];TU l=threadIdx.x;TW s=0;for(TU i=l;i<n;i+=256)s+=work[i];v[l]=s;__syncthreads();for(TU k=128;k;k>>=1){if(l<k)v[l]+=v[l+k];__syncthreads();}if(l==0)out[0]=v[0];}
