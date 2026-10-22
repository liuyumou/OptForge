"""Compile-only exact source test-binary inventory; never opens a CUDA context."""
import json
import os
from pathlib import Path
import subprocess
from benchmark_lp import source_identity,reference
from lp_protocol import ROOT,write_json,file_hash

def main():
    env=dict(os.environ,CARGO_BUILD_JOBS='4')
    command=['cargo','test','-p','optimizer-cuda','-p','optimizer-schedule-examples','-p','optimizer-lp-cuda','--all-features','--no-run','--message-format=json','--locked']
    r=subprocess.run(command,cwd=ROOT,capture_output=True,text=True,env=env)
    directory=ROOT/'artifacts/gpup-assess-v1/build';directory.mkdir(parents=True,exist_ok=True)
    (directory/'tests.stdout').write_text(r.stdout);(directory/'tests.stderr').write_text(r.stderr)
    if r.returncode:raise ValueError('assessment test compilation failed '+r.stderr[-2000:])
    found={}
    for line in r.stdout.splitlines():
        d=json.loads(line)
        if d.get('reason')!='compiler-artifact' or not d.get('executable') or not d['profile']['test']:continue
        source=Path(d['target']['src_path']);name=d['target']['name'];package=source.parent.parent.name
        key= 'assess' if name=='assess_device' else package if name=='device' else None
        if key:found[key]=reference(ROOT,Path(d['executable']))
    required=['optimizer-cuda','optimizer-schedule-examples','optimizer-lp-cuda','assess']
    if set(found)!=set(required):raise ValueError('assessment binary roster differs '+str(found))
    write_json(ROOT/'target/lp-assess-binaries.json',dict(source_tree_sha256=source_identity(),binaries=found))
    print('compiled four exact-source device suites; no GPU work')
if __name__=='__main__':main()
