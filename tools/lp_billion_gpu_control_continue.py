"""Admit and measure the GPU assessment/control without repeating attempted cells."""
import argparse
from lp_billion_common import BASE,ROOT,load,ref,require,CPU_CAPS,GPU_CAPS,NS
from lp_billion_budget import accounting
from lp_billion_prepare_continue import job,completed
PYTHON=ROOT/'artifacts/gpup-copt-adapter-env/venv/bin/python'

def admit():
    require(completed('gpu-control-quality-v3'),'complete native candidate acceptance')
    stages=[('gpu',240,None,16),('memcheck',240,'memcheck',16),('racecheck',600,'racecheck',64),('initcheck',240,'initcheck',16),('synccheck',240,'synccheck',16)]
    cpu,gpu=accounting();pending=[s for s in stages if not (BASE/'resources'/f'gpu-control-{s[0]}-v1.reservation.json').exists()]
    reserve=sum(s[1] for s in pending)
    require(cpu['admission']+(4*reserve+600)*NS<=CPU_CAPS['admission']*NS and gpu['admission']+reserve*NS<=GPU_CAPS['admission']*NS,'whole candidate CPU/GPU admission reservation')
    job('gpu-control-contracts-v1',120,[str(PYTHON),'-B','-m','unittest','discover','-s','tests/integration','-p','test_lp_billion*.py'])
    job('gpu-control-seal-v1',60,[str(PYTHON),'-B',str(ROOT/'tools/lp_mixed2_reuse_place.py'),str(PYTHON),'-B',str(ROOT/'tools/lp_billion_gpu_control_build.py'),'seal','--id','gpu-control-quality-v3'])
    for tag,seconds,sanitizer,host in stages:
        identity='gpu-control-'+tag+'-v1';cmd=[str(PYTHON),'-B',str(ROOT/'tools/lp_billion_gpu_control_admit.py'),'--id',identity]
        if sanitizer:cmd+=['--sanitizer',sanitizer]
        job(identity,seconds,cmd,gpu=True,host=host)

def measure():
    for scale in ['64m','1b']:
        manifest=BASE/f'gpu-control-{scale}-v1/freeze.json'
        if not manifest.exists():
            job('gpu-control-freeze-'+scale+'-v1',60,[str(PYTHON),'-B',str(ROOT/'tools/lp_mixed2_reuse_place.py'),str(PYTHON),'-B',str(ROOT/'tools/lp_billion_gpu_control_campaign.py'),'freeze','--scale',scale],phase='reporting',host=8)
        from lp_billion_gpu_control_campaign import execute
        if not (manifest.parent/'completed.json').exists():execute(manifest)
        job('gpu-control-report-'+scale+'-v1',120,[str(PYTHON),'-B',str(ROOT/'tools/lp_mixed2_reuse_place.py'),str(PYTHON),'-B',str(ROOT/'tools/lp_billion_gpu_control_report.py'),'report','--scale',scale],phase='reporting',host=8)
    job('gpu-control-delivery-v1',120,[str(PYTHON),'-B',str(ROOT/'tools/lp_mixed2_reuse_place.py'),str(PYTHON),'-B',str(ROOT/'tools/lp_billion_gpu_control_report.py'),'deliver'],phase='reporting',host=8)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['admit','measure']);a=p.parse_args();globals()[a.action]()
