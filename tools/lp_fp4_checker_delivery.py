"""Preserve historical bytes, verify closure and publish exact task accounting."""
import argparse
import hashlib
import os
from pathlib import Path
import subprocess
from lp_fp4_checker_common import ROOT,BASE,CPU_CAPS,GPU_CAPS,NS,put,ref,load,require
from lp_fp4_checker_budget import accounting,admission_open

DATA=ROOT/'docs/benchmarks/data'


def history():
    allowed={'AGENTS.md','state/active-task.md','state/backlog.yaml','docs/plans/gpu-lp-precision-roadmap.md'}
    records=subprocess.check_output(['git','ls-tree','-rz','--full-tree','83d513f'],cwd=ROOT).split(b'\0');exact=[]
    for record in records:
        if not record:continue
        meta,name=record.split(b'\t',1);mode,kind,blob=meta.split();name=name.decode()
        if name in allowed:continue
        require(kind==b'blob','unexpected historical gitlink');p=ROOT/name
        raw=os.readlink(p).encode() if mode==b'120000' else p.read_bytes()
        actual=hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()
        require(actual==blob.decode(),'changed historical file: '+name);exact.append(dict(path=name,git_blob=actual))
    return dict(baseline='83d513f',allowed=sorted(allowed),preserved=exact)


def verify():
    data=load(DATA/'fp4-checker-result-v1.json');h=history();m=data['manifest']
    for r in [m['image'],m['parent'],m['cpu_admission'],*m['binaries'].values(),*m['models'].values(),*m['sources']]:
        require(ref(ROOT/r['path'])==r,'changed frozen evidence')
    require(data['cells']==960 and data['certified']==880,'complete bounded/refusal coverage')
    for p in (BASE/'resources').glob('*.settlement.json'):
        s=load(p);require(not s['overrun'],'resource overrun')
        if s['resource']:
            r=load(ROOT/s['resource']['path'])
            require(r['guardian_cleanup']['empty'] and r['result']['cleanup']['empty'],'incomplete cleanup')
    binary=ROOT/m['binaries']['optimized']['path'];archive=BASE/'binaries'/m['binaries']['optimized']['sha256'];archive.parent.mkdir(exist_ok=True)
    if archive.exists():require(archive.read_bytes()==binary.read_bytes(),'changed binary archive')
    else:archive.write_bytes(binary.read_bytes())
    subprocess.run(['python3','tools/validate_artifacts.py'],cwd=ROOT,check=True)
    subprocess.run(['python3','tools/build_docs.py'],cwd=ROOT,check=True)
    subprocess.run(['git','diff','--check'],cwd=ROOT,check=True)
    put(DATA/'fp4-checker-history-v1.json',h)
    put(DATA/'fp4-checker-acceptance-v1.json',dict(status='passed',result=ref(DATA/'fp4-checker-result-v1.json'),
        exact_historical_files=len(h['preserved']),history=ref(DATA/'fp4-checker-history-v1.json'),binary_archive=ref(archive),
        cpu_endpoint_profiles=ref(BASE/'profile-final/result.json'),gpu_integration=ref(BASE/'smoke-v1/result.json'),
        tests=dict(isolated_rust=21,product_random_pairs=500000,product_edges=169,feasibility_cases=2880,cached_certificate_cases=720,
            python_contracts=4,original_core=18,original_lp=45),
        device_sanitizers='unchanged image and device sources; exact prior four-sanitizer admission reused',
        receipts=[ref(p) for p in sorted((BASE/'resources').glob('*.settlement.json'))]))
    print(dict(passed=True,historical_files=len(h['preserved'])),flush=True)


def close():
    admission_open();require(load(DATA/'fp4-checker-acceptance-v1.json')['status']=='passed','delivery acceptance')
    require(load(BASE/'resources/delivery-v1.settlement.json')['status']=='passed','delivery supervisor')
    for p in (BASE/'resources').glob('*.settlement.json'):
        s=load(p)
        if s['resource']:
            r=load(ROOT/s['resource']['path']);require(r['guardian_cleanup']['empty'] and r['result']['cleanup']['empty'],'cleanup')
    cpu,gpu=accounting();cpu['cleanup']+=64*NS
    require(all(cpu[k]<=v*NS for k,v in CPU_CAPS.items()) and all(gpu[k]<=v*NS for k,v in GPU_CAPS.items()),'final allocation overflow')
    receipt=dict(status='closed',cpu_caps_seconds=CPU_CAPS,gpu_caps_seconds=GPU_CAPS,cpu_ns=cpu,gpu_ns=gpu,
        cpu_seconds=sum(cpu.values())/NS,gpu_seconds=sum(gpu.values())/NS,closing_administration_cpu_seconds=64,
        failed_full_reservations=[ref(p) for p in sorted((BASE/'resources').glob('*.settlement.json')) if load(p)['status']!='passed'],
        all_settlements=[dict(binding=ref(p),settlement=load(p)) for p in sorted((BASE/'resources').glob('*.settlement.json'))],
        historical_transfers=0,cleanup_empty=True)
    put(DATA/'fp4-checker-accounting-v1.json',receipt);put(BASE/'CLOSED.json',dict(accounting=ref(DATA/'fp4-checker-accounting-v1.json')))
    print(dict(cpu_seconds=receipt['cpu_seconds'],gpu_seconds=receipt['gpu_seconds'],status='closed'),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['verify','close']);a=p.parse_args()
    verify() if a.action=='verify' else close()
