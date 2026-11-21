"""Finish independent copy/COPT admission, then the prospectively frozen capacity ladder."""
import subprocess
from lp_billion_common import ROOT,BASE,load,require
from lp_billion_idle import Nvml
from lp_billion_prepare_continue import job,completed
from lp_billion_admit import gate_identity
PYTHON=ROOT/'artifacts/gpup-copt-adapter-env/venv/bin/python'
def main():
    for kind in ['gpu','memcheck','racecheck','initcheck','synccheck']:require(completed(gate_identity(kind,9)),'complete device gate '+kind)
    sensor=Nvml()
    try:
        job('bounded-copy-gpu-v1',60,['python3','-B','tools/lp_billion_copy_admit.py','run'],gpu=True,host=8)
        job('copt-full-admission-v2',240,[str(PYTHON),'-B','tools/lp_billion_copt_full_admit.py','--id','copt-full-admission-v2'],gpu=True,host=16)
        for tag in ['64m','256m','512m']:
            job('copt-capacity-freeze-'+tag+'-v1',45,[str(PYTHON),'-B','tools/lp_billion_copt_capacity.py','freeze','--tag',tag],phase='reporting',host=8)
            p=subprocess.run([str(PYTHON),'-B','tools/lp_billion_copt_capacity.py','execute','--tag',tag])
            require(p.returncode==0,'capacity stage stopped; retain every attempt')
    finally:sensor.close()
if __name__=='__main__':main()
