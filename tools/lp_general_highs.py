"""Pinned external CPU reference on the unchanged broad development roster."""
import argparse
import json
import subprocess
import time
from lp_general_common import ROOT,BASE,put,ref,load,require
from lp_general_oracle import BINARY,settings
from lp_general_device import serial
from lp_baseline_common import options

HIGH=ROOT/'research/lp-external-baseline/target/release/lp-external-baseline'

def run(identity):
    out=BASE/identity;out.mkdir(parents=True,exist_ok=False)
    frozen=load(BASE/'development-pilot-v1/freeze.json');models={r['model_index']:r for r in frozen['cells']};rows=[]
    for index,cell in sorted(models.items()):
        model=ROOT/cell['model']['path'];opt=options(10);opt.update(iteration_limit=None,threads=1)
        op=out/f'm{index:02d}.options.json';dest=out/f'm{index:02d}.native.json';put(op,opt)
        start=time.monotonic_ns();p=subprocess.run([str(HIGH),'highs',str(model),str(op),str(dest)],text=True,capture_output=True)
        elapsed=time.monotonic_ns()-start;(out/f'm{index:02d}.stdout').write_text(p.stdout);(out/f'm{index:02d}.stderr').write_text(p.stderr)
        row=dict(model_index=index,family=cell['family'],model=cell['model'],returncode=p.returncode,producer_ns=elapsed,options=ref(op))
        if p.returncode==0:
            r=load(dest);row.update(native=ref(dest),termination=r['record']['termination'],certificates=[])
            candidate=r['record']['candidate'];dual=r['diagnostics']['dual']
            if candidate is not None and dual is not None:
                x=[a['value'] for a in candidate['values']]
                requests=[dict(settings={**settings('native'),'tolerance':t},primal=x,dual=dual) for t in [1e-7,1e-9]]
                started=time.monotonic_ns();check=subprocess.run([str(BINARY),'assess',str(model)],input=''.join(json.dumps(q)+'\n' for q in requests),text=True,capture_output=True,check=True)
                row['checker_process_ns']=time.monotonic_ns()-started
                certs=[json.loads(s) for s in check.stdout.splitlines()];require(len(certs)==2,'external checker coverage')
                for i,(request,certificate) in enumerate(zip(requests,certs)):
                    proof=serial(model,dict(primal=x,dual=dual,certificate=certificate),request['settings']['tolerance'],out,f'm{index:02d}-{i}')
                    row['certificates'].append(dict(tolerance=request['settings']['tolerance'],certificate=certificate,serial=proof))
        rows.append(row);put(out/f'm{index:02d}.json',row)
        print(dict(model_index=index,family=cell['family'],producer_ms=elapsed/1e6,termination=row.get('termination'),certificates=[r['certificate']['accepted'] for r in row.get('certificates',[])]),flush=True)
    put(out/'result.json',dict(status='complete',rows=rows,producer=ref(HIGH),checker=ref(BINARY),
        scope='External producer and checker process times separate; no GPU activity, no external status treated as certificate'))
    require(all(r['returncode']==0 for r in rows),'external execution admission failed; all attempted cells retained')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--id',required=True);a=p.parse_args();run(a.id)
