"""Wait for the owned frozen cohort, then finish admitted comparison/report work."""
import os,subprocess,time
from pathlib import Path
from lp_billion_common import BASE,ROOT,load,require
from lp_billion_prepare_continue import job
PYTHON=ROOT/'artifacts/gpup-copt-adapter-env/venv/bin/python'

def owned_driver():
    found=[]
    for p in Path('/proc').iterdir():
        if not p.name.isdigit():continue
        try:
            args=(p/'cmdline').read_bytes().split(b'\0')
            if args[:4]==[b'python3',b'-B',b'tools/lp_billion_large_continue.py',b'run']:
                ticks=int((p/'stat').read_text().rsplit(')',1)[1].split()[19]);found.append((int(p.name),ticks))
        except (FileNotFoundError,ProcessLookupError,PermissionError):continue
    require(len(found)==1,'one exact owned continuation driver');return found[0]

def live(identity):
    try:
        text=Path(f'/proc/{identity[0]}/stat').read_text().rsplit(')',1)[1].split()
        return int(text[19])==identity[1] and text[0]!='Z'
    except (FileNotFoundError,ProcessLookupError):return False

def main():
    completed=BASE/'full-billion-v1/completed.json';identity=owned_driver() if not completed.exists() else None
    while not completed.exists():
        require(live(identity),'owned driver ended before completing frozen billion cohort; retain results and investigate')
        resources=BASE/'resources';started=list(resources.glob('full-billion-v1*.reservation.json'))
        active=[p.name.removesuffix('.reservation.json') for p in started if not p.with_name(p.name.replace('.reservation.','.settlement.')).exists()]
        responses=len(list(BASE.glob('full-billion-v1-*/response.json')))
        print(dict(status='frozen_billion_cohort_running',responses=responses,active=active),flush=True)
        time.sleep(45)
    print(dict(status='original_frozen_billion_cohort_complete'),flush=True)
    p=subprocess.run([str(PYTHON),'-B',str(ROOT/'tools/lp_billion_copt_nopresolve_sequence.py')]);require(p.returncode==0,'separate COPT study stopped with retained evidence')
    job('full-billion-delivery-v1',120,[str(PYTHON),'-B',str(ROOT/'tools/lp_billion_full_delivery.py')],phase='reporting',host=8)
if __name__=='__main__':main()
