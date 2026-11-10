// FP64 is used only for conservative metadata; no reconstructed iterate feeds
// a product/update. Inputs and output state remain normalized Expansion64.
#include "expanded_compact_helpers.h"
#include "expanded_storage.h"
__device__ double eg_up(double x){return x>=0.&&isfinite(x)?__longlong_as_double(__double_as_longlong(x)+1):__longlong_as_double(0x7ff0000000000000ull);}
__device__ double eg_add(double a,double b){return a==0.?b:b==0.?a:eg_up(__dadd_rn(a,b));}
__device__ double eg_mul(double a,double b){return a==0.||b==0.?0.:eg_up(__dmul_rn(a,b));}
__device__ double eg_div(double a,double b){return a==0.?0.:eg_up(__ddiv_rn(a,b));}
__device__ double eg_abs(ExpandedConst x,U i,U &guard){
 Value v=expanded_load(x,i,guard);if(!v.m)return 0.;
 Value f=rounded<53>(from_words(v.m,0,0),v.e,0,guard);
 W bits=f.m<(1ull<<52)?f.m:((W)(f.e+1075)<<52)|(f.m&0xfffffffffffffull);
 double d=__longlong_as_double(bits+1);if(!isfinite(d))guard|=8u;return d;
}
__device__ double eg_primitive(double magnitude){return eg_add(eg_mul(0x1p-63,magnitude),__longlong_as_double(1));}
extern "C" __global__ void xe_check_flags(const U *flags,U *control,U count){
 U i=blockIdx.x*blockDim.x+threadIdx.x;if(i<count&&flags[i])atomicOr(control,flags[i]);
}
extern "C" __global__ void xe_primal_enclosure(
 ExpandedConst x,ExpandedConst aty,ExpandedConst anchor,ExpandedConst bar,
 const double *objective,const double *product_errors,const double *scales,
 double *xerror,double *bar_error,U *control,U count,U start,
 double step,double toward,double back){
 U i=blockIdx.x*blockDim.x+threadIdx.x;if(i>=count)return;U guard=0;
 double xv=eg_abs(x,i,guard),av=eg_abs(aty,i,guard),anchorv=eg_abs(anchor,i,guard);
 double difference=eg_add(fabs(objective[i]),av);
 double diff_error=eg_add(product_errors[start+i],eg_primitive(difference));
 // The magnitude of a rounded primitive is enclosed by exact magnitude + error.
 double rounded_diff=eg_add(difference,eg_primitive(difference));
 double change=eg_mul(step,rounded_diff);
 double change_error=eg_add(eg_mul(step,diff_error),eg_primitive(change));
 double rounded_change=eg_add(change,eg_primitive(change));
 double raw_error=eg_add(change_error,eg_primitive(eg_add(xv,rounded_change)));
 // 2*projected is exact when the accepted update has not overflowed. From
 // bar=RN64(2*projected-x), use a factor exceeding .5/(1-2^-64).
 double projected=eg_add(eg_mul(0x1.0000000000001p-1,eg_add(eg_abs(bar,i,guard),xv)),__longlong_as_double(1));
 double extrapolated=eg_add(eg_mul(2.,raw_error),eg_mul(2.,eg_primitive(eg_add(eg_mul(2.,projected),xv))));
 double mix=eg_add(eg_mul(toward,raw_error),eg_mul(3.,eg_primitive(eg_add(eg_mul(toward,projected),eg_mul(back,anchorv)))));
 xerror[i]=mix;bar_error[i]=extrapolated;
 if(!isfinite(mix)||!(eg_mul(mix,scales[i])<=1.e-7))guard|=1u;
 if(guard)atomicOr(control,guard);
}

extern "C" __global__ void xe_dual_enclosure(
 ExpandedConst y,ExpandedConst ax,ExpandedConst anchor,ExpandedConst next,
 const double *product_errors,const double *bar_error,const double *values,
 const double *coefficient_error,const U *offsets,const U *indices,
 const double *lower,const double *upper,const double *scales,double *yerror,
 U *control,U count,double step,double toward,double back){
 U i=blockIdx.x*blockDim.x+threadIdx.x;if(i>=count)return;U guard=0;
 double yv=eg_abs(y,i,guard),av=eg_abs(ax,i,guard),anchorv=eg_abs(anchor,i,guard);
 double propagated=0.;
 for(U k=offsets[i];k<offsets[i+1];k++)
  propagated=eg_add(propagated,eg_mul(eg_add(fabs(values[k]),coefficient_error[k]),bar_error[indices[k]]));
 double input_error=eg_add(product_errors[i],propagated);
 double change=eg_mul(step,av),rounded_change=eg_add(change,eg_primitive(change));
 double raw_magnitude=eg_add(yv,rounded_change);
 double raw_error=eg_add(eg_mul(step,input_error),eg_mul(2.,eg_primitive(raw_magnitude)));
 double rounded_raw=eg_add(raw_magnitude,eg_primitive(raw_magnitude));
 // Invert the magnitude enclosure of three normalized Halpern primitives.
 // t>=1/2, b>=0. With u64=2^-64 and eta64=2^-1086,
 // |p| <= ((|next|+(1+u64)*b*|anchor|)+4*eta64)
 //          / (t*(1-u64)^2).
 // The outward factor 1+2^-49 and 8 binary64 min-subnormal units dominate
 // every factor and absolute term, including gradual-underflow cases.
 double numerator=eg_add(eg_add(eg_abs(next,i,guard),eg_mul(back,anchorv)),__longlong_as_double(8));
 double projected=eg_mul(eg_div(0x1.0000000000008p0,toward),numerator);
 double clamp=eg_add(eg_add(rounded_raw,eg_mul(0x1.0000000000008p0,projected)),__longlong_as_double(1));
 double bound_error=0.;
 if(isfinite(lower[i]))bound_error=fmax(bound_error,eg_primitive(eg_mul(step,fabs(lower[i]))));
 if(isfinite(upper[i]))bound_error=fmax(bound_error,eg_primitive(eg_mul(step,fabs(upper[i]))));
 double projection_error=eg_add(eg_add(eg_mul(2.,raw_error),bound_error),eg_primitive(eg_add(rounded_raw,clamp)));
 double mix=eg_add(eg_mul(toward,projection_error),eg_mul(3.,eg_primitive(eg_add(eg_mul(toward,projected),eg_mul(back,anchorv)))));
 yerror[i]=mix;
 if(!isfinite(mix)||!(eg_mul(mix,scales[i])<=1.e-7))guard|=1u;
 if(guard)atomicOr(control,guard);
}

extern "C" __global__ void xe_boundary_enclosure(const double *endpoint,
 const double *errors,const double *scales,U *control,U count){
 U i=blockIdx.x*blockDim.x+threadIdx.x;if(i>=count)return;
 double converted=endpoint[i];
 double conversion=eg_add(eg_mul(0x1p-52,fabs(converted)),__longlong_as_double(1));
 if(!isfinite(converted)||!(eg_mul(eg_add(errors[i],conversion),scales[i])<=1.e-7))atomicOr(control,1u);
}
