"""CPU-only exact replay of DELIVERY4 portable evidence and frozen decisions."""
import argparse
import gzip
import hashlib
import json
from lp_delivery4_common import ROOT,load,ref,require,put
from lp_delivery4_stats import summarize
from lp_delivery2_study import matches,bits


def bound(binding):
    path=ROOT/binding['path'];require(ref(path)==binding,'portable binding differs')
    return json.loads(gzip.decompress(path.read_bytes()))


def replay():
    result=load(ROOT/'docs/benchmarks/data/delivery4-result-v1.json')
    portable=bound(result['cohorts_archive']);groups=portable['cohorts']
    for family,raw in portable['model_bytes'].items():
        require(hashlib.sha256(raw.encode()).hexdigest()==groups['confirmation']['manifest']['models'][family]['sha256'],'original model bytes changed')
    collected={k:[] for k in groups};logs={}
    for binding in result['archives']:
        archive=bound(binding);kind=archive['kind'];rows=archive['result']['rows'];manifest=groups[kind]['manifest']
        for row in rows:
            original=portable['originals'][row['original_result']['path']]
            for record in row['records']:
                value=archive['outputs'][record['result']['path']]
                matches(value,original,manifest['binary'])
                require(record['certified']==(row['family']!='infinite-bound-refusal'),'coverage changed')
                require(record['solve_ns']==value['solve_ns'] and record['costs_ns']==value['costs_ns'],'timer binding differs')
            if kind=='profile':logs[row['id']]=archive['stderr'][row['id']]
        collected[kind]+=rows
    for kind,rows in collected.items():
        require(bits(rows)==bits(groups[kind]['result']['rows']),'archive/cohort rows differ')
        manifest=groups[kind]['manifest'];require(len(rows)==len(manifest['cells']),'incomplete cohort')
        require({r['id'] for r in rows}=={c['id'] for c in manifest['cells']},'identity mismatch')
    decisions=summarize(collected['confirmation'],list(groups['confirmation']['manifest']['models']))
    require(decisions==result['decisions'],'frozen decision mismatch')
    from lp_delivery4_report import lifecycle_profiles
    require(lifecycle_profiles(collected['profile'],logs)==result['profile_lifecycle'],'lifecycle diagnosis differs')
    return dict(status='passed',cells=sum(map(len,collected.values())),confirmation_cells=len(collected['confirmation']),decisions=len(decisions),all_numerical_values_exact=True,profile_partition_exact=True,no_solver_or_device_execution=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output');a=p.parse_args();value=replay()
    if a.output:put(a.output,value)
    print(value)
