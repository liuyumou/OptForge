"""Source-bound retained-record MIXED2 admission. Forecasts are not measurements."""
import argparse
from collections import defaultdict
import gzip
import itertools
import json
import math
import statistics as stats
from lp_mixed2_common import ROOT, BASE, put, ref, load, require
from lp_delivery4_stats import interval, classify

DATA=ROOT/'docs/benchmarks/data'
OUTPUT=DATA/'mixed2-cost-v1.json'
TARGETS=('dense-generic-128','dense-generic-256','dense-generic-512')
METRICS=24
COSTS=('representation','transfer','guard','correction','fallback','checking')


def forecast(total, affected, speed, work, overhead):
    numbers=(total,affected,work,overhead)
    require(all(math.isfinite(v) for v in numbers),'nonfinite cost')
    require(total>0 and 0<=affected<total and work>=1 and overhead>=0,'invalid cost')
    require(speed is None or (math.isfinite(speed) and speed>0),'invalid speed')
    return total-affected+(0 if speed is None else work*affected/speed)+overhead


def scenarios():
    yield dict(id='ideal-all-events',fraction=1.0,speed=None,work=1.0,overhead_ms=0.0)
    for f,s,w,o in itertools.product((.25,.5,1.),(1.25,1.5,2.,4.),(1.,1.25,2.),(0.,.1,.5,1.)):
        yield dict(id=f'f{f}-s{s}-w{w}-o{o}',fraction=f,speed=s,work=w,overhead_ms=o)


def validate(rows,families,lifecycle):
    require(len(families)==12 and len(set(families))==12 and set(TARGETS)<=set(families) and 'infinite-bound-refusal' in families,'family roster')
    require(lifecycle in ('cold','prepared'),'lifecycle')
    index={}
    for row in rows:
        key=row['block'],row['family']
        require(key not in index,'duplicate cell');index[key]=row
        require(row['lane']=='nativefast' and row['tier']=='certified-1e-9' and row['role']=='candidate' and row['lifecycle']==lifecycle,'control selection')
        require(row['variant']==('candidate' if lifecycle=='cold' else 'batch'),'control variant')
        expected=row['family']!='infinite-bound-refusal'
        require(type(row['certified']) is bool and row['certified']==expected,'certificate coverage')
        require(len(row['records'])==(1 if lifecycle=='cold' else 3),'solve count')
        for rec in row['records']:
            require(type(rec['certified']) is bool and rec['certified']==expected,'solve coverage')
            costs=rec['costs_ns'];t=rec['complete_ns'];g=rec['gpu_us']*1000
            require(all(type(v) is int and v>=0 for v in costs.values()),'invalid phase cost')
            require(sum(costs.values())==rec['solve_ns'],'solve costs do not close')
            require(math.isfinite(g) and 0<=g<=costs.get('iteration',0) and 0<=g<t,'GPU event boundary')
            require(type(t) is int and t>0 and rec['solve_ns']<=t,'complete boundary')
            require(type(rec['physical']) is int and (rec['physical']>0 if expected else rec['physical']==0),'physical work')
            require(rec['setup_ns']>=0 and (lifecycle!='cold' or rec['solve_ns']+rec['setup_ns']<=t),'setup boundary')
        require(row['complete_ns']==stats.median(r['complete_ns'] for r in row['records']),'session reduction')
        if lifecycle=='prepared':require(row['setup']['total_ns']>=0 and row['teardown_ns']>=0,'lifecycle cost')
    require(set(index)==set(itertools.product(range(32),families)),'missing or extra cells')
    return index


def summarize(rows,families,lifecycle,scenario):
    index=validate(rows,families,lifecycle)
    predicted={}
    for key,row in index.items():
        predicted[key]=stats.median(forecast(r['complete_ns'],r['gpu_us']*1000*scenario['fraction'],scenario['speed'],scenario['work'],scenario['overhead_ms']*1e6) for r in row['records'])
    block_ratios=[math.exp(stats.mean(math.log(index[b,f]['complete_ns']/predicted[b,f]) for f in TARGETS)) for b in range(32)]
    ci=interval(block_ratios,metrics=METRICS)
    benefit=dict(**ci,decision=classify(ci,1.1,True))
    guards=[]
    for family in families:
        if family=='infinite-bound-refusal':continue
        values=[(predicted[b,family]-index[b,family]['complete_ns']-max(.02*index[b,family]['complete_ns'],100000))/1e6 for b in range(32)]
        ci=interval(values,metrics=METRICS)
        guards.append(dict(family=family,**ci,decision=classify(ci,0.,False)))
    return dict(scenario=scenario,benefit=benefit,guards=guards,block_ratios=block_ratios,
                conditional_all_cost_rules_supported=benefit['decision']=='supported' and all(g['decision']=='supported' for g in guards))


def bound(reference):
    p=ROOT/reference['path'];require(ref(p)==reference,'input binding mismatch')
    return json.loads(gzip.decompress(p.read_bytes())) if p.suffix=='.gz' else load(p)


def analyze():
    routes=[];bindings=[]
    for version,lifecycle in ((4,'cold'),(3,'prepared')):
        report_path=DATA/f'delivery{version}-result-v1.json';report=load(report_path)
        portable=bound(report['cohorts_archive']);bindings.extend([ref(report_path),report['cohorts_archive']])
        cohort=portable['cohorts']['confirmation'];all_rows=cohort['result']['rows']
        require(len(all_rows)==(3072 if version==4 else 6144),'historical cohort coverage')
        rows=[r for r in all_rows if r['lane']=='nativefast' and r['tier']=='certified-1e-9' and r['role']=='candidate' and r['lifecycle']==lifecycle]
        families=list(cohort['manifest']['models']);validate(rows,families,lifecycle)
        comparisons=[summarize(rows,families,lifecycle,s) for s in scenarios()]
        samples=[];family_summary=[]
        for row in rows:
            for solve,r in enumerate(row['records']):
                t=r['complete_ns'];g=r['gpu_us']*1000
                setup=r['setup_ns'] if lifecycle=='cold' else 0
                phases={k:v for k,v in r['costs_ns'].items() if k!='iteration'}
                phases.update(gpu_event=g,iteration_outside_event=r['costs_ns'].get('iteration',0)-g,session_setup=setup,outside_solve_and_setup=t-setup-r['solve_ns'])
                require(math.isclose(sum(phases.values()),t,abs_tol=1e-5),'partition mismatch')
                samples.append(dict(id=row['id'],block=row['block'],family=row['family'],solve=solve,certified=r['certified'],physical=r['physical'],complete_ns=t,gpu_upper_ns=g,parts_ns=phases,
                    extra_allowance_2x_ns=t/1.1-(t-g+g/2),result=r['result']))
        for family in families:
            group=[s for s in samples if s['family']==family]
            sessions=[r for r in rows if r['family']==family]
            family_summary.append(dict(family=family,solves=len(group),certificates=sum(s['certified'] for s in group),
                complete_median_ms=stats.median(s['complete_ns'] for s in group)/1e6,
                event_median_ms=stats.median(s['gpu_upper_ns'] for s in group)/1e6,
                event_fraction_median=stats.median(s['gpu_upper_ns']/s['complete_ns'] for s in group),
                extra_allowance_2x_median_ms=stats.median(s['extra_allowance_2x_ns'] for s in group)/1e6,
                setup_teardown_median_ms=stats.median(r['setup']['total_ns']+r['teardown_ns'] for r in sessions)/1e6 if lifecycle=='prepared' else None))
        ideal=comparisons[0]['benefit']
        disposition='defer-insufficient-upper-bound' if ideal['upper'] is not None and ideal['upper']<1.1 else 'defer-matrix-attribution-and-added-costs-unknown'
        routes.append(dict(lifecycle=lifecycle,source_version=version,cells=len(rows),solves=len(samples),families=families,summary=family_summary,samples=samples,scenarios=comparisons,
            disposition=disposition,matrix_affected_fraction_measured=False,new_mixed_certificates=0,useful_mixed_windows_measured=0,
            added_costs={c:dict(measured=False,lower_bound_ns=0,upper_bound_ns=None) for c in COSTS}))
    return dict(schema_version=1,status='cpu-admission-complete-device-deferred',source=ref(ROOT/'tools/lp_mixed2_cost.py'),
        protocol=ref(ROOT/'docs/specifications/SPEC-0036-mixed2.md'),inputs=bindings,metrics=METRICS,routes=routes,
        gpu_seconds=0,historical_decisions_unchanged=True,
        limitation='Assumed transformed retained costs, not measured speedup or confidence in a new candidate. Shared device and block independence limitations remain. Whole GPU events include non-matrix work; overhead and work amplification are unmeasured.')

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--verify',action='store_true');args=p.parse_args()
    result=analyze()
    if args.verify:require(result==load(OUTPUT),'cost replay mismatch')
    else:put(OUTPUT,result)
    print(json.dumps(dict(status=result['status'],routes=[dict(lifecycle=r['lifecycle'],disposition=r['disposition'],ideal=r['scenarios'][0]['benefit'],twofold=next(s['benefit'] for s in r['scenarios'] if s['scenario']['id']=='f1.0-s2.0-w1.0-o0.0')) for r in result['routes']]),indent=2))
