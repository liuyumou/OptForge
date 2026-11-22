"""Every GPU packing outcome, exact transcripts and disjoint complete phase costs."""
import argparse,copy,csv,statistics
from pathlib import Path
from lp_billion_common import BASE,ROOT,put,load,ref,resolve,require
from lp_billion_full_report import record

def canonical(r):
    r=copy.deepcopy(r)
    for k in ['model_sha256','input_ns','elapsed_ns','cost_ns','cached_assessments','device_bytes_upper','gpu_preparation','gpu_packing','preparation_detail_ns','solver_profile']:
        r.pop(k,None)
    if 'fast_config' in r:
        r['fast_config'].pop('gpu_preparation',None);r['fast_config'].pop('gpu_packing',None)
    return r

def compare(a,b,historical):
    eligible=a.get('timing_eligible',False) and b.get('timing_eligible',False)
    result=dict(family=a['family'],baseline=a['id'],candidate=b['id'],historical_control=historical,both_timing_eligible=eligible,
        both_strict_certified=bool(eligible and a.get('certified') and b.get('certified')))
    if 'response' in a and 'response' in b:
        old=load(resolve(a['response']));new=load(resolve(b['response']))
        require(old['model_sha256']==new['model_sha256'],'comparison original model identity')
        result.update(exact_numerical_transcript=canonical(old)==canonical(new),same_accepted_updates=old['logical']==new['logical'])
        before=old.get('assessments',[]);after=new.get('assessments',[])
        result['common_assessment_prefix_exact']=before[:min(len(before),len(after))]==after[:min(len(before),len(after))]
    if eligible:
        result.update(packing_ratio=a['preparation_detail_ns']['packing']/b['preparation_detail_ns']['packing'],
            preparation_ratio=a['solver_preparation_ns']/b['solver_preparation_ns'],complete_ratio=a['complete_ns']/b['complete_ns'],
            complete_reduction_fraction=1-b['complete_ns']/a['complete_ns'])
    return result

def report(scale):
    manifest=BASE/f'gpu-pack-{scale}-v1/freeze.json';f=load(manifest)
    require((manifest.parent/'completed.json').exists(),'completed cohort with every available endpoint audited')
    rows=[]
    for c in f['cells']:
        r=record(c);r['version']=c['version'];r['scale']=scale
        if 'response' in r:
            response=load(resolve(r['response']));r['gpu_packing']=response.get('gpu_packing')
            r['requested_solver_wall_ns']=c['request']['settings']['wall_ms']*1_000_000
            r['requested_wall_exceeded']=r['solver_wall_ns']>r['requested_solver_wall_ns']
        rows.append(r)
    historical=[]
    if scale=='1b':
        old=load(resolve(f['historical_control']))
        historical=[dict(record(c),version='v9',scale='1b',historical_control=True) for c in old['cells'] if c['lane']=='fp4x2']
    comparisons=[]
    for family in dict.fromkeys(c['family'] for c in f['cells']):
        a=next(r for r in rows+historical if r['family']==family and r['version']=='v9')
        b=next(r for r in rows if r['family']==family and r['version']=='v10')
        comparisons.append(compare(a,b,scale=='1b'))
    eligible=[c for c in comparisons if c['both_timing_eligible']]
    if scale=='64m':require(all(c.get('exact_numerical_transcript') for c in eligible),'full fixed-work transcript equality')
    value=dict(status='complete_development_cohort',scale=scale,freeze=ref(manifest),cells=rows,historical_controls=historical,comparisons=comparisons,
        preparation_ratio_median=statistics.median(c['preparation_ratio'] for c in eligible) if eligible else None,
        complete_ratio_median=statistics.median(c['complete_ratio'] for c in eligible) if eligible else None,
        jointly_certified_pairs=sum(c['both_strict_certified'] for c in comparisons),source=ref(__file__),
        timing_scope='Complete cost is fresh solver process, response persistence and cold independent final original-model proof; additional intermediate proofs are offline and reported separately.',
        limitations=['One rotated repetition at 64 M; billion controls are retained historical runs, not concurrent paired trials.',
            'No cache flush or hardware counter claim; input includes chunk hashing/validation and original CSR-to-CSC construction.',
            'Uncertified or unequal-work bounded runs do not establish certified-solve speedups; all regressions and missing outcomes remain.'])
    path=manifest.parent/'results.json';put(path,value);print(dict(scale=scale,eligible=len(eligible),preparation_ratio_median=value['preparation_ratio_median'],complete_ratio_median=value['complete_ratio_median']),flush=True)

def deliver():
    reports=[load(BASE/f'gpu-pack-{scale}-v1/results.json') for scale in ['64m','1b']]
    value=dict(status='complete',cohorts=reports,sources=[ref(BASE/f'gpu-pack-{s}-v1/results.json') for s in ['64m','1b']],
        candidate=ref(BASE/'image-v10/binding.json'),strict_original_model_tolerance=1e-9,public_adoption=False,confirmation=False)
    target=ROOT/'docs/benchmarks/lp-billion-gpu-packing-results.json';put(target,value)
    rows=[r for report in reports for r in report['cells']+report['historical_controls']]
    phases=sorted({k for r in rows for k in r.get('complete_cost_ledger',{}).get('exclusive_ns',{})})
    target=ROOT/'docs/benchmarks/lp-billion-gpu-packing-phases.csv'
    with target.open('x',newline='') as stream:
        w=csv.writer(stream,lineterminator='\n');w.writerow(['scale','family','version','historical_control','status','timing_eligible','certified','logical_updates','fp4_work_share','preparation_seconds','packing_seconds','complete_seconds','solver_hwm_gib',*[k+'_seconds' for k in phases]])
        for r in rows:
            costs=r.get('complete_cost_ledger',{}).get('exclusive_ns',{})
            if costs:require(sum(costs.values())==r['complete_ns'],'exact exported complete cost')
            w.writerow([r['scale'],r['family'],r['version'],r.get('historical_control',False),r['status'],r.get('timing_eligible',False),r.get('certified',False),r.get('logical'),r.get('accepted_fp4_share'),
                r.get('solver_preparation_ns',0)/1e9 if costs else None,r.get('preparation_detail_ns',{}).get('packing',0)/1e9 if costs else None,r.get('complete_ns',0)/1e9 if costs else None,
                r['solver_child_hwm_bytes']/2**30 if r.get('solver_child_hwm_bytes') else None,*[costs.get(k,0)/1e9 if costs else None for k in phases]])
    put(BASE/'gpu-pack-delivery-v1.json',dict(status='complete',results=ref(ROOT/'docs/benchmarks/lp-billion-gpu-packing-results.json'),phases=ref(target),source=ref(__file__)))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['report','deliver']);p.add_argument('--scale',choices=['64m','1b']);a=p.parse_args()
    report(a.scale) if a.action=='report' else deliver()
