"""Source-bound larger-scale candidate with validated certificate buffers."""
import argparse
from pathlib import Path
from unittest.mock import patch
from lp_sp_pricing_geometry_run import run
from sp_pricing import geometry_fast
from sp_pricing.certificate_guard import guarded_certificate

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('model',type=Path);p.add_argument('output',type=Path)
    p.add_argument('--seconds',type=float,default=120);p.add_argument('--cpu',action='store_true');a=p.parse_args()
    with patch.object(geometry_fast,'exact_certificate',guarded_certificate):
        failed=run(a.model,a.output,a.seconds,not a.cpu)
    raise SystemExit(int(failed))
