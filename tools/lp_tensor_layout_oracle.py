"""Prove production fragment loaders cover each required operand address once."""
import subprocess,tempfile
from pathlib import Path
from lp_protocol import ROOT,file_hash

def verify():
 header=ROOT/'cuda/lp_pdhg_tensor/fragment_layout.h'
 program='#include "'+str(header)+'"\n'+r'''
#include <cassert>
int main(){for(int mode=0;mode<3;mode++)for(unsigned half=0;half<2;half++){
 int a[32][32]={},b[32][8]={};int width=mode==0?4:2,chunks=mode==0?1:2;
 for(unsigned lane=0;lane<32;lane++)for(int chunk=0;chunk<chunks;chunk++){
  for(int reg=0;reg<4;reg++)for(int k=0;k<width;k++){
   unsigned r=tensor_a_row(half,lane/4,reg),c=tensor_a_col(lane%4,mode,reg,chunk,k);
   assert(r<32&&c<32);a[r][c]++;
  }
  for(int reg=0;reg<2;reg++)for(int k=0;k<width;k++){
   unsigned r=tensor_b_row(lane%4,mode,reg,chunk,k),c=lane/4;
   assert(r<32&&c<8);b[r][c]++;
  }
 }
 for(unsigned r=0;r<32;r++)for(unsigned c=0;c<32;c++)assert(a[r][c]==(r>=half*16&&r<half*16+16?1:0));
 for(unsigned r=0;r<32;r++)for(unsigned c=0;c<8;c++)assert(b[r][c]==1);
}}
'''
 with tempfile.TemporaryDirectory() as directory:
  source=Path(directory)/'layout.cpp';binary=Path(directory)/'layout';source.write_text(program)
  subprocess.run(['g++','-std=c++17','-O2',str(source),'-o',str(binary)],check=True,capture_output=True,text=True,timeout=30)
  subprocess.run([str(binary)],check=True,timeout=10)
 return dict(status='passed',gpu_seconds=0,header_sha256=file_hash(header),matrix_addresses=3072,vector_addresses=1536)
if __name__=='__main__':print(verify())
