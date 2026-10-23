// ADR-0041: original tuned exports remain exact; new guarded resident kernels.
#include "../lp_pdhg_tuned/lp_pdhg_tuned.cu"
#include <math.h>
__device__ double qup(double x){return !isfinite(x)?x:__longlong_as_double(__double_as_longlong(x)+1);}
__device__ double qa(double a,double b){return a==0?b:b==0?a:qup(__dadd_rn(a,b));}
__device__ double qm(double a,double b){return a==0||b==0?0:qup(__dmul_rn(a,b));}
__device__ double qd(double a,double b){return a==0?0:qup(__ddiv_rn(a,b));}
__device__ double qgamma(unsigned int n,bool low){double u=low?0x1p-24:0x1p-53,nu=(double)n*u;return nu>=1?INFINITY:qup(__ddiv_rn(nu,__dadd_rn(1.,-nu)));}
__device__ double qcast(double x){float f=__double2float_rn(x);return !isfinite(f)?INFINITY:x==(double)f?0:qup(fabs(__dadd_rn(x,-(double)f)));}
__device__ float qdecode(const unsigned char* codes,unsigned int id,unsigned int format,int scale){
 unsigned int c=format==0?((const unsigned short*)codes)[id]:codes[id];
 unsigned int mb=format==0?10:format==1?3:2, eb=format==1?4:5;int bias=format==1?7:15;
 unsigned int mag=c&((1u<<(mb+eb))-1),e=mag>>mb,m=mag&((1u<<mb)-1);
 float v=e?ldexpf((float)((1u<<mb)+m),(int)e-bias-(int)mb+scale):ldexpf((float)m,1-bias-(int)mb+scale);
 return c&(1u<<(mb+eb))?-v:v;
}
extern "C" __global__ void qr_begin(const double*x,const double*y,double*px,double*py,
 unsigned int*control,unsigned int n,unsigned int m,unsigned int final_step){
 unsigned int i=blockIdx.x*blockDim.x+threadIdx.x;
 if(control[0])return;
 if(i==0)control[1]++;
 if(final_step){if(i<n)px[i]=x[i];if(i<m)py[i]=y[i];}
}
// One vector reduction per product; no atomics or cached vector-dependent bounds.
extern "C" __global__ void qr_norm(const double*v,double*norm,unsigned int*control,
 unsigned int n,unsigned int native){
 __shared__ double maxima[256],conversions[256];__shared__ unsigned int active;
 unsigned int l=threadIdx.x;if(l==0)active=control[0]==0;__syncthreads();
 if(!active){if(l==0)norm[2]=0;return;}
 double a=0,d=0;for(unsigned int i=l;i<n;i+=256){a=fmax(a,fabs(v[i]));if(!native)d=fmax(d,qcast(v[i]));if(!isfinite(v[i]))a=INFINITY;}
 maxima[l]=a;conversions[l]=d;__syncthreads();
 for(unsigned int k=128;k;k>>=1){if(l<k){maxima[l]=fmax(maxima[l],maxima[l+k]);conversions[l]=fmax(conversions[l],conversions[l+k]);}__syncthreads();}
 if(l==0){norm[0]=maxima[0];norm[1]=conversions[0];norm[2]=isfinite(maxima[0])?1:0;if(!isfinite(maxima[0]))atomicOr(control,2u);}
}
// One thread owns an output. Many tiny tile segments share a warp. Per-tile
// products/adds are FP32; inter-tile adds are FP64, all with a frozen serial tree.
extern "C" __global__ void qr_product(const double*original,const unsigned char*codes,
 const double*low_error,const double*native_error,const unsigned int*line,
 const unsigned int*group,const unsigned int*tiles,const unsigned int*ids,
 const unsigned int*inputs,const int*exponents,const unsigned int*promoted,
 const double*constants,double*bounds,const double*scales,const double*v,double*out,
 const double*norm,unsigned int*control,unsigned int*flags,unsigned long long*stats,
 unsigned int count,unsigned int start,unsigned int format,unsigned int bridge,
 unsigned int guard_only){
 unsigned int i=blockIdx.x*blockDim.x+threadIdx.x;if(i>=count||norm[2]==0)return;
 unsigned int row=start+i,first=line[row],last=line[row+1];
 bool unchecked=guard_only==2;double coarse=unchecked?0:qa(qd(qa(qa(qm(constants[3*row],norm[0]),qm(constants[3*row+1],norm[1])),constants[3*row+2]),scales[row]),0x0.0000000000001p-1022);
 bool detailed=!unchecked&&!(coarse<=1.e-7);double total=0,bound=0,mass=0;unsigned int flag=0,terms=0;
 unsigned long long low_count=0,high_count=0,nonzero=0;
 for(unsigned int g=first;g<last;++g){unsigned int tile=tiles[g];bool low=!promoted[tile];double sum=0,b=0,ab=0;
  unsigned int begin=group[g],end=group[g+1];terms+=end-begin;
  for(unsigned int p=begin;p<end;++p){unsigned int id=ids[p];double x=v[inputs[p]],a=low?(double)qdecode(codes,id,format,exponents[tile]):original[id];
   double vx=low?(double)__double2float_rn(x):x;double product=low?(double)__fmul_rn((float)a,(float)vx):__dmul_rn(a,vx);
   if(low){++low_count;if(x!=0)++nonzero;}else ++high_count;
   if(!unchecked&&(!isfinite(vx)||(x!=0&&vx==0)||!isfinite(product)||(a!=0&&vx!=0&&product==0)))flag|=low?4u:2u;
   sum=low?(double)__fadd_rn((float)sum,(float)product):__dadd_rn(sum,product);
   if(!unchecked&&!isfinite(sum))flag|=low?4u:2u;
   if(detailed){b=qa(b,qm(low?low_error[id]:native_error[id],fabs(x)));if(low)b=qa(b,qm(fabs(a),qcast(x)));ab=qa(ab,qm(fabs(a),fabs(vx)));}
  }
  total=__dadd_rn(total,sum);
  if(detailed){b=qa(b,qm(qgamma(end-begin+1,low),ab));b=qa(b,(double)(end-begin+1)*(low?0x1p-149:0x0.0000000000001p-1022));bound=qa(bound,b);mass=qa(mass,ab);}
 }
 double result=detailed?qa(qd(qa(qa(bound,qm(qgamma(bridge?terms+8:last-first+2,false),qa(mass,bound))),__longlong_as_double((long long)(last-first+1))),scales[row]),0x0.0000000000001p-1022):coarse;
 if(!(result<=1.e-7))flag|=1;
 if(!unchecked&&!isfinite(total)&&!(flag&4))flag|=2;
 flags[row]=flag;bounds[row]=result;
 if(flag){atomicOr(control,flag);atomicCAS(control+2,0u,start?1u:2u);}
 if(guard_only!=1)out[i]=total;
 unsigned long long*s=stats+7*row;s[0]+=low_count;s[1]+=high_count*(bridge?2:1);s[2]+=nonzero;if(guard_only==1)s[6]+=low_count+high_count;
 if(!unchecked){if(detailed){if(result<=1.e-7)s[4]++;else s[5]++;}else s[3]++;}
}
__device__ bool qbadmul(double a,double b,double p){return !isfinite(p)||(a!=0&&b!=0&&p==0);}
extern "C" __global__ void qr_primal(double*x,const double*aty,const double*objective,
 const double*lo,const double*hi,const double*anchor,double*bar,const double*norm,
 unsigned int*control,const unsigned int*flags,unsigned int start,unsigned int n,
 double step,double toward,double back){
 unsigned int i=blockIdx.x*blockDim.x+threadIdx.x;if(i>=n||norm[2]==0||flags[start+i])return;
 double old=x[i],diff=__dadd_rn(objective[i],-aty[i]),move=__dmul_rn(step,diff),raw=__dadd_rn(old,-move);
 double next=fmin(fmax(raw,lo[i]),hi[i]);double extrapolated=__dadd_rn(__dmul_rn(2.,next),-old);
 double a=__dmul_rn(toward,next),b=__dmul_rn(back,anchor[i]),value=__dadd_rn(a,b);
 if(!isfinite(diff)||qbadmul(step,diff,move)||!isfinite(raw)||!isfinite(extrapolated)||qbadmul(toward,next,a)||qbadmul(back,anchor[i],b)||!isfinite(value)){atomicOr(control,2u);atomicCAS(control+2,0u,3u);return;}
 bar[i]=extrapolated;x[i]=value;
}
extern "C" __global__ void qr_dual(double*y,const double*ax,const double*lo,const double*hi,
 const double*anchor,const double*norm,unsigned int*control,const unsigned int*flags,
 unsigned int n,double step,double toward,double back){
 unsigned int i=blockIdx.x*blockDim.x+threadIdx.x;if(i>=n||norm[2]==0||flags[i])return;
 double move=__dmul_rn(step,ax[i]),raw=__dadd_rn(y[i],-move),scaled=__ddiv_rn(raw,step);
 double projected=fmin(fmax(scaled,-hi[i]),-lo[i]);double p=__dmul_rn(step,projected),next=__dadd_rn(raw,-p);
 double a=__dmul_rn(toward,next),b=__dmul_rn(back,anchor[i]),value=__dadd_rn(a,b);
 if(qbadmul(step,ax[i],move)||!isfinite(raw)||!isfinite(scaled)||qbadmul(step,projected,p)||!isfinite(next)||qbadmul(toward,next,a)||qbadmul(back,anchor[i],b)||!isfinite(value)){atomicOr(control,2u);atomicCAS(control+2,0u,3u);return;}
 y[i]=value;
}
extern "C" __global__ void qr_collect(const unsigned long long*stats,const unsigned int*control,
 unsigned long long*out,unsigned int rows,unsigned int columns){
 __shared__ unsigned long long partial[8][256];unsigned int l=threadIdx.x;
 for(unsigned int j=0;j<8;++j)partial[j][l]=0;
 for(unsigned int i=l;i<rows+columns;i+=256){const unsigned long long*s=stats+7*i;partial[0][l]+=s[0];partial[1][l]+=s[1];partial[i<rows?3:2][l]+=s[2];partial[4][l]+=s[3];partial[5][l]+=s[4];partial[6][l]+=s[5];partial[7][l]+=s[6];}
 __syncthreads();for(unsigned int k=128;k;k>>=1){if(l<k)for(unsigned int j=0;j<8;++j)partial[j][l]+=partial[j][l+k];__syncthreads();}
 if(l==0){for(unsigned int j=0;j<7;++j)out[j]=partial[j][0];out[7]=control[1];out[8]=control[0];out[9]=control[2];out[10]=partial[7][0];}
}

extern "C" __global__ void qr_tuned_spmv(const double*values,const unsigned int*indices,const unsigned int*offsets,const double*x,double*out,unsigned int count,const double*norm){
 unsigned int line=(blockIdx.x*blockDim.x+threadIdx.x)/32;if(line>=count||norm[2]==0)return;
 double total=warp_dot(values,indices,offsets,x,line);if((threadIdx.x&31)==0)out[line]=total;
}

extern "C" __global__ void qr_reset(unsigned long long*stats,unsigned int*flags,unsigned int*control,unsigned int lines){unsigned int i=blockIdx.x*blockDim.x+threadIdx.x;if(i<7*lines)stats[i]=0;if(i<lines)flags[i]=0;if(i<4)control[i]=0;}

extern "C" __global__ void qr_clear(unsigned int*control){if(threadIdx.x<4)control[threadIdx.x]=0;}
