// Canonical proposal packing only. Original-model certification remains on CPU.
#include <cuda_runtime.h>
#include <stdint.h>
#include <math.h>
using U = unsigned;
static constexpr U EMPTY = 0xffffffffu;
static constexpr U HASH = 4096;
__device__ U lower(const U* a, U lo, U hi, U x) {
    while (lo < hi) { U mid = lo + (hi-lo)/2; if (a[mid] < x) lo=mid+1; else hi=mid; }
    return lo;
}
extern "C" __global__ void pack_validate(const U* off, const U* idx,
 const double* val, U lines, U other, U* bad) {
    U row=blockIdx.x*blockDim.x+threadIdx.x;
    if(row>=lines) return;
    U lo=off[row], hi=off[row+1];
    for(U j=lo;j<hi;++j) if(idx[j]>=other || (j>lo && idx[j-1]>=idx[j]) ||
       !isfinite(val[j]) || fabs(val[j])>0x1p40) atomicOr(bad,1u);
}
extern "C" __global__ void pack_transpose(const U* ro, const U* ri, const double* rv,
 const U* co, const U* ci, const double* cv, U m, U* bad) {
    U row=blockIdx.x*blockDim.x+threadIdx.x;
    if(row>=m) return;
    for(U j=ro[row];j<ro[row+1];++j) {
        U c=ri[j], at=lower(ci,co[c],co[c+1],row);
        if(at==co[c+1] || ci[at]!=row || __double_as_longlong(cv[at])!=__double_as_longlong(rv[j])) atomicOr(bad,2u);
    }
}
// Integer atomics count structure only; no floating-point reduction is reordered.
// Overflow requests the exact host path rather than dropping an eligible tile.
extern "C" __global__ void pack_eligible(const U* off, const U* idx, U m,
 U minimum, U* counts, const U* prefix, U* keys, U emit, U* overflow) {
    __shared__ U table[HASH], hits[HASH], total;
    U t=threadIdx.x, group=blockIdx.x;
    for(U j=t;j<HASH;j+=blockDim.x) { table[j]=EMPTY; hits[j]=0; }
    if(t==0) total=0;
    __syncthreads();
    U first=group*32, end=min(first+32,m);
    for(U j=off[first]+t;j<off[end];j+=blockDim.x) {
        U key=idx[j]/32, slot=(key*2654435761u)&(HASH-1), tries=0;
        for(;tries<HASH;++tries) {
            U old=atomicCAS(table+slot,EMPTY,key);
            if(old==EMPTY || old==key) { atomicAdd(hits+slot,1u); break; }
            slot=(slot+1)&(HASH-1);
        }
        if(tries==HASH) atomicOr(overflow,1u);
    }
    __syncthreads();
    for(U j=t;j<HASH;j+=blockDim.x) if(hits[j]>=minimum) {
        U at=atomicAdd(&total,1u);
        if(emit) keys[prefix[group]+at]=table[j];
    }
    __syncthreads();
    if(t==0) counts[group]=total;
}
__device__ bool covered(const U* offsets,const U* columns,U row,U col) {
    U line=row/16, hi=offsets[line+1];
    U at=lower(columns,offsets[line],hi,col/32);
    return at<hi && columns[at]==col/32;
}
extern "C" __global__ void pack_coverage(const U* off,const U* idx,
 const U* to,const U* tc,U* cov,U n) {
    U row=blockIdx.x*blockDim.x+threadIdx.x;
    if(row>=n) return;
    U count=0;
    for(U j=off[row];j<off[row+1];++j) count+=covered(to,tc,row,idx[j]);
    cov[row]=count;
}
extern "C" __global__ void pack_residual(const U* off,const U* idx,const double* val,
 const U* to,const U* tc,const U* dstoff,U* dstidx,double* dstval,U n) {
    U row=blockIdx.x*blockDim.x+threadIdx.x;
    if(row>=n) return;
    U at=dstoff[row];
    for(U j=off[row];j<off[row+1];++j) if(!covered(to,tc,row,idx[j])) {
        dstidx[at]=idx[j]; dstval[at]=val[j]; ++at;
    }
}
__device__ U code(double v) {
    double x=fabs(v);
    U mag=2*(x>0.5)+(x>1.25)+(x>=1.75)+(x>2.5)+(x>=3.5)+(x>5.0);
    return mag | ((v<0 && mag!=0)?8:0);
}
__device__ double decoded(U c) {
    U mag=c&7;
    unsigned long long bits=mag==0?0ull:
      ((unsigned long long)(1022+(mag>>1))<<52) | ((unsigned long long)(mag&1)<<51) | ((unsigned long long)(c&8)<<60);
    return __longlong_as_double(bits);
}
// One CTA gathers/encodes each canonical tile once and writes both orientations.
extern "C" __global__ void pack_encode(const U* off,const U* idx,const double* val,
 const U* geometry,U m,U k,U compact,U* rf,int* re,U* cf,int* ce) {
    __shared__ double values[1024], maxima[256];
    __shared__ U codes[1024];
    __shared__ int exponent;
    U t=threadIdx.x, tile=blockIdx.x;
    const U* g=geometry+6ull*tile;
    for(U q=t;q<1024;q+=256) {
        U row=g[0]*32+q/32,col=g[1]*32+q%32;
        double v=0;
        if(row<m) { U at=lower(idx,off[row],off[row+1],col); if(at<off[row+1] && idx[at]==col) v=val[at]; }
        values[q]=v;
    }
    __syncthreads();
    for(U h=0;h<k;++h) {
        double mx=0;
        for(U q=t;q<1024;q+=256) mx=fmax(mx,fabs(values[q]));
        maxima[t]=mx;
        __syncthreads();
        for(U stride=128;stride;stride/=2) {
            if(t<stride) maxima[t]=fmax(maxima[t],maxima[t+stride]);
            __syncthreads();
        }
        if(t==0) {
            double mx=maxima[0];
            int e=mx==0?-48:max(ilogb(mx)-2,-48);
            if(mx>6.0*ldexp(1.0,e)) ++e;
            exponent=e;
        }
        __syncthreads();
        double scale=ldexp(1.0,exponent),inverse=ldexp(1.0,-exponent);
        for(U q=t;q<1024;q+=256) {
            U c=code(__dmul_rn(values[q],inverse)); codes[q]=c;
            values[q]=__dsub_rn(values[q],__dmul_rn(decoded(c),scale));
        }
        __syncthreads();
        // Four warps: row half 0/1, transpose half 0/1.
        if(t<128) {
            U orientation=t/64,half=(t/32)%2,lane=t%32,slot=g[2+orientation*2+half];
            if(slot!=EMPTY) {
                U* fragments=orientation?cf:rf; int* exponents=orientation?ce:re;
                U words=compact?64:128;
                if(lane==0) exponents[(size_t)slot*k+h]=exponent;
                U packed[2]={0,0};
                for(U reg=0;reg<4;++reg) {
                    U row=half*16+lane/4+(reg%2)*8, col=(lane%4)*4+(reg/2)*16, word=0;
                    for(U z=0;z<4;++z) {
                        U c=codes[orientation?(col+z)*32+row:row*32+col+z];
                        word|=c<<(2+z*8); packed[reg/2]|=c<<(16*(reg%2)+4*z);
                    }
                    if(!compact) fragments[((size_t)slot*k+h)*words+lane*4+reg]=word;
                }
                if(compact) for(U j=0;j<2;++j) fragments[((size_t)slot*k+h)*words+lane*2+j]=packed[j];
            }
        }
        __syncthreads();
    }
}
