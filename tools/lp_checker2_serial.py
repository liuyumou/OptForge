"""Independent original serial checking of every distinct assessed endpoint/tier."""
import argparse
import hashlib
import json
import os
import subprocess
from pathlib import Path
from lp_checker2_common import BASE, ROOT, PRIOR, load, put, ref, require
from lp_delivery2_study import bits

def run(confirmation=False):
    out=BASE/('serial-confirmation' if confirmation else 'serial-optimized');out.mkdir(exist_ok=False)
    models=load(PRIOR/'models/manifest.json');paths={p['sha256']:p for items in models['groups'].values() for p in items}
    folders=[BASE/'smoke-optimized',BASE/'pilot-optimized']
    if confirmation:folders+=sorted((BASE/'confirmation').glob('b*'))
    unique={};responses=requests=0
    for folder in folders:
        for path in sorted(folder.glob('*-r[0-9][0-9].json')):
            r=load(path);responses+=1
            for endpoint,cert in [(r['endpoint'],r['certificate'])]+[(a['endpoint'],a['certificate']) for a in r['audits']]:
                entry=dict(endpoint=endpoint,tier=r['tier']);key=hashlib.sha256(json.dumps(entry,sort_keys=True,separators=(',',':')).encode()).hexdigest()
                expected={k:v for k,v in cert.items() if k!='checker_binary_sha256'}
                if key in unique:require(bits(unique[key]['expected'])==bits(expected),'inconsistent assessment')
                else:unique[key]=dict(**entry,expected=expected)
                requests+=1
    old=ROOT/'artifacts/gpup-mixed2-fp4-v1/build-v10/executor';records=[]
    for key,entry in sorted(unique.items()):
        ep=out/(key+'.endpoint.json');dest=out/(key+'.certificate.json');put(ep,entry['endpoint'])
        subprocess.run([str(old),'check-serial',str(ROOT/paths[entry['endpoint']['model_sha256']]['path']),str(ep),entry['tier'],str(dest)],
                        check=True,capture_output=True,timeout=120,env=os.environ|{'CUDA_VISIBLE_DEVICES':''})
        clean={k:v for k,v in load(dest).items() if k!='checker_binary_sha256'}
        require(bits(clean)==bits(entry['expected']),'independent serial certificate mismatch')
        records.append(dict(endpoint=ref(ep),certificate=ref(dest),tier=entry['tier']))
    put(out/'result.json',dict(status='passed',binary=ref(old),responses=responses,assessment_requests=requests,
                              unique_assessments=len(records),records=records))
    print(dict(responses=responses,assessments=requests,unique=len(records)),flush=True)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--confirmation',action='store_true');run(p.parse_args().confirmation)
