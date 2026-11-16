"""Final source, frozen-runner, resource and dependency bindings for scale work."""
import argparse
import ast
import json
from pathlib import Path
import subprocess
import sys
import numpy as np
import scipy
from lp_general_common import BASE,ROOT,load,put,ref,require
from lp_general_budget import accounting
from lp_general_portable import digest,archive_ref
from lp_general_scale_copt import PYTHON
from lp_general_scale_imports import validate as validate_imports

def run(identity):
    out=BASE/identity;out.mkdir(exist_ok=False)
    for p in (ROOT/'tools').glob('lp_general_scale*.py'):ast.parse(p.read_text())
    require(not subprocess.check_output(['git','diff','--name-only','HEAD','--','crates'],cwd=ROOT,text=True).strip(),'public core source changed')
    historical_documents=[]
    for name in ['AGENTS.md','docs/plans/lp-benchmark-scaling.md','docs/plans/gpu-lp-precision-roadmap.md',
                 'docs/specifications/SPEC-0045-general-lowbit-lp.md']:
        original=subprocess.check_output(['git','show','HEAD:'+name],cwd=ROOT)
        current=(ROOT/name).read_bytes()
        preserved=current.endswith(original) if name=='AGENTS.md' else original.split(b'\n',1)[1] in current
        require(preserved,'historical documentation changed '+name)
        historical_documents.append(name)
    require(digest(BASE/'scale-image-v6/tensor.cubin')==digest(BASE/'fast-image-v10/tensor.cubin'),'device image changed')
    for p in (ROOT/'research/lp-general-lowbit/src').glob('*.rs'):
        retained=BASE/'sources/scale-cpu-v6'/p.relative_to(ROOT)
        require(p.read_bytes()==retained.read_bytes(),'numerical source changed after final CPU admission')
    proofs=[]
    names=['scale-cpu-v6','scale-gpu-v7','scale-input-refusal-v1','scale-evidence-contract-v1','scale-smoke-v6',
                 'scale-native-final-v1','scale-python-final-v2','scale-python-final-v3','scale-deferred-audit-v2','scale-deferred-smoke-v1',
                 'scale-copt-cpu-v1','scale-copt-gpu-disposition-v1','scale-replay-admission-v2',
                 'scale-gap-diagnosis-v1']+['scale-'+s+'-v7' for s in ['memcheck','racecheck','initcheck','synccheck']]
    target=None
    if (BASE/'scale-image-v7').exists():
        names+=['scale-cpu-v7','scale-target-gpu-v1','scale-frontier-report-v1','scale-target-report-v1']
        names+=['scale-target-'+s+'-v1' for s in ['memcheck','racecheck','initcheck','synccheck']]
        before=BASE/'scale-host-target-v1/original-fingerprint.json';after=BASE/'scale-host-target-v1/candidate-fingerprint.json'
        require(load(before)['rustflags']==[] and load(after)['rustflags']==['-C','target-cpu=x86-64-v4'],'host target fingerprint differs')
        require(digest(BASE/'scale-image-v7/tensor.cubin')==digest(BASE/'scale-image-v6/tensor.cubin'),'host target changed device code')
        target=dict(original_fingerprint=ref(before),candidate_fingerprint=ref(after),binary=ref(BASE/'scale-image-v7/executor'),checker_imports=validate_imports('scale-cpu-v7'))
    for name in names:
        p=BASE/'resources'/(name+'.settlement.json');require(load(p)['status']=='passed','admission missing '+name);proofs.append(ref(p))
    resources=[];failures=[]
    for p in sorted((BASE/'resources').glob('scale-*.settlement.json')):
        s=load(p);require(not s['overrun'],'resource overrun')
        r=load(ROOT/s['resource']['path']);require(r['guardian_cleanup']['empty'] and r['result']['cleanup']['empty'],'cleanup incomplete')
        reservation=load(p.with_name(p.name.replace('.settlement.json','.reservation.json')))
        if s['status']!='passed':
            require(s['cpu_ns']>=reservation['cpu_ns'] and s['gpu_ns']>=reservation['gpu_ns'],'failed reservation undercharged')
            failures.append(ref(p))
        resources.append(ref(p))
    env=subprocess.run([str(PYTHON),'-c','import sys,numpy,scipy,coptpy,json;print(json.dumps(dict(python=sys.version,numpy=numpy.__version__,scipy=scipy.__version__,copt=coptpy.__file__)))'],text=True,capture_output=True)
    require(env.returncode==0,'baseline environment query failed')
    baseline=load(BASE/'scale-copt-cpu-v1/irregular-0.copt.json')
    libraries=[]
    for key,installed in [('library','lib/python/deps/libcopt_python.so'),('binding','lib/python/311/coptpy/coptcore.so')]:
        item=baseline[key];p=ROOT/item['path'];require(ref(p)==item,'admitted baseline library changed')
        require(digest(p)==digest(Path('/root/copt80')/installed),'baseline differs from installed COPT')
        libraries.append(item)
    operational=BASE/'operational-readmission-v5.json'
    admission=load(operational);require(admission['status']=='passed','operational readmission missing')
    for item in admission['sources']:
        require(ref(ROOT/item['path'])==item,'operational source changed')
    cpu,gpu=accounting()
    put(out/'result.json',dict(status='passed',proofs=proofs,resources=resources,failures=failures,
        historical_documents_preserved=historical_documents,
        operational_readmission=ref(operational),
        host_target=target,
        source=[ref(p) for p in sorted((ROOT/'research/lp-general-lowbit/src').glob('*.rs'))],checker_imports=validate_imports('scale-cpu-v6'),
        tools=[ref(p) for p in sorted((ROOT/'tools').glob('lp_general_scale*'))],
        environment=dict(python=sys.version,numpy=np.__version__,scipy=scipy.__version__,baseline=json.loads(env.stdout),baseline_libraries=libraries,baseline_python=dict(path=str(PYTHON.relative_to(ROOT)),sha256=digest(PYTHON))),
        cpu_seconds={k:v/1e9 for k,v in cpu.items()},gpu_seconds={k:v/1e9 for k,v in gpu.items()},
        note='Current versions and executable identity. Source snapshots bind each earlier attempt; no license contents copied. Current reporting reservation is still open.'))
    print(dict(status='passed',resources=len(resources),failures=len(failures)),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--id',required=True);run(p.parse_args().id)
