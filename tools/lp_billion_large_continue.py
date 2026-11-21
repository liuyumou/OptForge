"""Finish the existing stage, then the explicitly reserved 512 M development pair."""
import argparse,math,os,signal,subprocess,time
from pathlib import Path
from lp_billion_common import BASE,ROOT,put,load,ref,resolve,require,CPU_CAPS,GPU_CAPS,NS
from lp_billion_budget import accounting,run
from lp_billion_prepare_continue import job
from lp_confirmation2_supervisor import same_process
from lp_billion_idle import Nvml
PYTHON=ROOT/'artifacts/gpup-copt-adapter-env/venv/bin/python'
MANIFEST=BASE/'copt-capacity-512m-tail-v1/freeze.json'

def freeze():
    require(not MANIFEST.exists(),'fresh unattempted 512 M development freeze')
    paths=sorted(BASE.glob('models-512m-*-v1/result.json'));require(len(paths)==2,'complete 512 M pair')
    cells=[]
    for i,p in enumerate(paths):
        m=load(p);identity=f'copt-capacity-512m-v2-{i}-copt-gpu-pdlp'
        require(not (BASE/'resources'/(identity+'.reservation.json')).exists(),'attempted capacity cell cannot repeat')
        cells.append(dict(id=identity,model=m['model'],model_result=ref(p),family=m['family'],lane='copt-gpu-pdlp',wall_seconds=120,
            seconds=600,check_seconds=300,host_gib=128,device_gib=80,memory_mb=48000.,disk_gib=3,phase='development'))
    cpu,gpu=accounting();require(cpu['development']+4800*NS<=CPU_CAPS['development']*NS,'whole 512 M development CPU reserve')
    require(gpu['development']+1200*NS<=GPU_CAPS['development']*NS,'whole 512 M development GPU reserve')
    require(cpu['reporting']+2400*NS<=CPU_CAPS['reporting']*NS,'whole 512 M final-check reserve')
    from lp_billion_copt_run import installation
    put(MANIFEST,dict(status='frozen_capacity_development_only',cells=cells,source=ref(ROOT/'tools/lp_billion_copt_tail.py'),creator=ref(__file__),
        adapter=ref(ROOT/'tools/lp_billion_copt_run.py'),installation=installation(),checker=ref(BASE/'image-v1/executor'),
        audit=ref(ROOT/'tools/lp_billion_full_audit.py'),child=ref(ROOT/'tools/lp_billion_owned_process.py'),protocol=ref(ROOT/'docs/specifications/SPEC-0046-amendment-47.md')))

def execute():
    f=load(MANIFEST);resolve(f['creator']);resolve(f['source']);resolve(f['audit'])
    sensor=Nvml()
    try:
        for i,c in enumerate(f['cells']):
            p=BASE/'resources'/(c['id']+'.reservation.json');require(not p.exists(),'never repeat attempted capacity cell')
            s=run(c['id'],'development',c['seconds'],True,[str(PYTHON),'-B',str(ROOT/'tools/lp_billion_copt_tail.py'),'worker','--manifest',str(MANIFEST),'--index',str(i)],128,80,3)
            print(dict(cell=c['id'],settlement=s),flush=True);require(s['cleanup_empty'] and not s['overrun'],'resource cleanup/overrun stops continuation')
            response=BASE/c['id']/'response.json'
            if response.exists() and load(response)['has_solution']:
                s=run(c['id']+'-full-audit','reporting',300,False,[str(PYTHON),'-B',str(ROOT/'tools/lp_billion_full_audit.py'),str(MANIFEST),str(i)],64,0,1)
                print(dict(check=c['id'],settlement=s),flush=True);require(s['status']=='passed','strict final check stopped')
        put(MANIFEST.parent/'completed.json',dict(status='all_tail_cells_attempted',freeze=ref(MANIFEST)))
    finally:sensor.close()

def main():
    marker=BASE/'copt-capacity-256m-tail-v1/completed.json'
    while not marker.exists():time.sleep(1)
    transition=load(BASE/'capacity-driver-transition-v1.json');driver=transition['driver']
    active=[p for p in (BASE/'resources').glob('*.reservation.json') if not p.with_name(p.name.replace('.reservation.json','.settlement.json')).exists()]
    require(not active,'current capacity stage must settle before driver transition')
    require(same_process(driver),'exact paused owned driver identity')
    p=Path('/proc')/str(driver['pid']);argv=(p/'cmdline').read_bytes().rstrip(b'\0').split(b'\0')
    require([a.decode() for a in argv]==driver['argv'] and (p/'stat').read_text().rsplit(')',1)[1].split()[0]=='T','same stopped outer driver')
    os.kill(driver['pid'],signal.SIGTERM);os.kill(driver['pid'],signal.SIGCONT)
    for _ in range(50):
        if not same_process(driver):break
        time.sleep(.1)
    require(not same_process(driver),'owned idle driver ended')
    put(BASE/'capacity-driver-transition-v1-complete.json',dict(status='completed',prior=ref(BASE/'capacity-driver-transition-v1.json'),completed_stage=ref(marker),no_scientific_job_interrupted=True))
    job('copt-development-freeze-512m-v1',90,[str(PYTHON),'-B',__file__,'freeze'],phase='reporting',host=8)
    execute()
    p=subprocess.run([str(PYTHON),'-B',str(ROOT/'tools/lp_billion_full_continue.py')]);require(p.returncode==0,'full scientific continuation stopped with retained evidence')
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['run','freeze'],default='run',nargs='?');a=p.parse_args();freeze() if a.action=='freeze' else main()
