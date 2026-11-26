"""Once-only final study; exact immutable reservation identities per group."""
import subprocess
from lp_sp_pricing_budget import ROOT,BASE,binding,put
from lp_sp_pricing_baselines import PYTHON
from lp_sp_pricing_final_study import frozen,STUDY
OUT=BASE/'final-driver-v1'

def run():
    frozen();OUT.mkdir(exist_ok=False);groups=[dict(kind='gpu',identity='final-focus-gpu-v1',seconds=570,gpu=True),dict(kind='control',identity='final-regression-cpu-v1',seconds=300,gpu=False),dict(kind='cpu',identity='final-vendor-cpu-v1',seconds=1800,gpu=False)]
    put(OUT/'plan.json',dict(source=binding(__file__),freeze=binding(STUDY/'freeze.json'),groups=groups,policy='Fresh cells once, preserve every failure/full charge, stop on any supervision failure. No monitoring or jobs remain after completion.'))
    for group in groups:
        identity=group['identity']
        if (BASE/'resources'/f'{identity}.reservation.json').exists():raise RuntimeError('attempted reservation')
        cmd=[str(PYTHON),'-B',str(ROOT/'tools/lp_sp_pricing_final_budget.py'),'--id',identity,'--phase','confirmation','--seconds',str(group['seconds']),'--host-gib','32']
        if group['gpu']:cmd.append('--gpu')
        cmd+=['--',str(PYTHON),'-B',str(ROOT/'tools/lp_sp_pricing_recovery_exit.py'),'--receipt',str(OUT/(identity+'.exit.json')),'--',str(PYTHON),'-B',str(ROOT/'tools/lp_sp_pricing_final_study.py'),'group','--kind',group['kind']]
        put(OUT/(identity+'.started.json'),dict(command=cmd));code=subprocess.call(cmd,cwd=ROOT);receipt=BASE/'resources'/f'{identity}.settlement.json';put(OUT/(identity+'.completed.json'),dict(returncode=code,settlement=binding(receipt) if receipt.exists() else None))
        if code:put(OUT/'stopped.json',dict(identity=identity,returncode=code));return 1
    put(OUT/'completed.json',dict(status='all_90_slots_disposed'));return 0

if __name__=='__main__':raise SystemExit(run())
