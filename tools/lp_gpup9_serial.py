"""Original serial checker verification of all distinct timed assessments."""
import argparse
import hashlib
import json
import os
import subprocess
from lp_gpup9_common import BASE, ROOT, SERIAL, load, put, ref, checked, require
from lp_delivery2_study import bits


def run(admission=False):
    out=BASE/('serial-admission-v2' if admission else 'serial-study');out.mkdir(exist_ok=False)
    folders=[BASE/'pilot',BASE/'pilot-v2',BASE/'pilot-v3'] if admission else [p for stage in ['screening','validation','holdout'] for p in sorted((BASE/stage).glob('b*'))]
    models={item['sha256']:item for root in [BASE/'models',BASE/'models-v2'] for p in root.glob('*/manifest.json')
            for group in load(p)['groups'].values() for item in group['models']}
    unique={};responses=requests=0;response_refs=[]
    for folder in folders:
        for path in sorted(folder.glob('*-r[0-9][0-9].json')):
            r=load(path);responses+=1;response_refs.append(ref(path))
            for endpoint,certificate in [(r['endpoint'],r['certificate'])]+[(a['endpoint'],a['certificate']) for a in r['audits']]:
                entry=dict(endpoint=endpoint,tier=r['tier'])
                key=hashlib.sha256(json.dumps(entry,sort_keys=True,separators=(',',':')).encode()).hexdigest()
                expected={k:v for k,v in certificate.items() if k!='checker_binary_sha256'}
                if key in unique:require(bits(unique[key]['expected'])==bits(expected),'inconsistent assessment')
                else:unique[key]=dict(**entry,expected=expected)
                requests+=1
    records=[]
    for i,(key,entry) in enumerate(sorted(unique.items())):
        ep=out/(key+'.endpoint.json');dest=out/(key+'.certificate.json');put(ep,entry['endpoint'])
        item=models[entry['endpoint']['model_sha256']];checked(item)
        subprocess.run([str(SERIAL),'check-serial',str(ROOT/item['path']),str(ep),entry['tier'],str(dest)],
            capture_output=True,check=True,timeout=120,env=os.environ|{'CUDA_VISIBLE_DEVICES':''})
        actual={k:v for k,v in load(dest).items() if k!='checker_binary_sha256'}
        require(bits(actual)==bits(entry['expected']),'original serial authority mismatch')
        records.append(dict(endpoint=ref(ep),certificate=ref(dest),tier=entry['tier'],model=item))
        if i%20==0:print(dict(serial=i+1,total=len(unique)),flush=True)
    put(out/'result.json',dict(status='passed',binary=ref(SERIAL),responses=responses,
        assessment_requests=requests,unique_assessments=len(records),records=records,response_files=response_refs))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--admission',action='store_true');run(p.parse_args().admission)
