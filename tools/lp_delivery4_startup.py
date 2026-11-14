"""Bound CPU attribution; no CUDA work or scientific trajectory."""
import argparse
import statistics
import subprocess
from lp_delivery4_cpu import environment
from lp_delivery4_common import ROOT, BASE, BINARY, load, put, ref, require


def run(variant='control', identity='startup-v1'):
    out=BASE/identity;out.mkdir(exist_ok=False)
    parent=load(ROOT/'artifacts/gpup-fp4-accel-v1/study-v1/manifest.json')
    families=('dense-generic-128','dense-generic-256','dense-generic-512','coupled-equality')
    put(out/'manifest.json',dict(binary=ref(BINARY),models={f:parent['models'][f] for f in families},image=parent['image'],count=5,
        variant=variant,source=ref(ROOT/'research/lp-delivery4/src/startup.rs'),note='Warm CPU constructor-plus-destruction attribution; alternating operation order, no device.'))
    results=[]
    for family in families:
        model=ROOT/parent['models'][family]['path'];require(ref(model)==parent['models'][family],'model changed')
        dest=out/(family+'.json')
        subprocess.run([str(BINARY),'startup-profile',str(model),str(ROOT/parent['image']['path']),'5',str(dest)],check=True,env=environment(variant))
        value=load(dest);groups={}
        require(value['model_sha256']==ref(model)['sha256'],'model digest changed')
        require(value['image_sha256']==parent['image']['sha256'],'image digest changed')
        require(value['executable_sha256']==ref(BINARY)['sha256'],'executable digest changed')
        for row in value['rows']:groups.setdefault(row['operation'],[]).append(row)
        summary={op:dict(median_ms=statistics.median(r['ns'] for r in rows)/1e6,
            scopes={str(scope['path']):statistics.median(next(s['inclusive_ns'] for s in r['costs']['scopes'] if s['path']==scope['path']) for r in rows)/1e6 for scope in rows[0]['costs']['scopes']}) for op,rows in groups.items()}
        results.append(dict(family=family,result=ref(dest),summary=summary))
        print(results[-1],flush=True)
    put(out/'result.json',dict(status='complete',rows=results))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('variant',choices=['control','candidate']);p.add_argument('identity');a=p.parse_args();run(a.variant,a.identity)
