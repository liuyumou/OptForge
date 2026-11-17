"""Run a previously frozen complete development campaign without cell retries."""
import argparse
import subprocess
import sys
from lp_general_common import BASE,ROOT,load,require

def run(identity):
    manifest=load(BASE/identity/'freeze.json')
    preflight=manifest['completion_preflight'];require(preflight is not None,'complete reservation preflight required')
    indices=sorted({c['model_index'] for c in manifest['cells']})
    require(len(indices)==preflight['model_jobs'],'job coverage')
    for i in indices:
        name=f'{identity}-m{i:02d}'
        require(not (BASE/'resources'/(name+'.reservation.json')).exists(),'existing scientific reservation; never retry')
        command=[sys.executable,str(ROOT/'tools/lp_general_budget.py'),'--id',name,'--phase','development',
            '--seconds',str(preflight['seconds_per_job']),'--gpu','--',sys.executable,
            str(ROOT/'tools/lp_mixed2_reuse_place.py'),sys.executable,str(ROOT/'tools/lp_general_development.py'),
            'run','--id',identity,'--index',str(i)]
        p=subprocess.run(command)
        require(p.returncode==0,'campaign stopped; retained failed job is not retried')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--id',required=True);run(p.parse_args().id)
