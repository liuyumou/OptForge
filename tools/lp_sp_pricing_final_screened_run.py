"""Final early projection with a cheap correction screen; all other paths identical."""
import argparse
from pathlib import Path
from unittest.mock import patch
import lp_sp_pricing_final_run as previous
from sp_pricing.dual_recovery_screened import build

def run(model,output,seconds=60,gpu=True,wide_backend='cpu'):
    with patch.object(previous,'build',build):return previous.run(model,output,seconds,gpu,wide_backend)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('model',type=Path);p.add_argument('output',type=Path);p.add_argument('--seconds',type=float,default=60);p.add_argument('--cpu',action='store_true');p.add_argument('--wide-backend',choices=['cpu','gpu','auto'],default='cpu');a=p.parse_args();raise SystemExit(int(run(a.model,a.output,a.seconds,not a.cpu,a.wide_backend)))
