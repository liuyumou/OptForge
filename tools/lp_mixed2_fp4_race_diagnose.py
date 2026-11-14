"""Predeclared eight-process comparison after the retained racecheck exit 11."""
import json
import os
import subprocess
from lp_mixed2_fp4_common import ROOT,BASE,BINARY,load,put,ref
from lp_mixed2_fp4_transport import Service


def run():
    out=BASE/'race-diagnose-v1';out.mkdir(exist_ok=False)
    os.environ['AI_OPTIMIZER_SANITIZER']='racecheck';os.environ['AI_OPTIMIZER_ADMISSION_TRACE']='1'
    models=load(BASE/'models/manifest.json');model=ROOT/models['models']['irregular-tail-33']['path']
    order=['build-v8','build-v6','build-v6','build-v8','build-v8','build-v6','build-v6','build-v8']
    put(out/'manifest.json',dict(binary=ref(BINARY),model=ref(model),order=order,prior_failure=ref(BASE/'resources/racecheck-v3.settlement.json'),images={name:ref(BASE/name/'mixed.cubin') for name in set(order)}))
    rows=[]
    for index,name in enumerate(order):
        s=None;error=None;result=None;code=None
        try:
            s=Service(BASE/name/'mixed.cubin',model,out/f'{index}-{name}.log')
            result,elapsed=s.solve_to_file(out/f'{index}-{name}.json',lane='native',tier='certified-1e-9',**models['settings'])
        except BaseException as e:error=repr(e)
        finally:
            if s:
                try:s.close()
                except BaseException as e:error=(error or '')+'; close: '+repr(e)
                code=s.proc.returncode
        row=dict(index=index,image=name,error=error,code=code,certified=result['certified'] if result else None);rows.append(row);put(out/f'{index}.outcome.json',row);print(row,flush=True)
    put(out/'result.json',dict(status='diagnostic-complete',rows=rows))
if __name__=='__main__':run()
