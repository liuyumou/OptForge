"""Conservative disposition of one lost process tree; never reconstruct a pass."""
import fcntl
import os
from pathlib import Path
import subprocess
import time
from lp_general_common import BASE, ROOT, DEVICE, load, put, ref, require
from lp_confirmation2_supervisor import identity, same_process


def run():
    name='development-extended-v1-m17'
    prefix=BASE/'resources'/name
    reservation=Path(str(prefix)+'.reservation.json')
    journal=Path(str(prefix)+'.cpu-journal.json')
    r,j=load(reservation),load(journal)
    require(not Path(str(prefix)+'.resource.json').exists(),'supervisor receipt exists; use its actual result')
    require(not Path(str(prefix)+'.settlement.json').exists(),'already disposed')
    active=j['active'];require(active is not None,'active source-bound journal missing')
    require(all(not same_process(active[k]) for k in ['guardian','coordinator','entry']), 'recorded process still exists')
    locks=[]
    try:
        for path in [BASE/'budget.lock',BASE/'cpu.lock',Path('/tmp/ai-optimizer-gpu.lock')]:
            f=path.open('a+b');locks.append(f);fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB)
        sessions={active[k]['sid'] for k in ['guardian','coordinator','entry']}
        processes=[]
        for p in Path('/proc').iterdir():
            if not p.name.isdigit():continue
            try:
                item=identity(int(p.name))
                if item['sid'] in sessions:processes.append(item)
            except (FileNotFoundError,ProcessLookupError):pass
        require(not processes,'old process session still exists')
        device=subprocess.check_output(['nvidia-smi','-i',DEVICE,'--query-compute-apps=pid,process_name,used_memory','--format=csv,noheader'],text=True)
        require(not device.strip(),'device still has compute processes')
        observed=time.monotonic_ns()
        # No final receipt survives. Charge the whole interval through this
        # observed-empty boundary, even though the actual exit was earlier.
        elapsed=observed-active['started_ns']
        require(elapsed>0,'monotonic clock changed')
        cpu=max(r['cpu_ns'],4*elapsed);gpu=max(r['gpu_ns'],elapsed)
        out=BASE/'interruptions'/name
        out.mkdir(parents=True,exist_ok=False)
        evidence=[]
        for directory in [BASE/'development-extended-v1/m17',BASE/'sources'/name]:
            evidence.extend(ref(p) for p in sorted(directory.rglob('*')) if p.is_file())
        evidence.extend(ref(p) for p in sorted((BASE/'resources').glob(name+'*')) if p.is_file())
        disposition=out/'disposition.json'
        put(disposition,dict(kind='missing-supervisor-receipt-disposition',reservation=ref(reservation),
            journal=ref(journal),original_evidence=evidence,observed_monotonic_ns=observed,
            observation_wall_time_ns=time.time_ns(),recorded_processes_gone=True,
            old_session_processes=processes,device_process_query=device,all_three_locks_acquired=True,
            cleanup_observed_empty=True,historical_supervision_established=False,campaign_stopped=True,
            charged_cpu_ns=cpu,charged_gpu_ns=gpu,
            cause='unknown; the original command session is no longer available and no final supervisor receipt survived',
            permitted='CPU implementation, acceptance, reporting and cleanup only; new GPU/scientific work requires operational readmission',
            scientific='No existing cell retry. Retain partial outputs; timings without a complete resource receipt are ineligible.'))
        put(Path(str(prefix)+'.settlement.json'),dict(phase=r['phase'],gpu=True,cpu_ns=cpu,gpu_ns=gpu,
            status='refused',overrun=cpu>r['cpu_ns'] or gpu>r['gpu_ns'],resource=None,
            interruption_disposition=ref(disposition),queue_ns=None,
            charge_scope='conservative start-to-observed-empty interval; no historical resource enclosure'))
        print(dict(status='refused',charged_cpu_seconds=cpu/1e9,charged_gpu_seconds=gpu/1e9,
                   cleanup_observed_empty=True,campaign_stopped=True),flush=True)
    finally:
        for f in locks:f.close()


if __name__=='__main__':run()
