"""Prospective operational readmission; never repairs the interrupted campaign."""
import argparse
import subprocess
import sys
import unittest
from pathlib import Path
from lp_general_common import BASE, ROOT, MAX_GAP_NS, SUPERVISOR_MODULE, load, put, ref, require


def sources():
    return [ref(ROOT/'tools'/n) for n in ['lp_general_budget.py','lp_general_readmit.py','lp_general_common.py',
        'lp_confirmation2_supervisor.py','lp_confirmation_supervisor.py','lp_cpu_admission.py']]


def validate(disposition, base=BASE):
    path=base/'operational-readmission-v1.json'
    require(path.exists(),'operational readmission is missing')
    r=load(path)
    require(r['kind']=='prospective-general-operational-readmission' and r['status']=='passed','invalid readmission')
    require(disposition in r['interruptions'] and not r['historical_supervision_established'],'readmission disposition mismatch')
    require(r['sources']==sources() and r['max_gap_ns']==MAX_GAP_NS,'operational sources or bound differ')
    proof=ROOT/r['proof']['path'];settlement=ROOT/r['settlement']['path']
    require(ref(proof)==r['proof'] and ref(settlement)==r['settlement'],'readmission evidence differs')
    p,s=load(proof),load(settlement)
    require(p['status']=='passed' and p['tests']>=39 and p['skipped']==0 and p['sources']==sources(),'operational proof incomplete')
    require(s['status']=='passed' and not s['overrun'] and not s['gpu'] and s['phase']=='admission','operational probe not settled')
    resource=ROOT/s['resource']['path'];require(ref(resource)==s['resource'],'operational resource differs')
    report=load(resource)
    require(report['status']=='passed' and report['guardian_cleanup']['empty'] and report['result']['cleanup']['empty'],'operational cleanup failed')
    return ref(path)


def probe(identity):
    out=BASE/identity;out.mkdir(parents=True,exist_ok=False)
    suite=unittest.defaultTestLoader.discover(str(ROOT/'tests/integration'),pattern='test_lp_confirmation2_supervisor.py')
    with (out/'contracts.log').open('w') as log:
        result=unittest.TextTestRunner(stream=log,verbosity=2).run(suite)
    require(result.wasSuccessful() and result.testsRun>=39 and not result.skipped,'supervisor contracts failed')
    # A real multi-process CPU workload under the unchanged outer supervisor.
    jobs=[subprocess.Popen([sys.executable,'-c','import hashlib\nx=b"x"*1048576\nfor _ in range(256): hashlib.sha256(x).digest()']) for _ in range(3)]
    require(all(p.wait()==0 for p in jobs),'supervised workload failed')
    put(out/'result.json',dict(status='passed',tests=result.testsRun,skipped=len(result.skipped),sources=sources(),max_gap_ns=MAX_GAP_NS))


def compose(identity):
    proof=BASE/identity/'result.json';settlement=BASE/'resources'/(identity+'.settlement.json')
    interruptions=[load(p)['interruption_disposition'] for p in (BASE/'resources').glob('*.settlement.json') if load(p).get('interruption_disposition')]
    require(interruptions,'no interrupted disposition to readmit')
    path=BASE/'operational-readmission-v1.json';require(not path.exists(),'readmission immutable')
    put(path,dict(kind='prospective-general-operational-readmission',status='passed',interruptions=interruptions,
        historical_supervision_established=False,sources=sources(),max_gap_ns=MAX_GAP_NS,proof=ref(proof),settlement=ref(settlement),
        claim='Fresh operational contract admission only. Interruption cause unknown; no availability guarantee, historical repair, or numerical admission.'))
    for d in interruptions:validate(d)
    print('prospective operational readmission passed',flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['probe','compose']);p.add_argument('--id',required=True);a=p.parse_args()
    (probe if a.action=='probe' else compose)(a.id)
