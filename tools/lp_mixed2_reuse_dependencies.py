"""Audit pinned external dependencies and exact local wildcard exceptions."""
import json
import subprocess
from pathlib import Path
from lp_mixed2_reuse_common import ROOT, BASE, load, put, ref, require

EXPECTED = {('lp-mixed2-reuse', name) for name in ('optimizer-core','optimizer-cuda-sys','optimizer-experiment','optimizer-lp')} | {('optimizer-cuda-sys','optimizer-core')}

def audit(metadata):
    paths=[];external=[];exceptions=set()
    for package in metadata['packages']:
        manifest=Path(package['manifest_path'])
        if package['source'] is None:
            require(manifest.resolve().is_relative_to(ROOT),'external unbound local package')
            paths.append(ref(manifest))
        else:
            require(package['source']=='registry+https://github.com/rust-lang/crates.io-index','unknown external source')
            external.append(dict(name=package['name'],version=package['version'],source=package['source']))
        for dep in package['dependencies']:
            if dep['req']=='*':
                require(dep.get('path') is not None and Path(dep['path']).resolve().is_relative_to(ROOT),'external wildcard')
                exceptions.add((package['name'],dep['name']))
    require(exceptions==EXPECTED,'local wildcard roster changed')
    sha=[p for p in external if p['name']=='sha2'];require(len(sha)==1 and sha[0]['version']=='0.10.9','SHA pin changed')
    return dict(paths=paths,external=external,local_wildcards=sorted(exceptions))

def run():
    args=['cargo','metadata','--manifest-path','research/lp-mixed2-reuse/Cargo.toml','--locked','--offline','--format-version','1']
    metadata=json.loads(subprocess.check_output(args,cwd=ROOT));result=audit(metadata)
    subprocess.run(['cargo','deny','--manifest-path','research/lp-mixed2-reuse/Cargo.toml','--locked','--offline','check','--config','research/lp-mixed2-reuse/deny.toml'],cwd=ROOT,check=True)
    put(BASE/'dependencies-v1.json',dict(status='passed',**result,lock=ref(ROOT/'research/lp-mixed2-reuse/Cargo.lock'),policy=ref(ROOT/'research/lp-mixed2-reuse/deny.toml'),source=ref(Path(__file__))))
    print(dict(status='passed',external=len(result['external']),local_wildcards=len(result['local_wildcards'])),flush=True)
if __name__=='__main__':run()
