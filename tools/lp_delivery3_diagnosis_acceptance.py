"""Exact historical preservation, reproducible diagnosis and separate closure."""
import argparse
import hashlib
import json
import os
import re
import subprocess
from pathlib import Path
from lp_delivery3_diagnose import diagnose, binding, OUTPUT, DATA, ROOT, require
from lp_delivery3_diagnosis_budget import BASE, CAPS, budget, NS
from lp_delivery3_common import load, put, ref

BASELINE = '1fce17e'
ALLOWED = {'AGENTS.md','state/active-task.md','state/backlog.yaml','docs/plans/gpu-lp-precision-roadmap.md'}
ACCEPTANCE = DATA/'delivery3-diagnosis-acceptance-v1.json'
ACCOUNTING = DATA/'delivery3-diagnosis-accounting-v1.json'


def publish(path, value):
    # Pending link targets are drafts, not historical acceptance evidence.
    # Preserve the draft before the one permitted pending -> final transition.
    if path.exists():
        require(load(path)=={'status':'pending'},'refusing completed receipt overwrite')
        draft=BASE/'draft-receipts'/path.name
        draft.parent.mkdir(parents=True,exist_ok=True)
        with draft.open('xb') as stream:stream.write(path.read_bytes())
        from lp_cpu_admission import atomic_json
        atomic_json(path,value)
    else:
        put(path,value)


def history():
    preserved=[]
    for item in subprocess.check_output(['git','ls-tree','-rz','--full-tree',BASELINE],cwd=ROOT).split(b'\0'):
        if not item:continue
        metadata,name=item.split(b'\t',1);mode,kind,blob=metadata.split();name=name.decode()
        if name in ALLOWED:continue
        require(kind==b'blob','historical gitlink')
        raw=os.readlink(ROOT/name).encode() if mode==b'120000' else (ROOT/name).read_bytes()
        digest=hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()
        require(digest==blob.decode(),'historical file changed: '+name)
        preserved.append(dict(path=name,git_blob=digest))
    for name in ('AGENTS.md','state/active-task.md'):
        original=subprocess.check_output(['git','show',BASELINE+':'+name],cwd=ROOT).decode().split('\n\n',1)[1]
        require((ROOT/name).read_text().endswith(original),'older handoff changed: '+name)
    def tasks(value):
        points=list(re.finditer(r'^  - id: (\S+)\s*$',value,re.M))
        return {point.group(1):value[point.start():points[i+1].start() if i+1<len(points) else len(value)] for i,point in enumerate(points)}
    old=tasks(subprocess.check_output(['git','show',BASELINE+':state/backlog.yaml'],cwd=ROOT).decode())
    now=tasks((ROOT/'state/backlog.yaml').read_text())
    require(set(now)==set(old)|{'GPUP-DELIVERY4'},'unexpected task roster')
    for name in old:require(old[name]==now[name],'historical task changed: '+name)
    require('next_ready_task: GPUP-DELIVERY4\n' in (ROOT/'state/backlog.yaml').read_text(),'next task differs')
    # The retained backlog uses a deliberately narrow one-line list format.
    # Reject other syntax instead of requiring an undeclared YAML dependency.
    tasks_by_id={}
    for name,body in now.items():
        status=re.search(r'^    status: (\S+)\s*$',body,re.M)
        dependencies=re.search(r'^    depends_on: \[([^]\n]*)\]\s*$',body,re.M)
        require(status is not None and dependencies is not None,'unsupported task metadata')
        parents=[value.strip() for value in dependencies.group(1).split(',') if value.strip()]
        tasks_by_id[name]=dict(status=status.group(1),depends_on=parents)
    visited=set()
    def visit(name, active):
        require(name in tasks_by_id and name not in active,'missing dependency or cycle')
        if name in visited:return
        for parent in tasks_by_id[name].get('depends_on',[]):visit(parent,active|{name})
        visited.add(name)
    for name in tasks_by_id:visit(name,set())
    next_task=tasks_by_id['GPUP-DELIVERY4']
    require(next_task['status']=='ready' and all(tasks_by_id[d]['status']=='complete' for d in next_task['depends_on']),'next task not ready')
    return dict(baseline=BASELINE,preserved=preserved,allowed=sorted(ALLOWED),older_handoffs_exact=True,all_prior_backlog_tasks_exact=True,dependency_tasks=len(visited),next_task_ready=True)


def verify():
    require(diagnose()==load(OUTPUT),'diagnosis does not reproduce exactly')
    h=history()
    launcher=load(BASE/'resources/native-gate-v1.settlement.json')
    tail=load(BASE/'resources/native-tail-v1.settlement.json')
    native_log=(BASE/'resources/native-gate-v1.resource.json.log').read_text()
    require(launcher['status']=='refused' and tail['status']=='passed','composite gate receipts missing')
    require('Ran 669 tests' in native_log and '\nOK\n' in native_log
            and 'committed run records re-executed and verified: passed' in native_log
            and 'broken link docs/benchmarks/lp-delivery3-diagnosis.md' in native_log,'launcher failure boundary changed')
    rust_prefix=native_log.split('advisories ok',1)[0]
    rust_count=sum(int(n) for n in re.findall(r'test result: ok\. (\d+) passed;',rust_prefix))
    require(rust_count==637,'workspace Rust coverage changed')
    rust_total=sum(int(n) for n in re.findall(r'test result: ok\. (\d+) passed;',native_log))
    require(rust_total==638 and 'lp_external_baseline_buffered' in native_log,'buffered transport Rust coverage changed')
    for command in (['python3','tools/validate_artifacts.py'],['python3','tools/build_docs.py'],['git','diff','--check']):
        subprocess.run(command,cwd=ROOT,check=True)
    history_path=DATA/'delivery3-diagnosis-history-v1.json'
    if history_path.exists():require(load(history_path)==h,'historical verification changed')
    else:put(history_path,h)
    publish(ACCEPTANCE,dict(status='passed',analysis=binding(OUTPUT),history=binding(DATA/'delivery3-diagnosis-history-v1.json'),
        native_gate=ref(BASE/'resources/native-gate-v1.settlement.json'),
        native_gate_status='failed_at_documentation',native_tail=ref(BASE/'resources/native-tail-v1.settlement.json'),
        composite_full_coverage=True,
        workspace_rust_tests=rust_count,total_rust_tests=rust_total,buffered_transport_rust_tests=1,python_tests=669,new_python_tests=6,
        historical_files=len(h['preserved']),reproduces_exactly=True,primary_decisions_unchanged=True,
        no_new_scientific_solver_checker_or_device_run=True))
    print(dict(status='passed',historical_files=len(h['preserved'])),flush=True)


def close():
    budget.admission_open(BASE)
    require(load(ACCEPTANCE)['status']=='passed','acceptance required')
    require(load(BASE/'resources/final-acceptance-v4.settlement.json')['status']=='passed','final acceptance settlement required')
    cpu,gpu=budget.accounting(BASE);cpu['cleanup']+=128*NS
    require(all(cpu[k]<=v*NS for k,v in CAPS.items()) and not gpu,'allocation exceeded')
    receipts=[]
    for path in sorted((BASE/'resources').glob('*.settlement.json')):
        settlement=load(path);require(not settlement['overrun'],'overrun')
        report=load(ROOT/settlement['resource']['path'])
        require(report['guardian_cleanup']['empty'] and report['result']['cleanup']['empty'],'cleanup incomplete')
        reservation=path.with_name(path.name.replace('.settlement.json','.reservation.json'))
        request=path.with_name(path.name.replace('.settlement.json','.request.json'))
        receipts.append(dict(binding=ref(path),settlement=settlement,resource=report,
            reservation=load(reservation),request=load(request),
            log=(BASE/'resources'/path.name.replace('.settlement.json','.resource.json.log')).read_text()))
    sources={}
    for path in sorted((BASE/'diagnosis-sources').rglob('*')):
        if path.is_file():sources[str(path.relative_to(BASE))]=path.read_text()
    for path in sorted((BASE/'failed-link-source-v1').rglob('*')):
        if path.is_file():sources[str(path.relative_to(BASE))]=path.read_text()
    for name in ('native-tail-v1.sh','inspect.py'):
        sources[name]=(BASE/name).read_text()
    value=dict(status='closed',cpu_caps_seconds=CAPS,cpu_ns=cpu,cpu_seconds=sum(cpu.values())/NS,
        gpu_seconds=0,preparation_cpu_seconds=512,closing_administration_cpu_seconds=128,
        failed_jobs=sum(r['settlement']['status']!='passed' for r in receipts),
        historical_transfers=0,cleanup_empty=True,receipts=receipts,development_sources=sources)
    publish(ACCOUNTING,value);put(BASE/'CLOSED.json',dict(accounting=ref(ACCOUNTING)))
    print(dict(status='closed',cpu_seconds=value['cpu_seconds'],gpu_seconds=0,failed_jobs=value['failed_jobs']),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['verify','close']);a=p.parse_args();globals()[a.action]()
