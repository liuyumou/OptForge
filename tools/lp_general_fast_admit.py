"""Source-bound admission for the isolated fast-proposal executor."""
import argparse
from lp_general_common import BASE,ROOT,load,put,ref,require


def admit(identity,image,cpu,generation,native,boundary=''):
    binary=BASE/image/'executor';cubin=BASE/image/'tensor.cubin';proofs={};resources={}
    for name in [cpu,cpu+'-oracle',f'fast-gpu-v{generation}']+[f'fast-{s}-v{generation}' for s in ['memcheck','racecheck','initcheck','synccheck']]+([n for n in boundary.split(',') if n]):
        p=BASE/name/'result.json';r=load(p);require(r['status']=='passed','missing proof '+name)
        require(r['binary']['sha256']==ref(binary)['sha256'],'admitted binary differs '+name)
        if r.get('image'):require(r['image']==ref(cubin),'admitted image differs '+name)
        resource=BASE/'resources'/((cpu if name==cpu+'-oracle' else name)+'.settlement.json')
        require(load(resource)['status']=='passed','proof has no complete resources '+name)
        proofs[name]=ref(p);resources[name]=ref(resource)
    native_path=BASE/'resources'/(native+'.settlement.json');require(load(native_path)['status']=='passed','native gate missing')
    # Root numerical libraries remain exactly those admitted by the full gate.
    native_sources=BASE/'sources'/native
    for p in sorted((ROOT/'crates').rglob('*.rs')):
        require(p.read_bytes()==(native_sources/p.relative_to(ROOT)).read_bytes(),'root source changed after native gate')
    retained=[];dest=BASE/(identity+'-sources');dest.mkdir(exist_ok=False)
    for p in sorted((ROOT/'research/lp-general-lowbit/src').glob('*.rs'))+sorted((ROOT/'research/lp-general-lowbit/cuda').glob('*')):
        require(p.read_bytes()==(BASE/'sources'/cpu/p.relative_to(ROOT)).read_bytes(),'numerical image/source mismatch')
        q=dest/p.relative_to(ROOT);q.parent.mkdir(parents=True,exist_ok=True);q.write_bytes(p.read_bytes());retained.append(ref(q))
    sass=(BASE/image/'tensor.sass').read_text()
    for k in range(1,5):
        section=sass.split('Function : fast_product_'+str(k)+'\n')[1].split('Function :')[0]
        require('QMMA.16832.F32.E2M1.E2M1' in section,'fast product does not use FP4 MMA')
        if 'Function : fast_combined_'+str(k)+'\n' in sass:
            section=sass.split('Function : fast_combined_'+str(k)+'\n')[1].split('Function :')[0]
            require('QMMA.16832.F32.E2M1.E2M1' in section,'combined product does not use FP4 MMA')
    put(BASE/(identity+'.json'),dict(kind='fast-proposal-admission',status='passed',binary=ref(binary),image=ref(cubin),
        proofs=proofs,resources=resources,native=ref(native_path),sources=retained,
        operational=ref(BASE/'operational-readmission-v1.json'),claim='Admitted search proposals and original-model certification; no product-enclosure or performance claim.'))
    print('source-bound fast-proposal admission passed',flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--id',required=True);p.add_argument('--image',required=True);p.add_argument('--cpu',required=True);p.add_argument('--generation',type=int,required=True);p.add_argument('--native',required=True);p.add_argument('--boundary',default='');a=p.parse_args();admit(a.id,a.image,a.cpu,a.generation,a.native,a.boundary)
