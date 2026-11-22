"""Run only the separately frozen unattempted COPT capacity stages."""
import subprocess
from lp_billion_common import BASE,ROOT,require
from lp_billion_prepare_continue import job
from lp_billion_idle import Nvml
PYTHON=ROOT/'artifacts/gpup-copt-adapter-env/venv/bin/python'
def main():
    sensor=Nvml()
    try:
        job('copt-tail-contracts-v1',90,['bash','-c','set -e\n'+str(PYTHON)+' -B -m unittest discover -s tests/integration -p \"test_lp_billion*.py\"\n'+str(PYTHON)+' -B tools/lp_billion_full_audit_admit.py'])
        for tag in ['64m','256m','512m']:
            job('copt-tail-freeze-'+tag+'-v1',45,[str(PYTHON),'-B','tools/lp_billion_copt_tail.py','freeze','--tag',tag],phase='reporting',host=8)
            p=subprocess.run([str(PYTHON),'-B','tools/lp_billion_copt_tail.py','execute','--tag',tag])
            require(p.returncode==0,'capacity stage stopped with retained evidence')
    finally:sensor.close()
if __name__=='__main__':main()
