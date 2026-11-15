"""Ordered campaign driver. Completed jobs may be skipped; refused jobs never retried."""
import argparse
import os
import subprocess
import sys
from lp_gpup9_common import BASE, ROOT, load, require


def job(identity,phase,seconds,command,gpu=False,native=False):
    prior=BASE/'resources'/(identity+'.reservation.json')
    if prior.exists():
        settlement=load(BASE/'resources'/(identity+'.settlement.json'))
        require(settlement['status']=='passed' and not settlement['overrun'],'refused or unsettled job cannot be retried')
        return
    placement='lp_mixed2_confirm_native_place.py' if native else 'lp_mixed2_reuse_place.py'
    args=[sys.executable,'tools/lp_gpup9_budget.py','--id',identity,'--phase',phase,'--seconds',str(seconds)]
    if gpu:args+=['--gpu']
    args+=['--',sys.executable,'tools/'+placement]+command
    subprocess.run(args,cwd=ROOT,check=True)


def python(tool,*args):return [sys.executable,'tools/lp_gpup9_'+tool+'.py',*args]


def admission():
    job('contracts-v4','implementation',300,[sys.executable,'-m','unittest','discover','-s','tests/integration','-p','test_lp_gpup9.py'],native=True)
    job('isolated-v1','acceptance',900,['bash','tools/check_checker2_cpu.sh'],native=True)
    job('cpu-v1','acceptance',600,python('admit','cpu'))
    job('historical-v1','implementation',120,python('evidence','historical'))
    job('design-v2','implementation',60,python('protocol','design'))
    job('projection-v1','implementation',300,[sys.executable,'-m','unittest','discover','-s','tests/integration','-p','test_lp_gpup9.py'],native=True)
    job('freeze-contracts-v1','implementation',300,[sys.executable,'-m','unittest','discover','-s','tests/integration','-p','test_lp_gpup9.py'],native=True)
    job('implementation-v5','implementation',60,python('protocol','implementation'))
    job('models-admission-v2','implementation',600,python('models','admission'))
    job('device-v1','acceptance',300,python('admit','device'),gpu=True)
    job('pilot-v3','acceptance',600,python('study','pilot'),gpu=True)
    job('serial-admission-v2','acceptance',600,python('serial','--admission'))
    job('admission-finalize-v2','implementation',60,python('admit','finish'))


def study(stage):
    if stage=='holdout':
        job('freeze-holdout','implementation',300,python('protocol','freeze','--stage',stage))
        job('models-holdout-v2','implementation',600,python('models',stage))
    else:
        job('models-v2-'+stage,'implementation',600,python('models',stage))
        job('freeze-screening-v2' if stage=='screening' else 'freeze-'+stage,'implementation',300,python('protocol','freeze','--stage',stage))
    # A started scientific stage is not resumed: every missing cell stays visible.
    subprocess.run(python('study','run','--stage',stage),cwd=ROOT,check=True)
    job('analyze-'+stage,'reporting',600,python('analysis',stage))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('phase',choices=['admission','screening','validation','holdout']);a=p.parse_args()
    if a.phase=='admission':admission()
    else:study(a.phase)
