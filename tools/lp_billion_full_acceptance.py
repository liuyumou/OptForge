"""Bind passing tests to the exact full-run sources and complete capacity roster."""
import subprocess,sys
from lp_billion_common import BASE,ROOT,put,load,ref,resolve,require,disk_bytes
from lp_billion_budget import accounting
from lp_billion_full_run import candidates,FAMILIES

def main():
    gate=BASE/'resources/copt-tail-contracts-v1.settlement.json';s=load(gate)
    require(s['status']=='passed' and not s['overrun'] and s['cleanup_empty'],'full-run contracts passed')
    reservation=load(gate.with_name('copt-tail-contracts-v1.reservation.json'))
    sources=load(resolve(reservation['source_manifest']))['sources'];bound=[]
    names={'tools/lp_billion_full_audit.py','tools/lp_billion_owned_process.py',
        'tests/integration/test_lp_billion_full_audit.py',
        'tests/integration/test_lp_billion_owned_process.py'}
    for item in sources:
        if item['original']['path'] in names:resolve(item['original']);bound.append(item['original'])
    require(len(bound)==len(names),'tested exact audit/owned-process sources')
    tested=subprocess.run([sys.executable,'-B','-m','unittest','discover','-s',str(ROOT/'tests/integration'),'-p','test_lp_billion_full*.py'])
    require(tested.returncode==0,'fresh full-run budget and roster tests')
    tested=subprocess.run([sys.executable,'-B',str(ROOT/'tools/lp_billion_full_audit_admit_v2.py')]);require(tested.returncode==0,'actual deadline-aware strict checker replay')
    audit=load(BASE/'full-audit-admission-v2/result.json')
    require(audit['status']=='passed' and audit['checker_source']==ref(ROOT/'tools/lp_billion_full_audit_v2.py'),'actual strict streaming replay')
    capacity=load(BASE/'copt-capacity-readiness-v1.json')
    require(capacity['status']=='complete_capacity_dispositions','complete capacity outcomes')
    models={f:load(BASE/f'models-1b-{f}-v1/result.json') for f in FAMILIES}
    cpu,gpu=accounting();plans=candidates(models,capacity['capacity'],cpu,gpu,disk_bytes())
    fitting=[p for p in plans if not p['rejected_by']];require(fitting,'whole full-roster reservation fits')
    put(BASE/'full-run-acceptance-v1.json',dict(status='passed',source=ref(__file__),tests=ref(gate),tested_sources=bound,current_full_run=ref(ROOT/'tools/lp_billion_full_run.py'),current_full_run_tests=ref(ROOT/'tests/integration/test_lp_billion_full_run.py'),
        audit=ref(BASE/'full-audit-admission-v2/result.json'),capacity=ref(BASE/'copt-capacity-readiness-v1.json'),
        proposed_iterations=fitting[-1]['iterations'],supported=sum(c['status']=='pending' for c in fitting[-1]['cells']),
        candidates=[{k:v for k,v in p.items() if k!='cells'} for p in plans]))
    print(dict(status='passed',iterations=fitting[-1]['iterations'],supported=sum(c['status']=='pending' for c in fitting[-1]['cells'])),flush=True)
if __name__=='__main__':main()
