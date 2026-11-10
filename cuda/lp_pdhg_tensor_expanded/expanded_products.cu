// ADR-0046 component main products and fused expanded working-state updates.
// This module has no host executor and cannot publish an audited endpoint.
#include "expanded_compact_helpers.h"
#include "expanded_fast.h"
#include "expanded_storage.h"
#include <cuda_fp16.h>
#include <cuda_bf16.h>
#include "../lp_pdhg_tensor_warp32/fragment_layout.h"
using TU=U;using TW=W;
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
__device__ Value xround(T128 value,int base,U &guard) {
 U negative=value.w[3]>>31;if(negative)tneg(value);
 W lo=(W)value.w[0]|((W)value.w[1]<<32),hi=(W)value.w[2]|((W)value.w[3]<<32);
 if(hi>=(1ull<<61)){guard|=8u;return {0,0,0};}
 return rounded<64>(from_words(lo,hi,0),base,negative,guard);
}
__device__ int xdigit(W magnitude,U sign,int index,int bits,int limbs) {
 int shift=(limbs-1-index)*bits;
 int d=shift>=64?0:(int)((magnitude>>shift)&((1u<<bits)-1));
 return sign?-d:d;
}
__device__ int tdigit(long long value,int index,int bits,int limbs) {
 W magnitude=value<0?(W)(-value):(W)value;
 return xdigit(magnitude,(U)(value<0),index,bits,limbs);
}
// A=row major, B=column major; one warp owns a 16x32 matrix half tile.
template<int Mode> __device__ void xtile(const long long*a,const int*ae,const TU*rows,const TU*columns,const TW*x,const TU*xs,const int*xe,ExpandedOut out,TU*tile_flags,TW*work,const double*norm,const TU*control,TU tiles,TU transpose,TU native){
 TU warp=(blockIdx.x*blockDim.x+threadIdx.x)/32,lane=threadIdx.x&31,tile=warp/2,half=warp&1;if(tile>=tiles||native||norm[2]==0||control[0])return;
 TU group=lane/4,thread=lane%4;int bits=Mode==2?4:7,limbs=Mode==2?14:8,xlimbs=Mode==2?16:10;TU xb=transpose?rows[tile]:columns[tile];T128 top={{0,0,0,0}},bottom=top;TW instructions=0;
 #pragma unroll 1
 for(int i=0;i<limbs;i++){
 #pragma unroll 1
 for(int bg=0;bg<(xlimbs+7)/8;bg++){
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
    for(int k=0;k<(Mode==0?4:2);k++){TU row=tensor_b_row(thread,Mode,r,chunk,k);int d=j<xlimbs?xdigit(x[xb*32+row],xs[xb*32+row],j,bits,xlimbs):0;if(Mode==0)packed|=(TU)(unsigned char)(signed char)d<<(8*k);else if(k==0)packed=(TU)(Mode==2?__bfloat16_as_ushort(__float2bfloat16_rn((float)d)):__half_as_ushort(__float2half_rn((float)d)));else packed|=(TU)(Mode==2?__bfloat16_as_ushort(__float2bfloat16_rn((float)d)):__half_as_ushort(__float2half_rn((float)d)))<<16;}
    br[r]=packed;
   }
   if constexpr(Mode==0){asm volatile("mma.sync.aligned.m16n8k32.row.col.s32.s8.s8.s32 {%0,%1,%2,%3}, {%4,%5,%6,%7}, {%8,%9}, {%0,%1,%2,%3};":"+r"(c[0]),"+r"(c[1]),"+r"(c[2]),"+r"(c[3]):"r"(ar[0]),"r"(ar[1]),"r"(ar[2]),"r"(ar[3]),"r"(br[0]),"r"(br[1]));}
   else if constexpr(Mode==1){asm volatile("mma.sync.aligned.m16n8k16.row.col.f32.f16.f16.f32 {%0,%1,%2,%3}, {%4,%5,%6,%7}, {%8,%9}, {%0,%1,%2,%3};":"+f"(f[0]),"+f"(f[1]),"+f"(f[2]),"+f"(f[3]):"r"(ar[0]),"r"(ar[1]),"r"(ar[2]),"r"(ar[3]),"r"(br[0]),"r"(br[1]));}
   else {asm volatile("mma.sync.aligned.m16n8k16.row.col.f32.bf16.bf16.f32 {%0,%1,%2,%3}, {%4,%5,%6,%7}, {%8,%9}, {%0,%1,%2,%3};":"+f"(f[0]),"+f"(f[1]),"+f"(f[2]),"+f"(f[3]):"r"(ar[0]),"r"(ar[1]),"r"(ar[2]),"r"(ar[3]),"r"(br[0]),"r"(br[1]));}
   instructions++;
  }
#pragma unroll
  for(int k=0;k<2;k++){int j=bg*8+thread*2+k;if(j<xlimbs){int shift=(limbs+xlimbs-2-i-j)*bits;tpartial(top,Mode==0?c[k]:(int)f[k],shift);tpartial(bottom,Mode==0?c[k+2]:(int)f[k+2],shift);}}
 }
 }
 // Sum the eight vector component columns across the four lanes owning a row.
#pragma unroll
 for(int offset=1;offset<4;offset*=2){T128 b,d;
#pragma unroll
  for(int j=0;j<4;j++){b.w[j]=__shfl_xor_sync(0xffffffffu,top.w[j],offset);d.w[j]=__shfl_xor_sync(0xffffffffu,bottom.w[j],offset);}tadd(top,b);tadd(bottom,d);}
 if(thread==0){TU bad=0;int e=ae[tile]+xe[xb]-120;Value a=xround(top,e,bad),b=xround(bottom,e,bad);if(!bad){expanded_store(out,tile*32+half*16+group,a);expanded_store(out,tile*32+half*16+group+8,b);}tile_flags[tile*32+half*16+group]=bad;tile_flags[tile*32+half*16+group+8]=bad;}
 if(lane==0)work[warp]+=instructions;
}
#define TENTRY(Name,Mode) extern "C" __global__ void Name(const long long*a,const int*ae,const TU*r,const TU*c,const TW*x,const TU*xs,const int*xe,ExpandedOut out,TU*flags,TW*work,const double*norm,const TU*control,TU tiles,TU transpose,TU native){xtile<Mode>(a,ae,r,c,x,xs,xe,out,flags,work,norm,control,tiles,transpose,native);}
TENTRY(xe_int8_main,0)
TENTRY(xe_fp16_main,1)
TENTRY(xe_bf16_main,2)
extern "C" __global__ void xe_simt_main(const long long*a,const int*ae,const TU*r,const TU*c,const TW*x,const TU*xs,const int*xe,ExpandedOut out,TU*flags,TW*work,const double*norm,const TU*control,TU tiles,TU transpose,TU native){
 TU i=blockIdx.x*blockDim.x+threadIdx.x,tile=i/32,row=i%32;if(tile>=tiles||native||norm[2]==0||control[0])return;TU xb=transpose?r[tile]:c[tile];T128 sum={{0,0,0,0}};
 for(TU k=0;k<32;k++){long long av=a[tile*1024+(transpose?k*32+row:row*32+k)];TW am=av<0?(TW)(-av):(TW)av,bm=x[xb*32+k],lo=am*bm,hi=__umul64hi(am,bm);T128 p={{(TU)lo,(TU)(lo>>32),(TU)hi,(TU)(hi>>32)}};if((av<0)!=(xs[xb*32+k]!=0))tneg(p);tadd(sum,p);}TU bad=0;Value result=xround(sum,ae[tile]+xe[xb]-120,bad);if(!bad)expanded_store(out,i,result);flags[i]=bad;if(row==0)work[tile*2]++;}

#include "expanded_updates.cuh"
