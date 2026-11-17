"""Bind actual Tensor Core numerical/operational admission before development."""
import argparse
from lp_general_common import BASE,ROOT,load,put,ref,require
from lp_general_readmit import sources

def run(identity,generation,image,cpu):
    binary=BASE/image/'executor';cubin=BASE/image/'tensor.cubin';proofs={};resources={}
    names=[cpu,f'tensor-gpu-v{generation}']+[f'tensor-{s}-v{generation}' for s in ['memcheck','racecheck','initcheck','synccheck']]
    for name in names:
        path=BASE/name/'result.json';r=load(path);require(r['status']=='passed','admission missing '+name)
        require(r['binary']['sha256']==ref(binary)['sha256'],'binary differs '+name)
        if r.get('image'):require(r['image']==ref(cubin),'image differs '+name)
        rp=BASE/'resources'/(name+'.settlement.json');s=load(rp)
        require(s['status']=='passed' and not s['overrun'],'admission resources refused '+name)
        proofs[name]=ref(path);resources[name]=ref(rp)
    native=BASE/'resources/tensor-native-v1.settlement.json';require(load(native)['status']=='passed','native admission missing')
    require('QMMA.16832.F32.E2M1.E2M1' in (BASE/image/'tensor.sass').read_text(),'actual FP4 MMA absent')
    path=BASE/(identity+'.json');require(not path.exists(),'immutable admission')
    frozen=BASE/(identity+'-sources');frozen.mkdir(exist_ok=False)
    retained=[]
    for source in sorted((ROOT/'research/lp-general-lowbit/src').glob('*.rs'))+sorted((ROOT/'research/lp-general-lowbit/cuda').glob('*')):
        dest=frozen/source.relative_to(ROOT);dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(source.read_bytes());retained.append(ref(dest))
    put(path,dict(kind='general-actual-fp4-tensor-admission',status='passed',binary=ref(binary),image=ref(cubin),proofs=proofs,resources=resources,native=ref(native),
        operational=ref(BASE/'operational-readmission-v1.json'),sources=retained,
        claim='Numerical/process admission only, not a broad performance pass.'))
    print('source-bound Tensor Core admission passed',flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--id',required=True);p.add_argument('--generation',type=int,default=1);p.add_argument('--image',required=True);p.add_argument('--cpu',required=True);a=p.parse_args();run(a.id,a.generation,a.image,a.cpu)
