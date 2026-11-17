"""Source-bound timelines bracketed by uninstrumented exact transcript checks."""
import argparse
import json
import os
import subprocess
import time
from lp_general_common import BASE,ROOT,load,put,ref,require
from lp_general_tensor_diagnose import NSYS,external_ref


def freeze(identity,pilot,split=False):
    root=BASE/identity;root.mkdir(exist_ok=False);p=load(BASE/pilot/'freeze.json');cells=[]
    for i in [3,18,21]:
        for fmt in ['native','fp32','fp4x2']+(['fp4x2-split'] if split else []):
            c=next(c for c in p['cells'] if c['model_index']==i and c['format']==fmt)
            cells.append(dict(**c,model=p['models'][i]['model'],reference=ref(BASE/pilot/f'm{i:02d}'/(c['id']+'.response.json'))))
    put(root/'freeze.json',dict(cells=cells,harness=ref(__file__),pilot=ref(BASE/pilot/'freeze.json'),nsys=external_ref(NSYS)))


def run(identity,index):
    root=BASE/identity;f=load(root/'freeze.json');require(ref(__file__)==f['harness'],'harness changed')
    require(external_ref(NSYS)==f['nsys'],'profiler changed')
    for c in [c for c in f['cells'] if c['model_index']==index]:
        for k in ['binary','image','model','reference']:require(ref(ROOT/c[k]['path'])==c[k],'frozen source changed')
        for mode in ['before','trace','after']:
            out=root/(c['id']+'-'+mode);out.mkdir(exist_ok=False)
            command=[str(ROOT/c['binary']['path']),'gpu-fast',str(ROOT/c['model']['path']),str(ROOT/c['image']['path'])]
            if mode=='trace':command=[str(NSYS),'profile','--trace=cuda','--sample=none','--cpuctxsw=none','--cuda-event-trace=false','--export=sqlite','--stats=false','--output='+str(out/'trace'),*command]
            env=dict(os.environ);env['LD_LIBRARY_PATH']='/tmp/gpup2-nsys-libs/root/usr/lib/x86_64-linux-gnu'+(':'+env['LD_LIBRARY_PATH'] if env.get('LD_LIBRARY_PATH') else '')
            request=json.loads(json.dumps(c['request']));request['settings']['wall_ms']=120000
            put(out/'command.json',dict(argv=command,request=request));start=time.monotonic_ns()
            p=subprocess.run(command,input=json.dumps(request)+'\n',capture_output=True,text=True,env=env);elapsed=time.monotonic_ns()-start
            (out/'stdout').write_text(p.stdout);(out/'stderr').write_text(p.stderr);require(p.returncode==0,'profile failed')
            response=[json.loads(s) for s in p.stdout.splitlines() if s.startswith('{')];require(len(response)==1,'one response required');r=response[0]
            put(out/'response.json',r);expected=load(ROOT/c['reference']['path']);ignored={'cost_ns','elapsed_ns','settings'}
            require({k:v for k,v in r.items() if k not in ignored}=={k:v for k,v in expected.items() if k not in ignored},'profile changed numerical work')
            require({k:v for k,v in r['settings'].items() if k!='wall_ms'}=={k:v for k,v in expected['settings'].items() if k!='wall_ms'},'settings differ')
            if mode=='trace':require((out/'trace.sqlite').exists(),'trace missing')
            put(out/'result.json',dict(status='passed',response=ref(out/'response.json'),outer_ns=elapsed,exact=True,reference=c['reference']))
            print(dict(cell=c['id'],mode=mode,execution_ms=r['cost_ns']['execution']/1e6),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['freeze','run']);p.add_argument('--id',required=True);p.add_argument('--pilot');p.add_argument('--split',action='store_true');p.add_argument('--index',type=int);a=p.parse_args()
    if a.action=='freeze':freeze(a.id,a.pilot,a.split)
    else:run(a.id,a.index)
