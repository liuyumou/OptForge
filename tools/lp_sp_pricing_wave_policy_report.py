"""Final cold-start policy evidence plus the preceding four-lane comparison."""
import argparse
import csv
import json
from pathlib import Path
import statistics
from lp_sp_pricing_budget import BASE,ROOT,CPU,GPU,NS,accounting,binding,put
from lp_sp_pricing_gpu_opt_compare import read
from lp_sp_pricing_gpu_opt_report import bindings,pairs
from lp_sp_pricing_wave_policy import validate_freeze,LANES
from lp_sp_pricing_wave_report import final_verify as verify_wave,settle as settle_wave
from lp_sp_pricing_report import resource_summary


def report(identity,freeze):
    f=validate_freeze(freeze);out=BASE/identity;out.mkdir(exist_ok=False)
    source=freeze.parent/'result.json';d=read(source);rows=d['rows'];bindings(d)
    if len(rows)!=len(f['cells']) or {r['cell'] for r in rows}!={c['id'] for c in f['cells']}:
        raise RuntimeError('policy comparison roster mismatch')
    lanes={};profiles={}
    for lane in LANES:
        group=[r for r in rows if r['lane']==lane];responses=[read(r['response']['path']) for r in group if r['response']]
        lanes[lane]=dict(attempts=len(group),timely_exact=sum(r['timely'] and r['exact_accepted'] for r in group),
            timely_strict=sum(r['timely'] and r['strict_accepted'] for r in group),
            total_complete_seconds=sum(r['complete_ns'] for r in group)/NS)
        events=[e['gpu'] for r in responses for e in r.get('events',[]) if e.get('gpu')]
        profiles[lane]=dict(exposed_preparation_seconds=sum(e['preparation_ns'] for e in events)/NS,
            initialization_wait_seconds=sum(r.get('wave_session',{}).get('initialization_wait_ns',0) for r in responses)/NS,
            actual_initialization_seconds=sum(r.get('wave_session',{}).get('initialization_ns',0) or 0 for r in responses)/NS,
            cpu_queries_while_initializing=sum(e.get('reason')=='initialization_in_progress' for e in events),
            host_check_seconds=sum(b['exact_check_ns'] for e in events for b in e['batches'])/NS,
            device_seconds=sum(b['device_iteration_ms'] for e in events for b in e['batches'])/1000,
            cpu_auxiliary_calls=sum(e.get('auxiliary_calls',0) for r in responses for e in r.get('events',[])))
    comparisons=[pairs(rows,left,'opportunistic',tier) for tier in ('exact','strict') for left in ('cpu','wave')]
    result=dict(schema=1,status='nonblocking_start_followup_complete',selected=f['selected'],selection=f['selection'],
        development=f['development'],lanes=lanes,profiles=profiles,pairs=comparisons,rows=rows,
        freeze=binding(freeze),comparison=binding(source),resources=resource_summary(),limitations=f['caveats'])
    put(out/'result.json',result)
    (ROOT/'docs/benchmarks/lp-sp-pricing-wave-policy-results.json').write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
    fields=[k for k in rows[0] if k not in ('response','audit')]
    with (ROOT/'docs/benchmarks/lp-sp-pricing-wave-policy-comparison.csv').open('w',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=fields);writer.writeheader();writer.writerows({k:r[k] for k in fields} for r in rows)
    lines=['# Avoiding CPU waits for GPU initialization','',
        'This final policy refinement retains the [synchronized-search and COPT comparison](lp-sp-pricing-wave.md). CUDA initialization still takes real time. While it is unfinished, the candidate now performs the current query with the existing exact CPU oracle. Later queries use the admitted synchronized GPU backend once it is ready.','',
        'No GPU labels are guessed. Failed initialization remains an error. Final teardown waits for and releases an unused session, so initialization is never hidden outside the complete process stopwatch. The admitted CUDA, interval and GMP numerical sources remain byte-for-byte unchanged.','',
        'See the [complete evidence](lp-sp-pricing-wave-policy-results.json), [all cells](lp-sp-pricing-wave-policy-comparison.csv), and [settled checkpoint](lp-sp-pricing-wave-policy-checkpoint.json).','',
        '## Development selection','',
        'The earlier held-out cohort exposed a remaining first-query wait. That cohort stays unchanged. The policy was then evaluated on development seed 73011 using seven models, both startup policies, alternating order and fresh processes. Selection maximizes timely exact certificates and then minimizes capped cold-process cost.','',
        '| Policy | Timely exact certificates | Capped process seconds |','| --- | ---: | ---: |']
    for score in f['selection']:lines.append(f"| {score['lane']} | {score['certified']}/7 | {score['capped_ns']/NS:.3f} |")
    lines+=['',f"Selected policy: **{f['selected']}**.",'',
        '## Fresh confirmation','',
        'A new seed, 111359, supplies seven original models across the seven families. CPU, the preceding wave policy and the opportunistic policy each have two cyclic repetitions: 42 cold processes. Native/process windows remain ten/fifteen seconds. Complete cost includes common input encoding, startup, initialization, solve, output, teardown and independent exact plus unchanged 1e-9 audits.','',
        '| Lane | Timely exact | Timely strict 1e-9 | Total complete seconds |','| --- | ---: | ---: | ---: |']
    for lane,r in lanes.items():lines.append(f"| {lane} | {r['timely_exact']}/{r['attempts']} | {r['timely_strict']}/{r['attempts']} | {r['total_complete_seconds']:.3f} |")
    lines+=['','Totals retain unsuccessful attempts and are not equal-certified-work comparisons. Ratios below use only jointly timely accepted pairs. Values above one favor the opportunistic policy.','',
        '| Tier | Comparator / opportunistic | Paired models / repetitions | Median ratio | Range |',
        '| --- | --- | ---: | ---: | ---: |']
    for p in comparisons:
        ratio='—' if p['median_left_over_right'] is None else f"{p['median_left_over_right']:.3f}×"
        span='—' if p['minimum_left_over_right'] is None else f"{p['minimum_left_over_right']:.3f}–{p['maximum_left_over_right']:.3f}×"
        lines.append(f"| {p['tier']} | {p['left']} / opportunistic | {p['paired_models']} / {p['paired_repetitions']} | {ratio} | {span} |")
    lines+=['','## Preparation and checking','',
        'These totals distinguish exposed waiting from actual initialization work. Initialization overlaps CPU work, so the columns are not additive parts of complete time.','',
        '| Policy | Initialization duration s | Waiting s | Exposed preparation s | Host checks s | CPU queries during initialization |',
        '| --- | ---: | ---: | ---: | ---: | ---: |']
    for lane in ['wave','opportunistic']:
        p=profiles[lane];lines.append(f"| {lane} | {p['actual_initialization_seconds']:.4f} | {p['initialization_wait_seconds']:.4f} | {p['exposed_preparation_seconds']:.4f} | {p['host_check_seconds']:.4f} | {p['cpu_queries_while_initializing']} |")
    lines+=['','The policy can perform more CPU auxiliary work in exchange for avoiding a startup wait. It does not eliminate the CUDA context cost, guarantee full GPU occupancy, or make the exact CPU fallback parallel. The preceding report retains the 12–30× fixed-input host-check gains, varying synchronized-kernel gains and the direct COPT comparison. This new cohort has no COPT lane, so no transitive COPT speedup is claimed.','',
        'Both cohorts are small generated problems with two repetitions and unflushed caches. All deadlines, unmatched certificates and regressions remain. Literal-reference and billion-case limitations are unchanged. CPU tests cover nonblocking dispatch, ready-future dispatch, error propagation and cleanup of unused sessions. The final checkpoint records the full test count, document verification, source bindings, retained failures and resource settlement.','']
    (ROOT/'docs/benchmarks/lp-sp-pricing-wave-policy.md').write_text('\n'.join(lines))
    print(json.dumps(dict(selected=f['selected'],lanes=lanes,profiles=profiles,
        pairs=[{k:v for k,v in p.items() if k!='rows'} for p in comparisons])),flush=True)


def final_verify(identity,freeze,wave_freeze):
    report(identity,freeze)
    verify_wave(identity+'/wave',wave_freeze)
    checked=bindings(read(BASE/identity/'result.json'))
    preceding=BASE/identity/'wave/verification.json';d=read(preceding)
    put(BASE/identity/'verification.json',dict(status='passed',tests=d['tests'],documentation_pages=d['documentation_pages'],
        checked_bindings=checked,wave_verification=binding(preceding),result=binding(BASE/identity/'result.json'),
        outputs=[binding(ROOT/'docs/benchmarks'/n) for n in ['lp-sp-pricing-wave-policy.md',
            'lp-sp-pricing-wave-policy-results.json','lp-sp-pricing-wave-policy-comparison.csv']]))


def settle(identity,reservation):
    settle_wave(identity+'/wave',reservation)
    from lp_sp_pricing_finish import identities,still_same_process
    summary=resource_summary()
    if summary['pending_at_snapshot']:raise RuntimeError('unsettled policy work')
    cpu,gpu=accounting(BASE),accounting(BASE,True)
    if any(cpu[p]>CPU[p]*NS or gpu[p]>GPU[p]*NS for p in CPU):raise RuntimeError('phase ceiling exceeded')
    owned=set()
    for pattern in ['*.resource.json','*.journal.json']:
        for path in (BASE/'resources').glob(pattern):owned.update(identities(read(path)))
    if any(still_same_process(*p) for p in owned):raise RuntimeError('owned process still live')
    result=read(BASE/identity/'result.json');verification=BASE/identity/'verification.json';bindings(read(verification))
    checkpoint=dict(status='nonblocking_wave_followup_settled',selected=result['selected'],resources=summary,
        cpu_phase_ns=cpu,gpu_phase_ns=gpu,lanes=result['lanes'],profiles=result['profiles'],
        pairs=[{k:v for k,v in p.items() if k!='rows'} for p in result['pairs']],tests=read(verification)['tests'],
        documentation_pages=read(verification)['documentation_pages'],owned_identities=len(owned),live_owned_identities=[],active_reservations=[],
        verification=binding(verification),wave_checkpoint=binding(BASE/identity/'wave/settled-checkpoint.json'))
    put(BASE/identity/'settled-checkpoint.json',checkpoint)
    target=ROOT/'docs/benchmarks/lp-sp-pricing-wave-policy-checkpoint.json'
    target.write_text(json.dumps(checkpoint,indent=2,sort_keys=True)+'\n')
    (ROOT/'book/docs/benchmarks/lp-sp-pricing-wave-policy-checkpoint.json').write_bytes(target.read_bytes())
    print(json.dumps(dict(status=checkpoint['status'],cpu_seconds=summary['cpu_ns']/NS,gpu_seconds=summary['gpu_ns']/NS,
        owned_identities=len(owned))),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['verify','settle']);p.add_argument('identity')
    p.add_argument('--freeze',type=Path);p.add_argument('--wave-freeze',type=Path);p.add_argument('--reservation');a=p.parse_args()
    if a.action=='verify':final_verify(a.identity,a.freeze.resolve(),a.wave_freeze.resolve())
    else:settle(a.identity,a.reservation)
