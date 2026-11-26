"""Readmit the local exit-race fix and finish only interrupted sanitizer work."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
from lp_sp_pricing_budget import BASE,ROOT,binding,put
from lp_sp_pricing_wave_quality import sources


def cpu():
    out=BASE/'wave-guard-cpu-v1';out.mkdir(exist_ok=False)
    subprocess.run([sys.executable,'-B','-m','unittest','discover','-s','tests/integration','-p','test_lp_sp_pricing*.py'],check=True)
    put(out/'result.json',dict(status='passed',sources=[binding(ROOT/p) for p in [
        'tools/lp_sp_pricing_guard.py','tests/integration/test_lp_sp_pricing_wave_guard.py']],
        shared_resource_sources_unchanged=True,retained_failure=binding(BASE/'resources/wave-gpu-admit-v1.settlement.json')))


def resume(identity):
    prior=BASE/'wave-gpu-admit-v1';out=BASE/identity;out.mkdir(exist_ok=False)
    receipt=json.loads((BASE/'resources/wave-gpu-admit-v1.settlement.json').read_text())
    if receipt['status']!='refused' or receipt['overrun'] or not receipt['cleanup_empty']:
        raise RuntimeError('preceding failure is not settled with empty cleanup')
    if json.loads((prior/'quality.json').read_text())['sources']!=sources():raise RuntimeError('numerical quality binding changed')
    if 'ERROR SUMMARY: 0 errors' not in (prior/'memcheck.log').read_text():raise RuntimeError('retained memcheck incomplete')
    cpu_path=BASE/'wave-cpu-admit-v2/result.json'
    if json.loads(cpu_path.read_text())['sources']!=sources():raise RuntimeError('CPU numerical admission changed')
    evidence=[binding(cpu_path),binding(prior/'quality.json'),binding(prior/'memcheck.json'),binding(prior/'memcheck.log'),
        binding(BASE/'resources/wave-gpu-admit-v1.settlement.json'),binding(BASE/'wave-guard-cpu-v1/result.json')]
    for name in ['racecheck','initcheck','synccheck']:
        cmd=['/usr/local/cuda/bin/compute-sanitizer','--tool',name,'--target-processes','all','--error-exitcode','91',
             sys.executable,'-B',str(ROOT/'tools/lp_sp_pricing_wave_quality.py'),'quality',str(out/(name+'.json')),'--smoke']
        with (out/(name+'.log')).open('x') as stream:subprocess.run(cmd,stdout=stream,stderr=subprocess.STDOUT,check=True)
        evidence.extend([binding(out/(name+'.json')),binding(out/(name+'.log'))])
    model=dict(A=[[1,1],[-1,0],[0,-1]],b=[2,0,0],c=[1,1]);put(out/'model.json',model)
    with (out/'cold.log').open('x') as stream:
        subprocess.run([sys.executable,'-B',str(ROOT/'tools/lp_sp_pricing_wave_run.py'),str(out/'model.json'),
            str(out/'response.json')],stdout=stream,stderr=subprocess.STDOUT,check=True)
    from lp_sp_pricing_verify import verify
    if not verify(model,json.loads((out/'response.json').read_text()))['accepted']:
        raise RuntimeError('cold asynchronous original-LP smoke failed')
    evidence.extend(binding(out/name) for name in ['model.json','response.json','cold.log'])
    put(out/'admission.json',dict(status='passed',sources=sources(),evidence=evidence,
        continuation=binding(__file__),retained_quality_and_memcheck=True))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['cpu','resume']);p.add_argument('identity',nargs='?');a=p.parse_args()
    if a.action=='cpu':cpu()
    else:resume(a.identity)
