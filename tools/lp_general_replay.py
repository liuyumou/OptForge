"""Compare numerical transcripts across a declared preparation-only correction."""
import argparse
import json
import struct
from lp_general_common import BASE,put,ref,require

def bits(value):
    if isinstance(value,float):return ('f64',struct.pack('>d',value).hex())
    if isinstance(value,list):return [bits(v) for v in value]
    if isinstance(value,dict):return {k:bits(v) for k,v in value.items()}
    return value

def compare(before,after,identity):
    before=BASE/before;after=BASE/after;rows=[]
    solve=['settings','status','certified','certificate','primal','dual','physical','logical','restarts','attempted','accepted','recoveries','assessments','model_sha256']
    fixed=['step','weight','initial_x','initial_y','column_bounds','row_bounds','objective','primal','dual','restored_x','restored_y','valid','count','model_sha256']
    for a in sorted(before.glob('*.stdout.jsonl')):
        b=after/a.name;require(b.exists(),'missing comparison '+a.name)
        old=[json.loads(s) for s in a.read_text().splitlines()];new=[json.loads(s) for s in b.read_text().splitlines()]
        require(len(old)==len(new),'response coverage')
        for i,(x,y) in enumerate(zip(old,new)):
            fields=fixed if x.get('kind')=='fixed-admission' else solve
            require(bits({k:x[k] for k in fields})==bits({k:y[k] for k in fields}),'numerical transcript differs '+a.name+' '+str(i))
        rows.append(dict(before=ref(a),after=ref(b),responses=len(old)))
    require(rows,'empty comparison')
    put(BASE/(identity+'.json'),dict(status='passed',rows=rows,responses=sum(r['responses'] for r in rows),
        claim='exact unchanged numerical/accepted-work transcripts; preparation costs and storage deliberately differ'))
    print(dict(status='passed',responses=sum(r['responses'] for r in rows)),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--before',required=True);p.add_argument('--after',required=True);p.add_argument('--id',required=True)
    a=p.parse_args();compare(a.before,a.after,a.id)
