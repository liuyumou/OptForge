"""Sequential supervised admission; a failed stage stops dependent work."""
import argparse
import subprocess
import sys
from lp_fp4_fast_common import ROOT, BASE, load, require


def main():
    p=argparse.ArgumentParser();p.add_argument('version');a=p.parse_args();v=a.version
    require(load(BASE/'resources'/('compile-'+v+'.settlement.json'))['status']=='passed','compiled image required')
    for stage,seconds in [('primitives',180),('stress',300),('transactions',180),('memcheck',180),('racecheck',300),('initcheck',180),('synccheck',180),('hardware',300)]:
        command=[sys.executable,'tools/lp_fp4_fast_budget.py','--id',stage+'-'+v,'--phase','acceptance','--seconds',str(seconds),'--gpu','--',sys.executable,'tools/lp_fp4_fast_experiment.py',stage,v,'--build',v]
        print('Starting',stage,flush=True);subprocess.run(command,cwd=ROOT,check=True)
    subprocess.run([sys.executable,'tools/lp_fp4_fast_budget.py','--id','admission-'+v,'--phase','acceptance','--seconds','60','--',sys.executable,'tools/lp_fp4_fast_admission.py',v],cwd=ROOT,check=True)

if __name__=='__main__':main()
