"""Run the separately identified COPT variant only after the frozen billion cohort."""
import subprocess
from lp_billion_common import BASE,ROOT,load,require
from lp_billion_budget import run
from lp_billion_prepare_continue import job
PYTHON=ROOT/'artifacts/gpup-copt-adapter-env/venv/bin/python'
DRIVER=ROOT/'tools/lp_billion_copt_nopresolve_continue.py'
def main():
    require((BASE/'full-billion-v1/completed.json').exists(),'finish the already frozen billion cohort first')
    job('copt-nopresolve-contracts-v1',90,[str(PYTHON),'-B','-m','unittest','discover','-s','tests/integration','-p','test_lp_billion_copt_nopresolve.py'],phase='admission',host=8)
    identity='copt-nopresolve-admission-v1'
    s=run(identity,'admission',450,True,[str(PYTHON),'-B',str(DRIVER),'admission_worker'],8,8,2)
    print(dict(job=identity,settlement=s),flush=True);require(s['status']=='passed','variant admission retained; no retry')
    for tag in ['64m','256m','512m']:
        job('copt-nopresolve-freeze-'+tag+'-v1',30,[str(PYTHON),'-B',str(DRIVER),'freeze','--tag',tag],phase='reporting',host=8)
        p=subprocess.run([str(PYTHON),'-B',str(DRIVER),'execute','--tag',tag]);require(p.returncode==0,'separate capacity stage stopped')
    job('copt-nopresolve-capacity-v1',30,[str(PYTHON),'-B',str(DRIVER),'capacity'],phase='reporting',host=8)
    job('copt-nopresolve-freeze-1b-v1',30,[str(PYTHON),'-B',str(DRIVER),'freeze','--tag','1b'],phase='reporting',host=8)
    p=subprocess.run([str(PYTHON),'-B',str(DRIVER),'execute','--tag','1b']);require(p.returncode==0,'separate billion stage stopped')
if __name__=='__main__':main()
