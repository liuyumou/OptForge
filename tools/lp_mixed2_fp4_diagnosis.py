"""Retain positive, negative and inconclusive development findings without regrading."""
from collections import defaultdict
from statistics import median
from lp_mixed2_fp4_common import ROOT,BASE,load,put,ref

def summarize(folder,extra):
    d=load(BASE/folder/'result.json');groups=defaultdict(list)
    for s in d['sessions']:
        key=(s['family'],s['lane'],*(s['settings'].get(k) for k in extra)) if extra else (s['family'],s['lane'])
        groups[key].append(s)
    rows=[]
    for key,ss in sorted(groups.items()):
        records=[r for s in ss for r in s['records']]
        rows.append(dict(family=key[0],lane=key[1],settings=dict(zip(extra,key[2:])),sessions=len(ss),solves=len(records),complete_ms=median(r['complete_ns'] for r in records)/1e6,gpu_ms=median(r['gpu_us'] for r in records)/1000,physical=sorted(set(r['physical'] for r in records)),setup_ms=median(s['setup_ns'] for s in ss)/1e6,costs_ms={k:median(r['costs_ns'].get(k,0) for r in records)/1e6 for k in set().union(*(r['costs_ns'] for r in records))},recoveries=sum(len(r['recoveries']) for r in records)))
    return dict(manifest=ref(BASE/folder/'manifest.json'),result=ref(BASE/folder/'result.json'),rows=rows)

def run():
    development={name:summarize(name,extra) for name,extra in [('development-v1',()),('development-v2',()),('windows-v1',('window_max',)),('schedule-v1',('fixed_audit',))]}
    products={}
    for folder in ('products-v1','products-v2'):
        d=load(BASE/folder/'result.json');groups=defaultdict(list)
        for r in d['rows']:groups[r['family'],r['lane'],r['transpose'],r['guarded']].append(r)
        products[folder]=dict(result=ref(BASE/folder/'result.json'),rows=[dict(family=k[0],lane=k[1],transpose=k[2],guarded=k[3],product_us=median(r['gpu_per_product_us'] for r in rs),vector_preparation_us=median(r['vector_prepare_ns'] for r in rs)/1000,block_values_us=[r['gpu_per_product_us'] for r in rs]) for k,rs in sorted(groups.items())])
    d=load(BASE/'timing-ablation-v1/result.json');pairs={}
    for s in d['sessions']:pairs[s['block'],s['family'],s['lane'],s['variant']]=median(r['complete_ns'] for r in s['records'])/1e6
    ablation=[]
    for family,lane in sorted(set((k[1],k[2]) for k in pairs)):
        timed=[pairs[b,family,lane,'timed'] for b in range(4)];minimal=[pairs[b,family,lane,'minimal'] for b in range(4)];ratios=[a/b for a,b in zip(timed,minimal)]
        ablation.append(dict(family=family,lane=lane,timed_ms=median(timed),minimal_ms=median(minimal),timed_over_minimal=median(ratios),ratios=ratios,difference_ms=[a-b for a,b in zip(timed,minimal)]))
    put(ROOT/'docs/benchmarks/data/mixed2-fp4-diagnosis-v1.json',dict(development=development,products=products,timing_ablation=dict(result=ref(BASE/'timing-ablation-v1/result.json'),exact_pairs=d['exact_pairs'],rows=ablation),limits=['Development cells are selection/diagnostic evidence, not confirmation or independent production samples.','Product event batches include host launch gaps; guard-free results never authorize a solver.','Four-block timer ablation is descriptive; noisy differences do not identify individual timer costs.']))
    print(dict(status='complete',development_stages=len(development),product_cells=360,timer_pairs=d['exact_pairs']))
if __name__=='__main__':run()
