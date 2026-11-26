"""Common postprocessor with the admitted balanced sparse correction basis."""
import argparse
from pathlib import Path
from unittest.mock import patch
import lp_sp_pricing_recovery_endpoint as original
from sp_pricing.primal_recovery_balanced import build

def prepare(model,response,output):
    with patch.object(original,'build',build):return original.prepare(model,response,output)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('model',type=Path);p.add_argument('response',type=Path);p.add_argument('output',type=Path);a=p.parse_args();prepare(a.model,a.response,a.output)
