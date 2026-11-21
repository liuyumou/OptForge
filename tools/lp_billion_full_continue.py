"""Freeze and complete the full billion roster after capacity dispositions."""
import subprocess
from lp_billion_common import ROOT,BASE,require
from lp_billion_prepare_continue import job
PYTHON=ROOT/'artifacts/gpup-copt-adapter-env/venv/bin/python'
def main():
    job('copt-capacity-readiness-v1',90,['bash','-c','set -e\n'+str(PYTHON)+' -B -m unittest discover -s tests/integration -p \"test_lp_billion_copt_readiness.py\"\n'+str(PYTHON)+' -B tools/lp_billion_copt_readiness.py'],phase='reporting',host=8)
    job('full-run-contracts-v1',90,[str(PYTHON),'-B','tools/lp_billion_full_acceptance.py'],phase='reporting',host=8)
    job('full-billion-freeze-v1',90,[str(PYTHON),'-B','tools/lp_billion_full_run.py','freeze'],phase='reporting',host=8)
    p=subprocess.run([str(PYTHON),'-B','tools/lp_billion_full_run.py','execute']);require(p.returncode==0,'full run stopped with retained evidence')
if __name__=='__main__':main()
