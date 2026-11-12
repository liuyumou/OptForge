"""Reproduce an exploratory CPU-only diagnosis from committed DELIVERY3 records.

No solver, checker service, compiler or device command is launched. Primary
retention decisions are reproduced unchanged, never replaced by these summaries.
"""
import argparse
from collections import defaultdict
import gzip
import hashlib
import json
import math
from pathlib import Path
import statistics as stats

from lp_delivery3_common import ROOT, LANES, TIERS, TARGETS, DEVICE
from lp_delivery3_stats import summarize

DATA = ROOT / 'docs/benchmarks/data'
OUTPUT = DATA / 'delivery3-diagnosis-v1.json'
KEYS = ('lifecycle', 'family', 'lane', 'tier', 'role')


def require(condition, message):
    if not condition:
        raise ValueError(message)


def binding(path):
    path = Path(path)
    return dict(path=str(path.relative_to(ROOT)), sha256=hashlib.sha256(path.read_bytes()).hexdigest())


def read_bound(reference):
    path = ROOT / reference['path']
    require(binding(path) == reference, 'input binding mismatch: ' + str(path))
    return json.loads(gzip.decompress(path.read_bytes())) if path.suffix == '.gz' else json.loads(path.read_bytes())


def distribution(values):
    require(bool(values) and all(math.isfinite(v) for v in values), 'empty/nonfinite distribution')
    ordered = sorted(values)
    return dict(n=len(values), mean=stats.mean(values), median=stats.median(values),
                minimum=min(values), maximum=max(values),
                q1=stats.median(ordered[:len(ordered)//2]) if len(ordered)>1 else ordered[0],
                q3=stats.median(ordered[(len(ordered)+1)//2:]) if len(ordered)>1 else ordered[0])


def correlation(a, b):
    require(len(a) == len(b) and len(a) >= 2, 'correlation sample mismatch')
    ma, mb = stats.mean(a), stats.mean(b)
    scale = math.sqrt(sum((x-ma)**2 for x in a)*sum((y-mb)**2 for y in b))
    return sum((x-ma)*(y-mb) for x,y in zip(a,b))/scale if scale else None


def components(record, lifecycle):
    """Disjoint measured phases; GPU event interval is nested in iteration."""
    costs = record['costs_ns']
    require(sum(costs.values()) == record['solve_ns'], 'solve phases do not close')
    gpu = record['gpu_us'] * 1000
    require(0 <= gpu <= costs.get('iteration', 0), 'GPU/iteration timing mismatch')
    setup = record['setup_ns'] if lifecycle == 'cold' else 0
    outside = record['complete_ns'] - record['solve_ns'] - setup
    require(outside >= 0, 'complete boundary mismatch')
    result = {k: v/1e6 for k,v in costs.items() if k != 'iteration'}
    result.update(gpu_event=gpu/1e6, iteration_outside_event=(costs.get('iteration', 0)-gpu)/1e6,
                  session_setup=setup/1e6, outside_solve_and_setup=outside/1e6)
    require(math.isclose(sum(result.values()), record['complete_ns']/1e6, abs_tol=1e-9), 'decomposition does not close')
    return result


def forecast(total, affected, speedup=None, work_multiplier=1., overhead=0.):
    require(0 <= affected < total and work_multiplier >= 0 and overhead >= 0, 'invalid cost model')
    require(speedup is None or speedup > 0, 'invalid assumed speedup')
    return total / (total - affected + (0 if speedup is None else work_multiplier*affected/speedup) + overhead)


def env_rows(environments):
    rows=[]
    for block, env in enumerate(environments):
        row=dict(block=block)
        for moment in ('start', 'end'):
            sample=env[moment]
            fields=next(line.split(',') for line in sample['device']['stdout'].splitlines() if line.startswith(DEVICE))
            for key,index in (('temperature_c',1),('sm_mhz',2),('utilization_pct',4),('memory_mib',5),('power_w',6)):
                row[f'{moment}_{key}']=float(fields[index])
            row[f'{moment}_load1']=sample['load_average'][0]
        row['block_wall_seconds']=(env['end']['monotonic_ns']-env['start']['monotonic_ns'])/1e9
        rows.append(row)
    return rows


def profile_rows(result):
    groups=defaultdict(list)
    parent_groups=defaultdict(list)
    setup_groups=defaultdict(list)
    delivery_groups=defaultdict(list)
    for archive in result['archives']:
        if 'delivery3-profile-' not in archive['path']:
            continue
        value=read_bound(archive)
        for row in value['result']['rows']:
            key=tuple(row[k] for k in ('lifecycle','family','lane','tier','variant'))
            log=[json.loads(line) for line in value['stderr'][row['id']].splitlines() if line.startswith('{')]
            child_setup=[e['delivery3_checker_setup'] for e in log if 'delivery3_checker_setup' in e]
            require(len(child_setup)==1, 'checker setup coverage')
            child=child_setup[0]
            first=value['outputs'][row['records'][0]['result']['path']]
            spans=first['delivery_profile']['setup']['spans']
            setup={s['phase']:(s['end_ns']-s['begin_ns'])/1e6 for s in spans}
            setup.update(checker_model_read_ms=child['read_ns']/1e6,
                         checker_model_prepare_ms=(child['prepared_ns']-child['read_ns'])/1e6,
                         checker_after_prepare_to_ready_ms=(child['ready_ns']-child['prepared_ns'])/1e6,
                         checker_internal_ready_ms=child['ready_ns']/1e6)
            setup_groups[key].append(setup)
            assessments=[e['delivery3_checker_assessment'] for e in log if 'delivery3_checker_assessment' in e]
            parent=[]
            for record in row['records']:
                output=value['outputs'][record['result']['path']]
                parent.extend(output['delivery_profile']['assessments'])
                if row['lifecycle']=='prepared':
                    d=record['delivery']
                    delivery_groups[key].append(dict(send_ms=d['send_ns']/1e6,
                        wait_read_ms=(d['receive_end_ns']-d['send_ns'])/1e6,
                        durable_ms=(d['durable_end_ns']-d['receive_end_ns'])/1e6))
            require(len(parent)==len(assessments), 'parent/child assessment mismatch')
            for index,(p,c) in enumerate(zip(parent,assessments)):
                require(c['serial']==index, 'checker serial order')
                groups[key].append(dict(decode_ms=c['decode_ns']/1e6,
                    assessment_ms=(c['assessed_ns']-c['decode_ns'])/1e6,
                    send_ms=(c['sent_ns']-c['assessed_ns'])/1e6))
                parent_groups[key].append(dict(request_ms=p['request_build_encode_write_flush_ns']/1e6,
                    wait_read_ms=(p['response_wait_read_end_ns']-p['request_build_encode_write_flush_ns'])/1e6,
                    decode_ms=(p['response_decode_end_ns']-p['response_wait_read_end_ns'])/1e6,
                    binding_ms=(p['binding_end_ns']-p['response_decode_end_ns'])/1e6,
                    total_ms=p['binding_end_ns']/1e6))
    output=[]
    for key in sorted(groups):
        row=dict(zip(('lifecycle','family','lane','tier','variant'),key))
        for name,source in (('child',groups),('parent',parent_groups),('setup',setup_groups),('delivery',delivery_groups)):
            rows=source.get(key,[])
            row[name]={metric:distribution([r[metric] for r in rows]) for metric in rows[0]} if rows else None
        output.append(row)
    return output


def diagnose():
    result=json.loads((DATA/'delivery3-result-v1.json').read_bytes())
    portable=read_bound(result['cohorts_archive'])
    for reference in result['archives']:
        require(binding(ROOT/reference['path'])==reference, 'evidence archive changed')
    cohort=portable['cohorts']['confirmation']
    rows=cohort['result']['rows']; manifest=cohort['manifest']
    require(len(rows)==6144 and sum(len(r['records']) for r in rows)==12288, 'confirmation coverage')
    require(sum(rec['certified'] for row in rows for rec in row['records'])==11264, 'certificate coverage')
    require(summarize(rows,list(manifest['models']))==result['decisions'], 'primary retention changed')
    lookup={tuple(r[k] for k in ('block',*KEYS)):r for r in rows}
    require(len(lookup)==len(rows), 'duplicate cell')
    schedule={c['id']:i for i,c in enumerate(manifest['cells'])}
    require(set(schedule)=={r['id'] for r in rows}, 'schedule coverage')
    environments=env_rows(result['environment']['confirmation'])
    groups=defaultdict(list)
    for row in rows:
        require(len(row['records'])==(1 if row['lifecycle']=='cold' else 3), 'solve count')
        require(row['complete_ns']==stats.median(r['complete_ns'] for r in row['records']), 'session estimand changed')
        groups[tuple(row[k] for k in KEYS)].append(row)
    phases=[]; positions=[]; budgets=[]
    for key,group in sorted(groups.items()):
        identity=dict(zip(KEYS,key));lifecycle=identity['lifecycle']
        records=[r for cell in group for r in cell['records']]
        decomposed=[components(r,lifecycle) for r in records]
        names=sorted(set().union(*(p.keys() for p in decomposed)))
        totals=[r['complete_ns']/1e6 for r in records]
        mean_parts={n:stats.mean(p.get(n,0) for p in decomposed) for n in names}
        phases.append(dict(**identity,sessions=len(group),solves=len(records),mean_complete_ms=stats.mean(totals),
            mean_parts_ms=mean_parts,median_primary_session_ms=stats.median(r['complete_ns']/1e6 for r in group),
            physical=sorted({r['physical'] for r in records}),
            mean_phase_fraction={n:stats.mean(p.get(n,0)/t for p,t in zip(decomposed,totals)) for n in names},
            phase_ms={n:distribution([p.get(n,0) for p in decomposed]) for n in names},
            complete_phase_correlations={n:correlation(totals,[p.get(n,0) for p in decomposed]) for n in names}))
        if lifecycle=='prepared':
            first_deltas=[(r['records'][0]['complete_ns']-stats.mean(v['complete_ns'] for v in r['records'][1:]))/1e6 for r in group]
            session_overhead=[(r['setup']['total_ns']+r['teardown_ns'])/1e6 for r in group]
            positions.append(dict(**identity,position_ms=[distribution([r['records'][i]['complete_ns']/1e6 for r in group]) for i in range(3)],
                first_minus_later_mean_ms=distribution(first_deltas),
                setup_plus_teardown_ms=distribution(session_overhead),
                amortized_delivery_mean_ms={str(n):stats.mean(totals)+stats.mean(session_overhead)/n for n in (3,10,100)},
                excluded_validation_and_coordinator_ms=distribution([(r['batch_with_analysis_ns']-r['setup']['total_ns']-r['teardown_ns']-sum(v['complete_ns'] for v in r['records']))/1e6 for r in group])))
        if identity['role']=='candidate' and identity['lane']=='nativefast' and identity['family']!='infinite-bound-refusal':
            # Retained trials, same lifecycle. GPU event interval is an optimistic
            # upper bound for a future matrix-only arithmetic implementation.
            forecasts=[]
            for row in group:
                ts=[r['complete_ns']/1e6 for r in row['records']]
                aa=[r['gpu_us']/1000 for r in row['records']]
                base=stats.median(ts)
                entry=dict(block=row['block'],gpu_fraction=stats.mean(a/t for a,t in zip(aa,ts)))
                for label,speed in (('gpu_2x',2.),('gpu_4x',4.),('gpu_removed',None)):
                    transformed=[t-a+(a/speed if speed else 0) for t,a in zip(ts,aa)]
                    entry[label]=base/stats.median(transformed)
                entry['headroom_for_1_10_ms']=base/1.1-stats.median(t-a for t,a in zip(ts,aa))
                entry['gpu_2x_headroom_for_1_10_ms']=base/1.1-stats.median(t-a/2 for t,a in zip(ts,aa))
                forecasts.append(entry)
            budgets.append(dict(**identity,per_block=forecasts,summary={metric:distribution([f[metric] for f in forecasts]) for metric in forecasts[0] if metric!='block'}))
    pairs=[]
    for lifecycle in ('cold','prepared'):
        for family in manifest['models']:
            for lane in LANES:
                for tier in TIERS:
                    observed=[]
                    for block in range(32):
                        a=lookup[block,lifecycle,family,lane,tier,'control'];b=lookup[block,lifecycle,family,lane,tier,'candidate']
                        require(abs(schedule[a['id']]-schedule[b['id']])==1, 'pair not adjacent')
                        ac,bc=a['complete_ns']/1e6,b['complete_ns']/1e6
                        observed.append(dict(block=block,control_ms=ac,candidate_ms=bc,ratio=ac/bc,
                            delta_ms=bc-ac,guard_excess_ms=bc-ac-max(.02*ac,.1),
                            candidate_first=schedule[b['id']]<schedule[a['id']],pair_position=min(schedule[a['id']],schedule[b['id']])%192))
                    ratios=[math.log(v['ratio']) for v in observed]
                    order={label:[p for p in observed if p['candidate_first']==flag] for label,flag in (('candidate_first',True),('control_first',False))}
                    require(all(len(v)==16 for v in order.values()), 'counterbalance mismatch')
                    pair=dict(lifecycle=lifecycle,family=family,lane=lane,tier=tier,observations=observed,
                        ratio=distribution([p['ratio'] for p in observed]),delta_ms=distribution([p['delta_ms'] for p in observed]),
                        positive_guard_blocks=sum(p['guard_excess_ms']>0 for p in observed),
                        by_order={k:dict(ratio=distribution([v['ratio'] for v in vv]),delta_ms=distribution([v['delta_ms'] for v in vv])) for k,vv in order.items()},
                        first_half_ratio=stats.median(v['ratio'] for v in observed[:16]),last_half_ratio=stats.median(v['ratio'] for v in observed[16:]),
                        control_candidate_correlation=correlation([v['control_ms'] for v in observed],[v['candidate_ms'] for v in observed]),
                        log_ratio_lag1=correlation(ratios[:-1],ratios[1:]),
                        log_ratio_associations={name:correlation(ratios,[e[name] for e in environments]) for name in environments[0]},
                        log_ratio_pair_position=correlation(ratios,[v['pair_position'] for v in observed]))
                    pairs.append(pair)
    target_forecasts=[]
    for lifecycle in ('cold','prepared'):
        for tier in TIERS:
            selected=[b for b in budgets if b['lifecycle']==lifecycle and b['tier']==tier and b['family'] in TARGETS]
            require(len(selected)==3, 'target cost model coverage')
            row=dict(lifecycle=lifecycle,tier=tier)
            for scenario in ('gpu_2x','gpu_4x','gpu_removed'):
                block_ratios=[math.exp(stats.mean(math.log(b['per_block'][i][scenario]) for b in selected)) for i in range(32)]
                row[scenario]=distribution(block_ratios)
            target_forecasts.append(row)
    value=dict(kind='delivery3-retained-diagnosis-v1',exploratory=True,gpu_seconds=0,
        inputs=[binding(DATA/'delivery3-result-v1.json'),result['cohorts_archive'],*result['archives']],
        source=binding(Path(__file__)),confirmation_cells=len(rows),confirmation_solves=12288,
        primary_decisions_exact=True,primary_decisions=result['decisions'],
        phases=phases,prepared_positions=positions,pairs=pairs,environment=environments,
        native_gpu_cost_bounds=budgets,dense_target_forecasts=target_forecasts,
        instrumented_profile=profile_rows(result),
        limits=[
            'Post hoc descriptive associations; no p-values, causal attribution, adjusted retention or block exclusions.',
            'Block-boundary device observations are not per-cell occupancy; process restarts do not prove independence.',
            'Per-record additive means differ from the primary median-of-block-ratios estimand.',
            'GPU event time is nested within iteration and includes stream/launch gaps; it is not isolated matrix arithmetic.',
            'Parent/child checker spans overlap and cannot be summed; profiling uses only two fresh blocks.',
            'Prepared setup and teardown are excluded from primary solve latency; amortization is a forecast using measured session overhead, not a new throughput experiment.',
            'GPU cost ceilings hold fixed all other work, update counts and certificates and assume zero added cost; MIXED2 can affect only part of the event interval.',
            'Constructed development families and a shared device; no general production guarantee.' ])
    return value


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,default=OUTPUT);a=p.parse_args()
    value=diagnose()
    a.output.parent.mkdir(parents=True,exist_ok=True)
    with a.output.open('x') as stream:
        json.dump(value,stream,sort_keys=True,indent=2,allow_nan=False);stream.write('\n')
    print(json.dumps(dict(output=str(a.output),cells=value['confirmation_cells'],decisions_unchanged=True,
                         dense_target_forecasts=value['dense_target_forecasts']),indent=2))


if __name__=='__main__':
    main()
