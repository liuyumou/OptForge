"""Isolated cold-process adapter for nonblocking wave initialization."""
import argparse
import hashlib
import json
from pathlib import Path
import lp_sp_pricing_wave_run as runner
from sp_pricing.gpu_wave_policy import OpportunisticWaveBackend


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('model',type=Path);p.add_argument('output',type=Path)
    p.add_argument('--steps',type=int,default=1000);p.add_argument('--seconds',type=float,default=10);a=p.parse_args()
    runner.WaveBackend=OpportunisticWaveBackend
    result=runner.run(json.loads(a.model.read_text()),'wave',steps=a.steps,seconds=a.seconds)
    result['startup_policy']='cpu_while_initializing'
    result['model_sha256']=hashlib.sha256(a.model.read_bytes()).hexdigest()
    with a.output.open('x') as stream:json.dump(result,stream,sort_keys=True,allow_nan=False);stream.write('\n')
    print(json.dumps({k:result[k] for k in ['status','complete_ns','audit']}),flush=True)
    raise SystemExit(int(result['status']=='implementation_error'))
