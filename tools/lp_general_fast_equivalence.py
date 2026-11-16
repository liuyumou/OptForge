"""Exact transcript check for hoisting FP32 vector differences out of sparse loops."""
import argparse
import json
from lp_general_common import BASE,load,put,ref,require


def run(identity,before,after):
    old=BASE/before;new=BASE/after;a=load(new/'result.json');require(a['status']=='passed','completed admission required')
    paths=sorted(old.glob('*.response.json'));require({p.name for p in paths}=={p.name for p in new.glob('*.response.json')},'response coverage changed')
    ignored={'elapsed_ns','cost_ns','device_bytes_upper'};records=[]
    for p in paths:
        q=new/p.name;x=load(p);y=load(q)
        # Canonical JSON distinguishes signed zero, unlike Python float equality.
        canonical=lambda r:json.dumps({k:v for k,v in r.items() if k not in ignored},sort_keys=True,separators=(',',':'))
        require(canonical(x)==canonical(y),'cached vector arithmetic differs '+p.name)
        records.append(dict(before=ref(p),after=ref(q)))
    out=BASE/identity;out.mkdir(exist_ok=False)
    put(out/'result.json',dict(status='passed',binary=a['binary'],image=a['image'],responses=len(records),records=records,ignored=sorted(ignored),source=ref(__file__)))
    print(dict(status='passed',responses=len(records)),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--id',required=True);p.add_argument('--before',required=True);p.add_argument('--after',required=True);a=p.parse_args();run(a.id,a.before,a.after)
