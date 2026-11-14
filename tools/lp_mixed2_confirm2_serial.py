"""Stream retained assessments through the original independent serial checker."""
import argparse
from collections import defaultdict
import hashlib
import json
import os
from pathlib import Path
import subprocess
from lp_mixed2_confirm2_common import BASE, PRIOR, ROOT, load, put, ref, require
from lp_mixed2_reuse_common import OLD
from lp_delivery2_study import bits


def run(out, confirmation):
    out.mkdir(exist_ok=False);models=load(PRIOR/'models/manifest.json')
    model_paths={p['sha256']:p for paths in models['groups'].values() for p in paths}
    folders=[BASE/'same-image-smoke-v1',BASE/'resource-pilot-v1',BASE/'resource-pilot2-v1',BASE/'resource-pilot3-v1']
    if confirmation:folders += [BASE/f'confirmation-b{i:02d}' for i in range(32)]
    unique={};requests=0;responses=0
    for folder in folders:
        for path in sorted([*folder.glob('*-r[0-9][0-9].json'),*folder.glob('*-fresh[0-9].json'),*folder.glob('*-cached.json'),*folder.glob('[0-9]-fresh.json')]):
            r=load(path);responses+=1
            for endpoint,cert in [(r['endpoint'],r['certificate'])]+[(a['endpoint'],a['certificate']) for a in r['audits']]:
                value=dict(endpoint=endpoint,tier=r['tier'])
                key=hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':')).encode()).hexdigest()
                expected={k:v for k,v in cert.items() if k!='checker_binary_sha256'}
                if key in unique:require(bits(unique[key]['expected'])==bits(expected),'inconsistent repeated receipt')
                else:unique[key]=dict(**value,expected=expected)
                requests+=1
    grouped=defaultdict(list)
    for key,entry in unique.items():grouped[entry['endpoint']['model_sha256']].append((key,entry))
    old=OLD/'build-v10/executor';checked=[]
    for model,entries in sorted(grouped.items()):
        for key,entry in entries:
            ep=out/(key+'.endpoint.json');dest=out/(key+'.certificate.json')
            put(ep,entry['endpoint'])
            subprocess.run([str(old),'check-serial',str(ROOT/model_paths[model]['path']),
                            str(ep),entry['tier'],str(dest)],capture_output=True,check=True,timeout=120,
                           env=os.environ|{'CUDA_VISIBLE_DEVICES':''})
            result=load(dest);clean={k:v for k,v in result.items() if k!='checker_binary_sha256'}
            require(bits(clean)==bits(entry['expected']),'independent original serial certificate mismatch')
            checked.append(dict(endpoint=ref(ep),certificate=ref(dest),tier=entry['tier']))
    put(out/'result.json',dict(status='passed',binary=ref(old),serial_mode='check-serial original arithmetic',
        model_manifest=ref(PRIOR/'models/manifest.json'),responses=responses,assessment_requests=requests,
        unique_assessments=len(checked),records=checked))
    print(dict(status='passed',responses=responses,assessment_requests=requests,unique_assessments=len(checked)),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('out',type=Path);p.add_argument('--confirmation',action='store_true')
    a=p.parse_args();run(a.out,a.confirmation)
