// ADR-0040: canonical sparse tiles, fixed warp reductions, no contraction or FTZ.
#include <math.h>
__device__ float decode(const unsigned char* codes,unsigned int id,unsigned int format,int scale){
 unsigned int code=format==0?((const unsigned short*)codes)[id]:codes[id];
 unsigned int mb=format==0?10:format==1?3:2, eb=format==1?4:5;
 int bias=format==1?7:15;unsigned int mag=code&((1u<<(mb+eb))-1),e=mag>>mb,m=mag&((1u<<mb)-1);
 float value=e?ldexpf((float)((1u<<mb)+m),(int)e-bias-(int)mb+scale):ldexpf((float)m,1-bias-(int)mb+scale);
 return code&(1u<<(mb+eb))?-value:value;
}
extern "C" __global__ void quant_product(const double* original,const unsigned char* codes,
 const unsigned int* line_offsets,const unsigned int* group_offsets,const unsigned int* tiles,
 const unsigned int* ids,const unsigned int* inputs,const int* exponents,const unsigned int* promoted,
 const double* vector,double* output,unsigned int* guards,unsigned int count,unsigned int start,unsigned int format){
 unsigned int line=(blockIdx.x*blockDim.x+threadIdx.x)/32,lane=threadIdx.x&31;
 if(line>=count)return;double total=0.0;unsigned int guard=0;
 for(unsigned int group=line_offsets[start+line];group<line_offsets[start+line+1];++group){
  unsigned int tile=tiles[group];bool low=!promoted[tile];double sum=0.0;
  unsigned int entry=group_offsets[group]+lane;
  if(entry<group_offsets[group+1]){unsigned int id=ids[entry];double x=vector[inputs[entry]],a=original[id];
   if(!isfinite(x))guard|=1;
   if(low){float q=decode(codes,id,format,exponents[tile]),v=__double2float_rn(x);float product=__fmul_rn(q,v);sum=(double)product;
    if(!isfinite(q)||!isfinite(v)||!isfinite(product))guard|=1;
    if((x!=0.0&&v==0.0f)||(q!=0.0f&&v!=0.0f&&product==0.0f))guard|=2;
   }else{sum=__dmul_rn(a,x);if(!isfinite(sum))guard|=1;if(a!=0.0&&x!=0.0&&sum==0.0)guard|=2;}
  }
  for(unsigned int k=16;k;k>>=1){double other=__shfl_down_sync(0xffffffffu,sum,k);unsigned int g=__shfl_down_sync(0xffffffffu,guard,k);if(lane<k){sum=low?(double)__fadd_rn((float)sum,(float)other):__dadd_rn(sum,other);guard|=g;if(!isfinite(sum))guard|=1;}}
  if(lane==0){total=__dadd_rn(total,sum);if(!isfinite(total))guard|=1;}
 }
 if(lane==0){output[line]=total;guards[line]=guard;}
}
