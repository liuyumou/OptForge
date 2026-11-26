"""Once-only fresh scaled-tall comparisons and other-shape regressions."""
import subprocess
from lp_sp_pricing_budget import ROOT,BASE,binding,put
from lp_sp_pricing_baselines import PYTHON
from lp_sp_pricing_pipeline_study_v2 import frozen,STUDY
OUT=BASE/'pipeline-driver-v2'

def run():
    frozen();OUT.mkdir(exist_ok=False);groups=[dict(kind='gpu',identity='pipeline-focus-gpu-v2',seconds=120,gpu=True),dict(kind='control',identity='pipeline-regression-cpu-v2',seconds=300,gpu=False),dict(kind='cpu',identity='pipeline-vendor-cpu-v2',seconds=600,gpu=False)]
    put(OUT/'plan.json',dict(source=binding(__file__),freeze=binding(STUDY/'freeze.json'),groups=groups,policy='Fresh identities once; stop on supervision failure, retain all outcomes/charges.'))
    for g in groups:
        identity=g['identity']
        if (BASE/'resources'/f'{identity}.reservation.json').exists() or (BASE/'sources'/identity).exists():raise RuntimeError('occupied identity')
        cmd=[str(PYTHON),'-B',str(ROOT/'tools/lp_sp_pricing_pipeline_budget_v2.py'),'--id',identity,'--phase','confirmation','--seconds',str(g['seconds']),'--host-gib','32']
        if g['gpu']:cmd.append('--gpu')
        cmd+=['--',str(PYTHON),'-B',str(ROOT/'tools/lp_sp_pricing_recovery_exit.py'),'--receipt',str(OUT/(identity+'.exit.json')),'--',str(PYTHON),'-B',str(ROOT/'tools/lp_sp_pricing_pipeline_study_v2.py'),'group','--kind',g['kind']]
        put(OUT/(identity+'.started.json'),dict(command=cmd));code=subprocess.call(cmd,cwd=ROOT);receipt=BASE/'resources'/f'{identity}.settlement.json';put(OUT/(identity+'.completed.json'),dict(returncode=code,settlement=binding(receipt) if receipt.exists() else None))
        if code:put(OUT/'stopped.json',dict(identity=identity,returncode=code));return 1
    put(OUT/'completed.json',dict(status='all_54_slots_disposed'));return 0

if __name__=='__main__':raise SystemExit(run())
