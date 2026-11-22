"""Source-retained CPU quality and separate CUDA packing build."""
import argparse,re,subprocess,shutil
from pathlib import Path
from lp_billion_common import BASE,ROOT,put,ref,require,resolve,load

def build(identity):
    out=BASE/identity;out.mkdir(exist_ok=False);rows=[]
    manifest='research/lp-billion-lowbit/Cargo.toml'
    def command(name,cmd):
        p=subprocess.run(cmd,text=True,capture_output=True)
        (out/(name+'.stdout')).write_text(p.stdout);(out/(name+'.stderr')).write_text(p.stderr)
        rows.append(dict(name=name,command=cmd,returncode=p.returncode,stdout=ref(out/(name+'.stdout')),stderr=ref(out/(name+'.stderr'))))
        if p.returncode:print(p.stdout[-4000:]+p.stderr[-4000:],flush=True)
        require(p.returncode==0,'GPU packing quality '+name);print(dict(command=name,status='passed'),flush=True)
        return p.stdout
    command('format',['cargo','fmt','--manifest-path',manifest,'--check'])
    text=command('tests',['cargo','test','--manifest-path',manifest,'--release','--offline'])
    counts=[tuple(map(int,m)) for m in re.findall(r'test result: ok\. (\d+) passed; (\d+) failed; (\d+) ignored;',text)]
    require(counts and all(f==i==0 for _,f,i in counts),'complete isolated tests')
    command('clippy',['cargo','clippy','--manifest-path',manifest,'--all-targets','--offline','--','-D','warnings'])
    command('release',['cargo','build','--manifest-path',manifest,'--release','--bins','--offline'])
    command('cuda',['/usr/local/cuda/bin/nvcc','-std=c++17','-O3','-lineinfo','-fmad=false','-ftz=false','-arch=sm_120a','--ptxas-options=-v','--cubin','research/lp-billion-lowbit/cuda/pack.cu','-o',str(out/'pack.cubin')])
    for item in load(BASE/'sources'/identity/'manifest.json')['sources']:
        if item['original']['path'].endswith(('.rs','.cu')) or Path(item['original']['path']).name.startswith('Cargo.'):
            resolve(item['original']);resolve(item['retained'])
    put(out/'result.json',dict(status='passed',rust_tests=sum(c for c,_,_ in counts),commands=rows,cuda=ref(out/'pack.cubin'),cuda_source=ref(ROOT/'research/lp-billion-lowbit/cuda/pack.cu')))

def seal(identity):
    built=load(BASE/identity/'result.json')
    require(built['status']=='passed','packing quality passed')
    for item in load(BASE/'sources'/identity/'manifest.json')['sources']:
        if item['original']['path'].endswith(('.rs','.cu')) or item['original']['path'].split('/')[-1].startswith('Cargo.'):
            resolve(item['original']);resolve(item['retained'])
    image=BASE/'image-v10';image.mkdir(exist_ok=False)
    for source,name in [(BASE/'target/release/billion','executor'),(BASE/'target/release/packing_check','packing-check'),(BASE/'image-v9/tensor.cubin','tensor.cubin'),(BASE/'image-v9/prepare.cubin','prepare.cubin'),(resolve(built['cuda']),'pack.cubin')]:
        shutil.copyfile(source,image/name);(image/name).chmod(0o755 if name in ['executor','packing-check'] else 0o644)
    put(image/'binding.json',dict(status='CPU_quality_only',executor=ref(image/'executor'),cuda=ref(image/'tensor.cubin'),preparation=ref(image/'prepare.cubin'),packing=ref(image/'pack.cubin'),files={p.name:ref(p) for p in image.iterdir()},quality=ref(BASE/identity/'result.json'),source_manifest=ref(BASE/'sources'/identity/'manifest.json'),previous_image=ref(BASE/'image-v9/binding.json')))
    print(dict(status='sealed',image=str(image)),flush=True)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['build','seal']);p.add_argument('--id',required=True);a=p.parse_args();globals()[a.action](a.id)
