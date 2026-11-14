"""Explicit timer-removal diagnostic; never changes the confirmation executable."""
import argparse
from pathlib import Path
import random
import shutil
import subprocess
from lp_mixed2_fp4_common import ROOT,BASE,BINARY,load,put,ref,require
import lp_mixed2_fp4_transport as transport
from lp_mixed2_fp4_study import execute_session
from lp_delivery2_study import bits

SOURCE=BASE/'timing-ablation-source'
ABLATION=BASE/'timing-ablation-executor'

def build():
    SOURCE.mkdir(exist_ok=False);(SOURCE/'research').mkdir();(SOURCE/'crates').symlink_to(ROOT/'crates',target_is_directory=True)
    for p in (ROOT/'research').iterdir():
        if p.is_dir() and p.name!='lp-mixed2-fp4':(SOURCE/'research'/p.name).symlink_to(p,target_is_directory=True)
    dest=SOURCE/'research/lp-mixed2-fp4';shutil.copytree(ROOT/'research/lp-mixed2-fp4',dest,ignore=shutil.ignore_patterns('target'))
    p=dest/'src/main.rs';s=p.read_text().replace('let phase = Instant::now();','let phase = NoPhase;').replace('let initial_audit = Instant::now();','let initial_audit = NoPhase;')
    s+='\nstruct NoPhase;\nimpl NoPhase { fn elapsed(&self) -> std::time::Duration { std::time::Duration::ZERO } }\n';p.write_text(s)
    p=dest/'src/device.rs';s=p.read_text();start=s.index('    pub fn run(');end=s.index('    pub fn raw(',start);part=s[start:end].replace('        self.start.record(stream)?;\n','').replace('        self.end.record(stream)?;\n','').replace('let gpu_us = f64::from(self.start.elapsed_to(&self.end)?) * 1000.;','let gpu_us = 0.;');s=s[:start]+part+s[end:];p.write_text(s)
    put(BASE/'timing-ablation-source.json',dict(control=ref(BINARY),sources=[ref(p) for p in sorted(dest.rglob('*')) if p.is_file()],change='only phase clock reads and run-window CUDA event records/elapsed read removed; original stream synchronization/readbacks and deadlines retained'))
    subprocess.run(['cargo','build','--manifest-path',str(dest/'Cargo.toml'),'--release','--locked','--offline','--target-dir',str(ROOT/'research/lp-mixed2-fp4/target')],check=True)
    shutil.copy2(ROOT/'research/lp-mixed2-fp4/target/release/lp-mixed2-fp4',ABLATION)
    put(BASE/'timing-ablation-binary.json',dict(binary=ref(ABLATION),source=ref(BASE/'timing-ablation-source.json')))

def numerical(r):
    def strip(x):
        if isinstance(x,dict):return {k:strip(v) for k,v in x.items() if k not in ('gpu_us','checker_binary_sha256')}
        if isinstance(x,list):return list(map(strip,x))
        return x
    return bits({k:strip(r[k]) for k in ('endpoint','certificate','audits','checkpoint','terminal','physical','logical','attempted','status','events')})

def run():
    out=BASE/'timing-ablation-v1';out.mkdir(exist_ok=False);image=BASE/'build-v8/mixed.cubin';models=load(BASE/'models/manifest-v2.json');rng=random.Random(380077);cells=[]
    for block in range(4):
        families=['dense-generic-128','dense-generic-512','dense-generic-1024','dense-generic-2048','dense-coupled-2048'];rng.shuffle(families)
        for family in families:
            lanes=['native','fp4x2'];rng.shuffle(lanes)
            for lane in lanes:
                variants=['timed','minimal'];rng.shuffle(variants)
                for position,v in enumerate(variants):cells.append(dict(id=f'b{block}-{family}-{lane}-{v}',block=block,family=family,lane=lane,variant=v,position=position,settings=dict(window_max=32 if lane=='native' else 16,fixed_audit=True)))
    put(out/'manifest.json',dict(control=ref(BINARY),ablation=ref(ABLATION),image=ref(image),source=ref(BASE/'timing-ablation-source.json'),cells=cells,blocks=4,repeats=3,seed=380077))
    rows=[];pairs={}
    for cell in cells:
        transport.BINARY=BINARY if cell['variant']=='timed' else ABLATION
        row=execute_session(out,cell,image,models,['certified-1e-9'],3);rows.append(row)
        key=(cell['block'],cell['family'],cell['lane']);values=[numerical(load(ROOT/r['result']['path'])) for r in row['records']]
        if key in pairs:require(values==pairs[key],'timer ablation changed numerical state')
        else:pairs[key]=values
    put(out/'result.json',dict(status='complete',sessions=rows,exact_pairs=len(pairs)))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['build','run']);a=p.parse_args();build() if a.action=='build' else run()
