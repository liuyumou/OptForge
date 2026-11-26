"""Minimal cold-process entry point for the lean candidate; no baseline imports."""
import argparse
import hashlib
import json
from pathlib import Path
from lp_sp_pricing_run import attempt


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('model',type=Path);p.add_argument('output',type=Path)
    p.add_argument('--library',type=Path);p.add_argument('--cpu',action='store_true');p.add_argument('--seconds',type=float,default=10)
    p.add_argument('--width',type=int,choices=[1,8,32,64],default=64)
    p.add_argument('--steps',type=int,default=1000);p.add_argument('--dense',action='store_true')
    a=p.parse_args()
    if not a.cpu and a.library is None:p.error('--library is required for GPU execution')
    config=None if a.cpu else dict(library=str(a.library.resolve()),mode='fp64',sparse=not a.dense,backend='lean',steps=a.steps)
    result=attempt(json.loads(a.model.read_text()),seconds=a.seconds,operations=200000000,
                   gpu=config,batch=32 if a.cpu else a.width,compact_trace=True,market_backend='flow')
    result['model_sha256']=hashlib.sha256(a.model.read_bytes()).hexdigest()
    result['trace_policy']='compact; original-model final certificate retained'
    with a.output.open('x') as stream:json.dump(result,stream,sort_keys=True,allow_nan=False);stream.write('\n')
    print(json.dumps({k:result[k] for k in ['status','audit','complete_ns']}))
    raise SystemExit(int(result['status']=='implementation_error'))
