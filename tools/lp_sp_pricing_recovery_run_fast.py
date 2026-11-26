"""Final candidate: unchanged old success paths and efficient CPU/GPU wide proposals."""
import argparse
from pathlib import Path
from unittest.mock import patch
import lp_sp_pricing_recovery_run as original
from sp_pricing.primal_recovery_fast import row_proposal

def run(model,output,seconds=60,gpu=True,wide_backend='auto'):
    with patch.object(original,'row_proposal',row_proposal):return original.run(model,output,seconds,gpu,wide_backend)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('model',type=Path);p.add_argument('output',type=Path);p.add_argument('--seconds',type=float,default=60);p.add_argument('--cpu',action='store_true');p.add_argument('--wide-backend',choices=['auto','cpu','gpu'],default='auto');a=p.parse_args();raise SystemExit(int(run(a.model,a.output,a.seconds,not a.cpu,a.wide_backend)))
