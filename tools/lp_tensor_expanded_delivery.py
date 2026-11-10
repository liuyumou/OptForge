"""CPU-only post-stop delivery; consumes no numerical or profile attempts."""
import ast
import copy
import json
from pathlib import Path
import subprocess
import sys

import lp_cpu_admission as supervisor
import lp_tensor_expanded_authority as a
import lp_tensor_expanded_study as s

BASE=a.BASE/'recovery-delivery-v1'
JOURNAL=BASE/'cpu-journal-v19.json'
REPORT=a.ROOT/'docs/benchmarks/lp-tensor-expanded-recovery-gpup8.md'
MUTABLE=['AGENTS.md','state/active-task.md','state/known-failures.md','wiki/status.md','state/backlog.yaml','CHANGELOG.md']

def initialize():
    s.frozen();j=a.read(s.JOURNAL)
    a.require(j['active'] is None and j['failed'] and j['scientific_closed'],'scientific stop not settled')
    a.require(a.read(s.D/'acceptance.json')['status']=='passed','device acceptance missing')
    for name in MUTABLE:
        p=BASE/'prior-source'/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes((a.ROOT/name).read_bytes())
    auth=a.DATA/'recovery-delivery-authorization-v1.json'
    a.put(auth,dict(status='accepted',scope='CPU-only evidence/report/documentation/accounting after actual profile deadline refusal; no scientific retry.',
        prior_journal=a.ref(s.JOURNAL),transfers=[dict(source='reporting',target='delivery_report',seconds=488),dict(source='reporting',target='delivery_checks',seconds=200)],
        bookkeeping_cpu_seconds=32,additional_resources=0,report_work_wall_seconds=120))
    entry=j['stages']['reporting'];a.require(entry['cap_cpu_ns']-entry['charged_cpu_ns']>=720*a.NS,'delivery funds exhausted')
    entry['cap_cpu_ns']-=688*a.NS;entry['charged_cpu_ns']+=32*a.NS
    for stage,cap in [('delivery_report',488),('delivery_checks',200)]:j['stages'][stage]=dict(cap_cpu_ns=cap*a.NS,charged_cpu_ns=0)
    j['runs'].append(dict(stage='reporting',charged_cpu_ns=32*a.NS,status='conservative_final_accounting_bookkeeping',output=str(auth)))
    j.update(identity='gpup-tensor-expanded-delivery-journal-v19',failed=False,delivery_only=True,scientific_closed=True,prior_stage_journal=a.ref(s.JOURNAL),continuation_authorization=a.ref(auth))
    a.put(JOURNAL,j)
    p=a.ROOT/'state/active-task.md';first,rest=p.read_text().split('\n',1)
    p.write_text(first+'\n\n## GPUP-8 device acceptance passes; large-model profile deadline stop (2026-10-24)\n\nThe corrected proof, CPU model admission, native build and six device jobs pass.\nSix small-model profiles complete and independently verify. The first large-model\nBF16 profile reaches its unchanged 18-second worker deadline without an endpoint.\nPreserve its timeout and full 3200-CPU-second profile reservation charge; no more\nprofiles, resource admission or timings follow. Timing funds remain unused.\nCPU-only delivery uses existing reporting funds, with 488 CPU seconds for\n120 work-wall seconds of reporting and 200 for documentation/evidence checks.\nActive journal: artifacts/gpup-tensor-expanded-v1/recovery-delivery-v1/cpu-journal-v19.json.\nGPUP-8 remains incomplete and all completion criteria remain unchanged.\n\n'+rest.lstrip('\n'))

def cleanup_receipts(j):
    rows=[]
    for run in j['runs']:
        p=Path(run['output'])
        if not p.is_absolute():p=a.ROOT/p
        if not p.exists():continue
        document=a.read(p)
        if 'guardian_cleanup' not in document:continue
        a.require(document['guardian_cleanup']['empty'],'guardian descendants remain')
        result=document.get('result',{})
        if 'cleanup' in result:a.require(result['cleanup']['empty'],'coordinator descendants remain')
        rows.append(dict(receipt=a.ref(p),guardian_empty=True,coordinator_empty=result.get('cleanup',{}).get('empty')))
    return rows

def compose():
    result=s.report();a.require(result['status']=='incomplete','unexpected completion')
    failed=[a.read(p) for p in s.D.glob('*.trial.json') if a.read(p)['status']!='completed']
    a.require(len(failed)==1 and failed[0]['error']=='GPU worker failed: timeout','unexpected stop')
    key=failed[0]['id'];w=a.read(s.D/(key+'.worker.json'));a.require(w['reason']=='timeout' and not (s.D/(key+'.endpoint.json')).exists(),'timeout binding differs')
    for j in s.jobs():
        if j['kind']=='timing':a.require(not (s.D/(j['id']+'.request.json')).exists(),'timing ran after refusal')
    result.update(stop=dict(stage='profiles',reason='unchanged 18-second BF16 large-model profile deadline',trial=a.ref(s.D/(key+'.trial.json')),worker=a.ref(s.D/(key+'.worker.json')),endpoint_available=False),
        cpu_proofs=a.ref(a.DATA/'independent-proof-v2.json'),device_acceptance=a.ref(s.D/'acceptance.json'),
        completed_profiles=6,attempted_profiles=7,unexecuted_profiles=9,timings_executed=0,
        frozen_sources=a.ref(s.D/'freeze.json'),source_changes_after_observation=False,
        passed_checks_rerun=False,passed_profiles_rerun=False,completion_criteria_changed=False,
        cleanup=cleanup_receipts(a.read(JOURNAL)))
    partial=[]
    for j in s.jobs():
        ep=s.D/(j['id']+'.endpoint.json')
        if j['kind']!='profile' or not ep.exists() or j['configuration']['backend']=='cuda-lp-tuned':continue
        e=a.read(ep);first=e['outcome']['first_certified_iteration'];ph=e['phases_ns']
        partial.append(dict(configuration=j['configuration']['id'],model=j['instance']['id'],iterations=e['outcome']['core']['iterations'],first_certified_iteration=first,
            prefix_ns=ph['boundary/'+str(first)+'/execute_total'],final_assessment_ns=ph['delivery_original_assessment'],execute_ns=ph['execute_total'],endpoint=a.ref(ep)))
    result['partial_profile_observations']=partial
    dest=a.DATA/'recovery-result-v1.json';a.put(dest,result)
    old=a.authority();new=result['new_gpu_ns'];gpup=old['prior_gpup8_gpu_ns']+new
    text=f'''# GPUP-8 expanded-window recovery

The fixture correction and one corrected independent proof pass. The new expanded
state implementation passes CPU/model/native acceptance and all six device jobs.
GPUP-8 remains **incomplete**: the first large-model BF16 profile reaches its
unchanged 18-second worker deadline without an endpoint. The worker records
{w['elapsed_ns']/a.NS:.9f} seconds including termination. No numerical failure is
inferred from this timeout. No later profile, resource gate or timing is launched.

The [accepted contract](../decisions/ADR-0046-expanded-audit-window-state.md) and
[plan](../plans/lp-tensor-expanded-windows.md) remain unchanged. Expanded primal,
dual and extrapolated state stays private within audit windows. Both penultimate
vectors are canonicalized and bound to the retained FP64 reference buffers;
successful audits adopt the reference endpoint. Cross-window persistence remains
separate, unallocated future work.

## Correction and validation

The versioned generator canonicalizes operands after exponent replacement using
the independent exact-rational oracle. The original generator, rejected corpus,
5600-CPU-second failed proof charge and original reports remain exact. The corrected
proof covers 7376 scalar cases, 1400 conversions, 1400 splits, 720 component
products and 2400 projections. Rust arithmetic, window/recovery tests and all
twelve required dense 400-update CPU configurations pass. Four compiled CUDA
modules use at most 96 registers with zero spills; emitted Tensor instructions
and the new 64-bit unsigned packing are admitted.

The new device checks pass 7376 primitive cases, 112 product pairs, 20 window/
reference comparisons, four expanded-controller comparisons and a matched-FP64
controller comparison. All twelve fixed-work/replay pairs are accounted for:
ten changed pairs with twenty new independent endpoint receipts and two retained
control pairs. Memcheck, racecheck, initcheck and synccheck pass. The unchanged
ordinary suite, native product scenarios and eligible source-bound checks are
reused. No passed check/profile or endpoint verification is rerun.

The emitted-instruction reader and wrapper lint corrections retain their failed
attempts and full reservation charges. They alter no numerical result or criterion.
The separate artifact adapters pass six new receipt, budget and report-composition
checks. Original supervisor, estimator and gain-statistics bodies remain unchanged.

## Profile disposition

All six small-model profiles complete and independently verify. The five research
configurations reach 2000 updates and first certify at update 1400. Expanded
configurations take about 5.8 seconds through final assessment; their measured
certificate prefixes alone exceed 4.0 seconds, above the 0.415902600-second
small-model forecast threshold even before the required global producer tail.
These are partial observations, not a complete sixteen-profile gain forecast.

The seventh profile times out. Nine profiles and all sixty timing cells remain
unexecuted; all 76 frozen study cells remain in the report. No replacement,
favorable-tail substitution, deadline extension or numerical change follows.
No certified total-latency gain or supported preset is established; GPUP-9 remains
gated. Profiling distinguishes exclusive host-wall scopes from CUDA-event durations;
normalization inside fused kernels is included in those kernels' event durations.

## Resources and evidence

New cohort GPU charge: **{new/a.NS:.9f} / 1760 seconds**. GPUP-8 cumulative:
**{gpup/a.NS:.9f} / 3000**. Campaign cumulative:
**{result['campaign_gpu_ns']/a.NS:.9f} / 25202.574545061 seconds**. All phase ceilings
fit. The ledger has {result['ledger_events']} events, preserving the exact original
17412-event prefix. The failed profile stage retains its full 3200 CPU-second
reservation; the 6400 CPU-second / 990 GPU-second timing allocation stays unused.
No new resources are added by this recovery.

- [Exact result and all 76 cells](data/tensor-expanded/recovery-result-v1.json)
- [Corrected independent proof](data/tensor-expanded/independent-proof-v2.json)
- [CPU admission](data/tensor-expanded/cpu-model-admission-v1.json)
- [Native acceptance](data/tensor-expanded/executor-native-acceptance-v3.json)
- [Adapter acceptance](data/tensor-expanded/study-adapter-acceptance-v1.json)
- [Original failed handoff](lp-tensor-expanded-final-gpup8.md)

Final delivery checks revalidate immutable bindings, exact accounting, documentation
links, source syntax, diff hygiene and empty owned-process cleanup. They reuse
endpoint receipts and do not rerun numerical checks or profiles. Publication,
merge, host/container changes and GPUP-9 remain outside scope.
'''
    a.require(not REPORT.exists(),'report already exists');REPORT.write_text(text)
    status=f'''## GPUP-8 corrected proof and device acceptance pass; profile timeout (2026-10-24)

The corrected 7376-case proof, CPU/model/native gates and all six device jobs pass.
All twelve fixed-work/replay pairs are accounted for; twenty changed endpoints
independently verify once. Six small-model profiles complete. The first large-model
BF16 profile times out at its unchanged 18-second deadline without an endpoint.
Nine profiles and sixty timings remain unexecuted. Preserve the full 3200 CPU-second
profile failure charge and every source, image, receipt and historical charge.
No completed check/profile is rerun; no numerical or latency criterion changes.
GPU charge is {new/a.NS:.9f} seconds; GPUP-8 {gpup/a.NS:.9f}/3000 and campaign
{result['campaign_gpu_ns']/a.NS:.9f}/25202.574545061. The {result['ledger_events']}-event ledger
preserves the exact 17412-event prefix. Timing funds remain unused.
Report: docs/benchmarks/lp-tensor-expanded-recovery-gpup8.md.
Scientific stages are closed. GPUP-8 remains incomplete; GPUP-9 stays gated.

'''
    for name in ['AGENTS.md','state/active-task.md','state/known-failures.md','wiki/status.md']:
        p=a.ROOT/name;first,rest=p.read_text().split('\n',1);p.write_text(first+'\n\n'+status+rest.lstrip('\n'))
    p=a.ROOT/'state/backlog.yaml';p.write_text('# GPUP-8 corrected proof/device acceptance pass; large BF16 profile deadline stop; no timings, GPUP-9 gated.\n'+p.read_text())
    p=a.ROOT/'CHANGELOG.md';first,rest=p.read_text().split('\n',1);p.write_text(first+'\n\n## GPUP-8 expanded-window recovery (2026-10-24)\n\n- Correct the versioned fixture generator and pass the independent proof.\n- Add isolated expanded CPU/CUDA window execution, exact reference adoption, bounds, counters and interfaces.\n- Pass device/replay/sanitizer acceptance; retain six complete profiles and the large-model deadline refusal.\n- Preserve all prior evidence/charges; GPUP-8 remains incomplete, with no timing or GPUP-9 execution.\n\n'+rest.lstrip('\n'))

def checks():
    s.frozen();cleanup_receipts(a.read(JOURNAL))
    result=a.read(a.DATA/'recovery-result-v1.json')
    a.require(result['ledger']==a.ref(a.LEDGER),'ledger changed after stop')
    for p in a.ROOT.glob('tools/lp_tensor_expanded_*.py'):ast.parse(p.read_text(),filename=str(p))
    for p in a.ROOT.glob('tests/integration/test_lp_tensor_expanded*.py'):ast.parse(p.read_text(),filename=str(p))
    for name,cmd in [('docs',[sys.executable,'tools/build_docs.py']),('diff',['git','diff','--cached','--check'])]:
        p=subprocess.run(cmd,cwd=a.ROOT,capture_output=True,text=True,timeout=30)
        (BASE/(name+'.stdout')).write_text(p.stdout);(BASE/(name+'.stderr')).write_text(p.stderr);print(p.stdout+p.stderr,flush=True)
        a.require(p.returncode==0,name+' failed')
    a.put(a.DATA/'recovery-delivery-checks-v1.json',dict(status='passed',documentation=a.ref(BASE/'docs.stdout'),diff=a.ref(BASE/'diff.stdout'),
        scientific_report=a.ref(a.DATA/'recovery-result-v1.json'),frozen=a.ref(s.D/'freeze.json'),old_tests_rerun=False,new_endpoint_verification_reused=True))

def run(stage):
    a.require(stage in ['delivery_report','delivery_checks'],'delivery only');j=a.read(JOURNAL)
    a.require(j['delivery_only'] and j['scientific_closed'] and not j['failed'] and j['active'] is None and stage not in j['stage_attempts'],'delivery reservation unavailable')
    amount=j['stages'][stage]['cap_cpu_ns'];out=BASE/(stage+'-resource-v1.json')
    j['stage_attempts'][stage]=dict(output=str(out.relative_to(a.ROOT)),reserved_cpu_ns=amount);supervisor.atomic_json(JOURNAL,j)
    r=supervisor.run(dict(stage=stage,reserve_cpu_seconds=amount/a.NS,output=str(out),log=str(out)+'.log',journal=str(JOURNAL),lock=str(a.ROOT/'artifacts/lp-cpu-admission.lock'),slots=4,
        declared_memory_bytes=4<<30,rss_stop_bytes=6<<30,address_space_bytes=0,sources=[str(Path(__file__))],bootstrap=False,show_log=True,max_gap_ns=100_000_000,
        command=[sys.executable,str(Path(__file__)),'child',stage]))
    print(json.dumps(dict(status=r['status'],charged_cpu_ns=r['charged_cpu_ns'])));return 0 if r['status']=='passed' else 1

if __name__=='__main__':
    if sys.argv[1]=='initialize':initialize()
    elif sys.argv[1]=='child':(compose if sys.argv[2]=='delivery_report' else checks)()
    elif sys.argv[1]=='run':raise SystemExit(run(sys.argv[2]))
