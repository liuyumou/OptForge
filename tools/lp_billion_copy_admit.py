"""Source-bound standalone exercise of the same checked Rust upload boundary."""
import argparse,shutil,subprocess
from pathlib import Path
from lp_billion_common import BASE,ROOT,load,put,ref,resolve,require

BUILD=BASE/'bounded-copy-build-v2'
def build():
    BUILD.mkdir(exist_ok=False)
    image=load(BASE/'image-v9/binding.json')
    old=next(i for i in load(resolve(image['source_manifest']))['sources'] if i['original']['path']=='research/lp-tensor-expanded-device/cuda-sys/src/lib.rs')
    resolve(old['original']);resolve(old['retained'])
    deps=BASE/'target/release/deps';paths=list(deps.glob('liboptimizer_cuda_sys-*.rlib'));require(len(paths)==1,'unambiguous CUDA boundary')
    library=BUILD/'liboptimizer_cuda_sys.rlib';shutil.copyfile(paths[0],library)
    source=ROOT/'research/lp-billion-lowbit/diagnostics/copy.rs';exe=BUILD/'copy'
    compiler=Path('/root/.rustup/toolchains/1.93.1-x86_64-unknown-linux-gnu/bin/rustc')
    cmd=[str(compiler),'--edition','2024','-C','opt-level=3','--extern','optimizer_cuda_sys='+str(library),'-L','dependency='+str(deps),str(source),'-o',str(exe)]
    p=subprocess.run(cmd,text=True,capture_output=True);(BUILD/'build.stdout').write_text(p.stdout);(BUILD/'build.stderr').write_text(p.stderr);require(p.returncode==0,'copy diagnostic build '+p.stderr)
    put(BUILD/'result.json',dict(status='passed',source=ref(source),executable=ref(exe),library=ref(library),boundary=old['original'],compiler_sha256=__import__('hashlib').sha256(compiler.read_bytes()).hexdigest()))
def run():
    b=load(BUILD/'result.json');out=BASE/'bounded-copy-gpu-v1';out.mkdir(exist_ok=False)
    p=subprocess.run([str(resolve(b['executable']))],text=True,capture_output=True);(out/'stdout').write_text(p.stdout);(out/'stderr').write_text(p.stderr)
    require(p.returncode==0,'GPU offset-copy diagnostic '+p.stderr)
    import json
    r=json.loads(p.stdout);require(r['bitwise_exact'] and r['chunk_copies']==3 and r['partial_tail_elements']==17,'multi-chunk exact GPU copy')
    put(out/'result.json',dict(status='passed',build=ref(BUILD/'result.json'),result=r))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['build','run']);a=p.parse_args();globals()[a.action]()
