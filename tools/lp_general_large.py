"""Larger independent development operators; compact local models, exact witnesses."""
import json
import subprocess
from lp_general_common import BASE,ROOT,load,put,ref,require
from lp_general_models import generate
from lp_general_oracle import BINARY,settings
from lp_general_device import serial

def run():
    out=BASE/'models-large-v1';out.mkdir(parents=True,exist_ok=False);rows=[]
    sizes=dict(irregular=65537,rectangular=65537,dense_blocks=16385,ill_scaled=32769,degenerate=32769,dense=1025)
    for i,(family,size) in enumerate(sizes.items()):
        seed=819000+i;model,w=generate(family,size,seed);path=out/(model['model_id']+'.json')
        # Generated matrices stay local; deterministic compact bytes avoid
        # pretty-print whitespace and are reproducible from generator and seed.
        with path.open('x') as f:json.dump(model,f,separators=(',',':'),allow_nan=False);f.write('\n')
        witness=out/(model['model_id']+'.construction.json');put(witness,w)
        requests=[dict(settings={**settings(),'tolerance':t},primal=w['primal'],dual=w['dual']) for t in [1e-7,1e-9]]
        p=subprocess.run([str(BINARY),'assess',str(path)],input=''.join(json.dumps(q)+'\n' for q in requests),capture_output=True,text=True,check=True)
        (out/(family+'.responses.jsonl')).write_text(p.stdout);certs=[json.loads(s) for s in p.stdout.splitlines()];require(len(certs)==2,'construction coverage')
        proofs=[]
        for j,(q,c) in enumerate(zip(requests,certs)):
            require(c['accepted'],'large construction certificate')
            proofs.append(serial(path,dict(primal=w['primal'],dual=w['dual'],certificate=c),q['settings']['tolerance'],out,f'{family}-{j}'))
        rows.append(dict(model=ref(path),construction=ref(witness),family=family,size=size,seed=seed,partition='development',certificates=proofs))
        print(dict(family=family,size=size,nonzeros=w['nonzeros'],bytes=path.stat().st_size),flush=True)
    put(out/'manifest.json',dict(status='passed',models=rows,generator=ref(ROOT/'tools/lp_general_models.py'),materializer=ref(__file__),holdout_accessed=False))

if __name__=='__main__':run()
