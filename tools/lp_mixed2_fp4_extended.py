"""Prospectively added larger coupled fixtures; no timing-selected model changes."""
import json
import subprocess
import numpy as np
from lp_mixed2_fp4_common import ROOT,BASE,BINARY,load,put,ref,require
from lp_mixed2_fp4_cpu import fixture,environment


def run():
    old=load(BASE/'models/manifest.json');models=dict(old['models']);rows=[]
    for n in (1024,2048):
        family=f'dense-coupled-{n}';i=np.arange(n)
        a=np.eye(n)+(((13*i[:,None]+7*i[None,:])%37)-18)/(73*n)
        a[i,(i+1)%n]+=.5
        x=(13*i%37)/37-.5;y=(7*i%29)/29-.5;c=a.T@y;rhs=a@x
        doc=fixture(a,'mixed2-fp4-'+family)
        for row,v in zip(doc['constraints'],rhs):row['lower']['value']=row['upper']['value']=float(v)
        doc['objective']['terms']=[dict(variable_id=3*j+7,coefficient=float(c[j])) for j in range(n) if c[j]!=0]
        path=BASE/'models'/(family+'.json')
        with path.open('x') as f:json.dump(doc,f,separators=(',',':'),allow_nan=False)
        models[family]=ref(path);del doc,a
        process=subprocess.run([str(BINARY),'check-service',str(path)],input=b'',capture_output=True,check=True,env=environment(),timeout=90)
        ready=json.loads(process.stdout);require(ready['ready'],'extended independent checker readiness');rows.append(dict(family=family,ready=ready))
        print(dict(prepared=family),flush=True)
    put(BASE/'models/manifest-v2.json',dict(**{k:v for k,v in old.items() if k!='models'},models=models,extension=dict(generator=ref(__file__),coupling=.5,roster=['dense-coupled-1024','dense-coupled-2048'],checker_admission=rows)))
if __name__=='__main__':run()
