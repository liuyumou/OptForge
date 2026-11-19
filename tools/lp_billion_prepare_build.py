"""Retained CPU-only builds of the separate GPU preparation module."""
import argparse
import re
import subprocess
from lp_billion_common import BASE,ROOT,put,ref,require,digest


def build(identity,quality=False):
    out=BASE/identity;out.mkdir(exist_ok=False)
    manifest='research/lp-billion-lowbit/Cargo.toml'
    rows=[]
    def run(name,command):
        p=subprocess.run(command,text=True,capture_output=True)
        (out/(name+'.stdout')).write_text(p.stdout);(out/(name+'.stderr')).write_text(p.stderr)
        rows.append(dict(name=name,command=command,returncode=p.returncode,stdout=ref(out/(name+'.stdout')),stderr=ref(out/(name+'.stderr'))))
        if p.returncode:
            print(p.stdout[-5000:]+p.stderr[-5000:],flush=True)
        require(p.returncode==0,'preparation build '+name)
        print(dict(command=name,status='passed'),flush=True)
        return p.stdout
    run('format',['cargo','fmt','--manifest-path',manifest,'--check'])
    if quality:
        text=run('tests',['cargo','test','--manifest-path',manifest,'--release','--offline'])
        counts=[tuple(map(int,m)) for m in re.findall(r'test result: ok\. (\d+) passed; (\d+) failed; (\d+) ignored;',text)]
        require(counts and all(f==i==0 for _,f,i in counts),'complete isolated tests')
        rust_tests=sum(c for c,_,_ in counts)
        run('clippy',['cargo','clippy','--manifest-path',manifest,'--all-targets','--offline','--','-D','warnings'])
        run('release',['cargo','build','--manifest-path',manifest,'--release','--bins','--offline'])
    else:
        run('check',['cargo','check','--manifest-path',manifest,'--all-targets','--offline'])
        rust_tests=None
    command=['/usr/local/cuda/bin/nvcc','-std=c++17','-O3','-lineinfo','-fmad=false','-ftz=false','-arch=sm_120a','--ptxas-options=-v','--cubin',
        'research/lp-billion-lowbit/cuda/prepare.cu','-o',str(out/'prepare.cubin')]
    run('cuda',command)
    original=ROOT/'crates/optimizer-lp/src/pdhg.rs';candidate=ROOT/'research/lp-billion-lowbit/src/host-lp/pdhg.rs'
    text=candidate.read_text();start=text.index('    /// Consume an admitted proposal preparation')
    end=text.index('    /// Build the scaled working problem.',start)
    require(text[:start]+text[end:]==original.read_text(),'all pre-existing host engine source remains exact')
    put(out/'result.json',dict(status='passed',quality=quality,rust_tests=rust_tests,commands=rows,cuda=ref(out/'prepare.cubin'),
        cuda_source=ref(ROOT/'research/lp-billion-lowbit/cuda/prepare.cu'),original_engine=ref(original),extended_engine=ref(candidate),
        original_engine_preserved=True,rustc=subprocess.check_output(['rustc','-vV'],text=True),
        nvcc=subprocess.check_output(['/usr/local/cuda/bin/nvcc','--version'],text=True)))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--id',required=True);p.add_argument('--quality',action='store_true');a=p.parse_args()
    build(a.id,a.quality)
