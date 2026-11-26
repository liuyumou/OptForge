"""Cold-process entry point; the wave backend is installed only in this process."""
import argparse
import hashlib
import json
from pathlib import Path
from lp_sp_pricing_budget import ROOT
from lp_sp_pricing_run import attempt
from sp_pricing import gpu as proposals
from sp_pricing.gpu_wave import WaveBackend,GPU_LIBRARY


def run(model,lane,steps=1000,sparse=True,asynchronous=True,seconds=10):
    if lane=='wave':
        with WaveBackend(asynchronous=asynchronous) as backend:
            original=proposals.propose_labels
            try:
                proposals.propose_labels=backend
                result=attempt(model,seconds=seconds,operations=200000000,compact_trace=True,market_backend='flow',
                    gpu=dict(backend='wave',library=str(GPU_LIBRARY),sparse=sparse,steps=steps),batch=64)
            finally:proposals.propose_labels=original
            result['wave_session']=dict(asynchronous_initialization=asynchronous,
                initialization_ns=backend.engine.initialization_ns if backend.engine else None,
                initialization_wait_ns=backend.initialization_wait_ns)
        return result
    if lane not in ('cpu','lean'):raise ValueError('unknown candidate lane')
    config=None if lane=='cpu' else dict(backend='lean',library=str(ROOT/'research/lp-sp-pricing/target/release/libsp_batch_optimized.so'),
        sparse=sparse,steps=steps)
    return attempt(model,seconds=seconds,operations=200000000,compact_trace=True,market_backend='flow',gpu=config,batch=64 if config else 32)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('model',type=Path);p.add_argument('output',type=Path)
    p.add_argument('--lane',choices=['cpu','lean','wave'],default='wave');p.add_argument('--steps',type=int,default=1000)
    p.add_argument('--seconds',type=float,default=10);p.add_argument('--dense',action='store_true');p.add_argument('--synchronous-init',action='store_true')
    a=p.parse_args();result=run(json.loads(a.model.read_text()),a.lane,a.steps,not a.dense,not a.synchronous_init,a.seconds)
    result['model_sha256']=hashlib.sha256(a.model.read_bytes()).hexdigest()
    with a.output.open('x') as stream:json.dump(result,stream,sort_keys=True,allow_nan=False);stream.write('\n')
    print(json.dumps({k:result[k] for k in ['status','complete_ns','audit']}),flush=True)
    raise SystemExit(int(result['status']=='implementation_error'))
