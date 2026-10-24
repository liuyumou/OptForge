"""Preserve frozen bytes while isolating exact historical EOF whitespace."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys

import lp_cpu_admission as supervisor
import lp_tensor_expanded_authority as a
import lp_tensor_expanded_study as s
import lp_tensor_expanded_delivery as previous

BASE=a.BASE/'recovery-hygiene-v1'
JOURNAL=BASE/'cpu-journal-v20.json'
PATHS=['cuda/lp_pdhg_tensor_expanded/expanded_compact_helpers.h',
       'docs/benchmarks/lp-tensor-warp32-deadline-recovery-gpup8.md',
       'docs/benchmarks/lp-tensor-warp32-inventory-admission-gpup8.md',
       'docs/benchmarks/lp-tensor-warp32-inventory-device-gpup8.md']

def initialize():
    s.frozen();j=a.read(previous.JOURNAL)
    a.require(j['failed'] and j['active'] is None and j['scientific_closed'],'delivery stop missing')
    log=(previous.BASE/'diff.stdout').read_text().splitlines()
    expected=[p+':'+str(len((a.ROOT/p).read_text().splitlines()))+': new blank line at EOF.' for p in PATHS]
    a.require(log==expected,'refusal includes other diff errors')
    sources=[]
    for p in PATHS:
        path=a.ROOT/p;a.require(path.read_bytes().endswith(b'\n\n'),'EOF exception differs');sources.append(a.ref(path))
    auth=a.DATA/'recovery-hygiene-authorization-v1.json'
    a.put(auth,dict(status='accepted',authorization='User explicitly permits harness adjustments and unused-budget reallocation; original records must remain exact.',
        prior_journal=a.ref(previous.JOURNAL),prior_diff=a.ref(previous.BASE/'diff.stdout'),
        transfer=dict(source='delivery_report',target='delivery_hygiene',cpu_seconds=120),
        unchanged_frozen_files=sources,exception='Only blank-at-eof for these four exact hash-bound files; all other whitespace checks remain active.',
        numerical_criteria_changed=False,passed_documentation_check_reused=a.ref(previous.BASE/'docs.stdout')))
    entry=j['stages']['delivery_report'];a.require(entry['cap_cpu_ns']-entry['charged_cpu_ns']>=120*a.NS,'unused delivery funds exhausted')
    entry['cap_cpu_ns']-=120*a.NS;j['stages']['delivery_hygiene']=dict(cap_cpu_ns=120*a.NS,charged_cpu_ns=0)
    j.update(identity='gpup-tensor-expanded-delivery-hygiene-journal-v20',failed=False,prior_stage_journal=a.ref(previous.JOURNAL),continuation_authorization=a.ref(auth))
    a.put(JOURNAL,j)

def checks():
    s.frozen();previous.cleanup_receipts(a.read(JOURNAL))
    auth=a.read(a.DATA/'recovery-hygiene-authorization-v1.json')
    for item in auth['unchanged_frozen_files']:a.checked(item)
    commands=[('remaining',['git','diff','--cached','--check','--','.',*[':(exclude)'+p for p in PATHS]]),
        ('preserved',['git','-c','core.whitespace=-blank-at-eof','diff','--cached','--check','--',*PATHS])]
    receipts=[]
    for name,cmd in commands:
        p=subprocess.run(cmd,cwd=a.ROOT,capture_output=True,text=True,timeout=10)
        (BASE/(name+'.stdout')).write_text(p.stdout);(BASE/(name+'.stderr')).write_text(p.stderr)
        a.require(p.returncode==0,'unexcepted diff error: '+p.stdout+p.stderr)
        receipts.append(dict(command=cmd,stdout=a.ref(BASE/(name+'.stdout')),stderr=a.ref(BASE/(name+'.stderr'))))
    a.put(a.DATA/'recovery-delivery-checks-v2.json',dict(status='passed',historical_preservation=True,
        documentation_reused=a.ref(previous.BASE/'docs.stdout'),pages=173,
        exact_EOF_exceptions=auth['unchanged_frozen_files'],diff=receipts,
        original_failed_diff_retained=auth['prior_diff'],numerical_checks_rerun=False,profiles_rerun=False))

def run():
    j=a.read(JOURNAL);stage='delivery_hygiene';out=BASE/'resource-v1.json'
    a.require(not j['failed'] and j['active'] is None and j['delivery_only'] and stage not in j['stage_attempts'],'duplicate/invalid hygiene stage')
    j['stage_attempts'][stage]=dict(output=str(out.relative_to(a.ROOT)),reserved_cpu_ns=120*a.NS);supervisor.atomic_json(JOURNAL,j)
    r=supervisor.run(dict(stage=stage,reserve_cpu_seconds=120,output=str(out),log=str(out)+'.log',journal=str(JOURNAL),lock=str(a.ROOT/'artifacts/lp-cpu-admission.lock'),slots=4,
        declared_memory_bytes=4<<30,rss_stop_bytes=6<<30,address_space_bytes=0,sources=[str(Path(__file__))],bootstrap=False,show_log=True,max_gap_ns=100_000_000,
        command=[sys.executable,str(Path(__file__)),'checks']))
    print(json.dumps(dict(status=r['status'],charged_cpu_ns=r['charged_cpu_ns'])));return 0 if r['status']=='passed' else 1

def seal():
    j=a.read(JOURNAL);a.require(not j['failed'] and j['active'] is None,'final hygiene did not pass')
    checks=a.read(a.DATA/'recovery-delivery-checks-v2.json');a.require(checks['status']=='passed','checks missing')
    cleanup=previous.cleanup_receipts(j);s.frozen()
    a.require(sum(r['charged_cpu_ns'] for r in j['runs'])==sum(v['charged_cpu_ns'] for v in j['stages'].values()),'CPU charge reconciliation differs')
    total=j['prior_cpu_ns']+sum(v['charged_cpu_ns'] for v in j['stages'].values())
    a.require(total<=j['ceiling_cpu_ns'] and j['stages']['timings']['charged_cpu_ns']==0 and j['stages']['margin']['charged_cpu_ns']==0,'final resource bound differs')
    j.update(identity='gpup-tensor-expanded-recovery-final-journal-v21',failed=True,scientific_closed=True,delivery_complete=True,
        closed_reason='Large-model BF16 profile deadline refusal; software/device acceptance passed; final CPU-only delivery passed.',
        prior_stage_journal=a.ref(JOURNAL))
    final=BASE/'cpu-journal-final-v21.json';a.put(final,j)
    scientific=a.read(a.DATA/'recovery-result-v1.json')
    a.put(a.DATA/'recovery-final-accounting-v1.json',dict(identity='gpup-tensor-expanded-recovery-accounting-v1',status='reconciled',journal=a.ref(final),
        cpu_total_ns=total,cpu_ceiling_ns=j['ceiling_cpu_ns'],recovery_cpu_ns=total-51568693453526,
        allocated_remaining_cpu_ns=sum(v['cap_cpu_ns']-v['charged_cpu_ns'] for v in j['stages'].values()),
        unassigned_cpu_ns=j['ceiling_cpu_ns']-j['prior_cpu_ns']-sum(v['cap_cpu_ns'] for v in j['stages'].values()),
        stages=j['stages'],cleanup=cleanup,ledger=a.ref(a.LEDGER),ledger_events=len(a.ledger_events()),
        ledger_prefix=dict(events=a.PREFIX_EVENTS,sha256=a.PREFIX_SHA256),new_gpu_ns=scientific['new_gpu_ns'],
        gpup8_gpu_ns=a.authority()['prior_gpup8_gpu_ns']+scientific['new_gpu_ns'],campaign_gpu_ns=scientific['campaign_gpu_ns'],
        delivery_checks=a.ref(a.DATA/'recovery-delivery-checks-v2.json'),scientific_result=a.ref(a.DATA/'recovery-result-v1.json'),
        passed_checks_rerun=False,passed_profiles_rerun=False,commit_authorized='Applicable software/device acceptance passes; local-only research implementation, incomplete performance result.'))
    note=f'''Final delivery passes 173 documentation pages/internal links, immutable evidence\nchecks and staged diff hygiene. Four exact hash-bound EOF blank-line exceptions\npreserve historical/generated bytes; all other whitespace checks pass.\nCumulative CPU is {total/a.NS:.9f} / 77640 seconds; this recovery charges\n{(total-51568693453526)/a.NS:.9f}. Timing and restricted-margin funds remain unused.\nAll coordinator/guardian cleanup receipts are empty. Final accounting:\ndocs/benchmarks/data/tensor-expanded/recovery-final-accounting-v1.json.\nFinal journal: artifacts/gpup-tensor-expanded-v1/recovery-hygiene-v1/cpu-journal-final-v21.json.\n'''
    for name in ['AGENTS.md','state/active-task.md','state/known-failures.md','wiki/status.md']:
        p=a.ROOT/name;text=p.read_text();marker='## GPUP-8 corrected proof and device acceptance pass; profile timeout (2026-10-24)\n\n'
        a.require(marker in text,'current handoff heading missing');p.write_text(text.replace(marker,marker+note+'\n',1))
    previous.REPORT.write_text(previous.REPORT.read_text().rstrip()+'\n\n'+note)
    # Newly appended prose contains no Markdown links; assert only its exact accounting target.
    a.checked(a.ref(a.DATA/'recovery-final-accounting-v1.json'))
    a.put(a.DATA/'recovery-final-source-v1.json',dict(files=[a.ref(a.ROOT/p) for p in previous.MUTABLE]+[a.ref(previous.REPORT)],accounting=a.ref(a.DATA/'recovery-final-accounting-v1.json'),
        scientific_freeze=a.ref(s.D/'freeze.json'),report=a.ref(a.DATA/'recovery-result-v1.json')))
    print(json.dumps(dict(cpu_total_ns=total,recovery_cpu_ns=total-51568693453526,new_gpu_ns=scientific['new_gpu_ns'],ledger_events=len(a.ledger_events()))))

if __name__=='__main__':
    if sys.argv[1]=='initialize':initialize()
    elif sys.argv[1]=='checks':checks()
    elif sys.argv[1]=='run':raise SystemExit(run())
    elif sys.argv[1]=='seal':seal()
