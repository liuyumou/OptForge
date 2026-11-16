"""Compose source-bound admission without opening or changing older allocations."""
import argparse
import os
import platform
import subprocess
from pathlib import Path
from lp_general_common import ROOT,BASE,DEVICE,load,put,ref,require
from lp_general_device import BINARY

def run(image,identity='device-admission-v1',generation=2):
    binary=ref(BINARY);image_ref=ref(image)
    proofs={}
    names=['oracle-v5','cpu-models-v2','gpu-oracle-v2','device-v2','longrows-cpu-v2','longrows-gpu-v2'] if generation==2 else ['oracle-v6','cpu-models-v3',f'gpu-oracle-v{generation}',f'device-v{generation}','longrows-cpu-v3',f'longrows-gpu-v{generation}','implied-admission-v1']
    if generation==5:names=['oracle-v7','cpu-models-v4','gpu-oracle-v5','device-v5','longrows-cpu-v4','longrows-gpu-v5','implied-admission-v2']
    for name in names:
        p=BASE/name/'result.json';r=load(p);require(r['status']=='passed','missing admission '+name)
        require(r['binary']==binary,'admission executable differs '+name)
        if r.get('image'):require(r['image']==image_ref,'admission image differs '+name)
        proofs[name]=ref(p)
    sanitizers={}
    for name in ['memcheck','racecheck','initcheck','synccheck']:
        entries=[]
        for suite in ['sanitizer-'+name+f'-v{generation}','longrows-'+name+f'-v{generation}']:
            p=BASE/suite/'result.json';r=load(p)
            require(r['status']=='passed' and r['binary']==binary and r['image']==image_ref and r['sanitizer']==name,'sanitizer admission differs')
            entries.append(ref(p))
        sanitizers[name]=entries
    resources={}
    for name in ['native-v2',{2:'cpu-contracts-v11',3:'cpu-contracts-v12',4:'cpu-contracts-v12',5:'cpu-contracts-v14'}[generation]]:
        p=BASE/'resources'/(name+'.settlement.json');r=load(p)
        require(r['status']=='passed' and not r['overrun'],'native/CPU admission missing');resources[name]=ref(p)
    inventory=dict(gpu=subprocess.check_output(['nvidia-smi','-i',DEVICE,'--query-gpu=uuid,name,driver_version,memory.total,compute_mode,pci.bus_id','--format=csv'],text=True),
        compiler=subprocess.check_output(['/usr/local/cuda/bin/nvcc','--version'],text=True),host=platform.platform(),
        rust_flags={k:os.environ.get(k,'') for k in ['RUSTFLAGS','CARGO_ENCODED_RUSTFLAGS','CARGO_BUILD_TARGET','CARGO_TARGET_X86_64_UNKNOWN_LINUX_GNU_RUSTFLAGS']},
        toolchain=ref(ROOT/'rust-toolchain.toml'),cargo=ref(ROOT/'research/lp-general-lowbit/Cargo.toml'),lock=ref(ROOT/'research/lp-general-lowbit/Cargo.lock'),
        cuda_source=ref(ROOT/'research/lp-general-lowbit/cuda/lowbit.cu'))
    put(BASE/(identity+'.json'),dict(kind='general-device-admission',status='passed',binary=binary,image=image_ref,
        proofs=proofs,sanitizers=sanitizers,resources=resources,inventory=inventory,claim='numerical/process admission only; no performance or broad-adoption pass'))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--image',required=True,type=Path);p.add_argument('--id',default='device-admission-v1');p.add_argument('--generation',type=int,choices=[2,3,4,5],default=2)
    a=p.parse_args();run(a.image,a.id,a.generation)
