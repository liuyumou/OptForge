"""Final independent CPU reassessment and process refusal admission."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
from lp_mixed2_fp4_common import BASE,BINARY,ROOT,load,put,ref,require
from lp_mixed2_fp4_cpu import environment
from lp_mixed2_fp4_transport import Service
from lp_delivery2_study import bits

def endpoints(out):
    out=Path(out);out.mkdir(exist_ok=False);models=load(BASE/'models/manifest-v2.json')['models'];unique={};requests=0
    for folder in ['development-v1','development-v2','windows-v1','schedule-v1']+[f'confirmation-b{i:02d}' for i in range(32)]:
        directory=BASE/folder
        sessions=load(directory/'result.json')['sessions'] if (directory/'result.json').exists() else [load(p) for p in directory.glob('*.session.json')]
        candidates=[(s['family'],ROOT/rr['result']['path']) for s in sessions for rr in s['records']]
        if folder=='confirmation-b25':
            seen={p for _,p in candidates}
            for c in load(BASE/'confirmation-freeze.json')['cells']:
                if c['block']!=25:continue
                for p in directory.glob(c['id']+'-certified-*.json'):
                    if p not in seen:candidates.append((c['family'],p))
        for family,path in candidates:
                r=load(path)
                for endpoint,certificate in [(r['endpoint'],r['certificate'])]+[(a['endpoint'],a['certificate']) for a in r['audits']]:
                    value=dict(endpoint=endpoint,tier=r['tier'],family=family);key=hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':')).encode()).hexdigest();expected={k:v for k,v in certificate.items() if k!='checker_binary_sha256'}
                    if key in unique:require(bits(unique[key]['expected'])==bits(expected),'same endpoint conflicting certificate')
                    else:unique[key]=dict(**value,expected=expected)
                    requests+=1
    put(out/'manifest.json',dict(binary=ref(BINARY),endpoints=len(unique),requests=requests));rows=[]
    for key,v in sorted(unique.items()):
        ep=out/(key+'.endpoint.json');put(ep,v['endpoint']);dest=out/(key+'.certificate.json')
        subprocess.run([str(BINARY),'check-serial',str(ROOT/models[v['family']]['path']),str(ep),v['tier'],str(dest)],check=True,capture_output=True,timeout=120,env=environment())
        actual=load(dest);require(bits({k:v for k,v in actual.items() if k!='checker_binary_sha256'})==bits(v['expected']),'independent original serial checker differs')
        rows.append(dict(key=key,family=v['family'],tier=v['tier'],endpoint=ref(ep),certificate=ref(dest)))
    put(out/'result.json',dict(status='passed',endpoints=len(rows),requests=requests,rows=rows));print(dict(status='passed',endpoints=len(rows),requests=requests),flush=True)

def processes(out):
    out=Path(out);out.mkdir(exist_ok=False);image=BASE/'build-v8/mixed.cubin';model=ROOT/load(BASE/'models/manifest.json')['models']['irregular-tail-33']['path'];rows=[]
    put(out/'manifest.json',dict(binary=ref(BINARY),image=ref(image),model=ref(model)))
    bad=[dict(op='solve',solve_id=1),dict(op='solve',generation=1),dict(op='solve',window_max=0),dict(op='solve',window_max=64),dict(op='solve',audit_max=201),dict(op='solve',max_updates=10001),dict(op='solve',max_updates=0),dict(op='solve',wall_ms=30001),dict(op='solve',tier='fake'),dict(op='solve',lane='fp4'),dict(op='solve',fault='unknown'),dict(op='unknown'),dict(op='solve',unknown=True)]
    for i,fields in enumerate(bad):
        s=Service(image,model,out/f'invalid-{i}.log')
        s.write(dict(solve_id=0,generation=0,lane='fp4x2',tier='certified-1e-9')|fields)
        s.close(expected=1);require(s.proc.stdout.closed,'output not closed');rows.append(dict(case='invalid-request',fields=fields,exit=1))
    for case in ('stale-generation','active-solve','over-cap','stale-solve','empty-eof'):
        s=Service(image,model,out/(case+'.log'))
        if case=='empty-eof':s.close();rows.append(dict(case=case,exit=0));continue
        if case=='stale-solve':
            s.call('solve',lane='native',tier='certified-1e-9',fixed_audit=True)
            s.write(dict(op='solve',solve_id=0,lane='native',tier='certified-1e-9'))
        else:
            s.call('debug_reset',lane='fp4x2',max_updates=2)
            if case=='stale-generation':
                s.call('debug_restore');s.write(dict(op='debug_export',solve_id=0,generation=0))
            elif case=='active-solve':s.write(dict(op='solve',solve_id=0,lane='native',tier='certified-1e-9'))
            else:s.write(dict(op='debug_step',solve_id=0,generation=0,count=3,limit=1e20))
        s.close(expected=1);rows.append(dict(case=case,exit=1))
    for case,args,env in [('model-missing',['serve',str(image),str(out/'missing')],environment()),('image-missing',['serve',str(out/'missing'),str(model)],environment()),('lease-missing',['serve',str(image),str(model)],environment()|{'AI_OPTIMIZER_GPU_LEASE':''}),('conflicting-env',['serve',str(image),str(model)],environment()|{'GPUP_DELIVERY_VARIANT':'candidate'})]:
        p=subprocess.run([str(BINARY)]+args,capture_output=True,env=env,timeout=60);require(p.returncode!=0 and not p.stdout,'setup failure escaped')
        (out/(case+'.log')).write_bytes(p.stderr);rows.append(dict(case=case,exit=p.returncode))
    put(out/'result.json',dict(status='passed',cases=len(rows),rows=rows));print(dict(status='passed',cases=len(rows)))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['endpoints','processes']);p.add_argument('out');a=p.parse_args();(endpoints if a.action=='endpoints' else processes)(a.out)
