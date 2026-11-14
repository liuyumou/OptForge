"""Original-model CPU differential admission; no device access."""
import hashlib
import json
import os
import subprocess
from pathlib import Path
from lp_checker2_common import BASE, ROOT, PRIOR, load, put, ref, require
from lp_checker2_study import CANDIDATE, BASELINE_BINARY, MODELS
from lp_delivery2_study import bits

def inspect_digest(binary,model):
    with subprocess.Popen([str(binary),'inspect',str(model)],stdout=subprocess.PIPE,stderr=subprocess.PIPE,
                          env=os.environ|{'CUDA_VISIBLE_DEVICES':''}) as p:
        h=hashlib.sha256();count=0
        while chunk:=p.stdout.read(1<<20):h.update(chunk);count+=len(chunk)
        error=p.stderr.read();require(p.wait(timeout=120)==0,'inspect failed '+error.decode())
    return dict(sha256=h.hexdigest(),bytes=count)

def run():
    out=BASE/'cpu-optimized';out.mkdir(exist_ok=False)
    old=(ROOT/'research/lp-mixed2-reuse/src/main.rs').read_text()
    new=(ROOT/'research/lp-mixed2-checker2/src/main.rs').read_text()
    require(old[old.index('    fn solve('):old.index('    fn command(')]==new[new.index('    fn solve('):new.index('    fn command(')],'numerical solve body changed')
    for name in ['device.rs','policy.rs','config.rs','identity.rs']:
        require((ROOT/'research/lp-mixed2-reuse/src'/name).read_bytes()==(ROOT/'research/lp-mixed2-checker2/src'/name).read_bytes(),'unchanged module '+name)
    models=load(MODELS);rows=[]
    for group,items in models['groups'].items():
        for item in items:
            path=ROOT/item['path'];a=inspect_digest(BASELINE_BINARY,path);b=inspect_digest(CANDIDATE,path)
            require(a==b,'prepared representation differs '+item['path']);rows.append(dict(model=item,inspection=a))
            print(dict(preparation=path.name,status='exact'),flush=True)
    put(out/'preparation.json',dict(status='passed',cases=rows,binaries=[ref(BASELINE_BINARY),ref(CANDIDATE)]))
    import lp_mixed2_fp4_cpu as cpu
    cpu.BINARY=CANDIDATE
    cpu.run(out/'original-cpu')
    put(out/'result.json',dict(status='passed',binary=ref(CANDIDATE),preparation=ref(out/'preparation.json'),
                              original_cpu=ref(out/'original-cpu/result.json')))

if __name__=='__main__':run()
