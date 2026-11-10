// ADR-0042 lane addresses shared by production MMA packing and CPU coverage proof.
#pragma once
#ifdef __CUDACC__
#define TENSOR_HD __host__ __device__
#else
#define TENSOR_HD
#endif
TENSOR_HD inline unsigned tensor_a_row(unsigned half,unsigned group,int reg){return half*16+group+(reg%2)*8;}
TENSOR_HD inline unsigned tensor_a_col(unsigned thread,int mode,int reg,int chunk,int element){return thread*(mode==0?4:2)+(reg/2)*(mode==0?16:8)+chunk*16+element;}
TENSOR_HD inline unsigned tensor_b_row(unsigned thread,int mode,int reg,int chunk,int element){return thread*(mode==0?4:2)+reg*(mode==0?16:8)+chunk*16+element;}
#undef TENSOR_HD
