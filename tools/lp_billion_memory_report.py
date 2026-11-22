"""Audit borrowed-storage comparisons and retain their measured memory costs."""
import argparse
import statistics
from pathlib import Path
from lp_billion_common import BASE,ROOT,load,put,ref,resolve,require,CPU_CAPS,GPU_CAPS
from lp_billion_budget import accounting
from lp_billion_admit import gate_identity


def array_transcript(response):
    # Endpoint arrays are already content-addressed and independently checked.
    # Compare their exact manifests without materializing millions of Python floats.
    result={k:v for k,v in response.items() if k not in
            ['model_sha256','input_ns','elapsed_ns','cost_ns','cached_assessments','device_bytes_upper','gpu_preparation']}
    if 'fast_config' in result:
        result['fast_config']={k:v for k,v in result['fast_config'].items() if k!='gpu_preparation'}
    require('endpoint' in result,'canonical array endpoint')
    return result


def report(identity):
    old=load(BASE/'image-v3/binding.json');new=load(BASE/'image-v4/binding.json')
    require(old['cuda']['sha256']==new['cuda']['sha256'],'unchanged solve CUDA')
    require(old['preparation']['sha256']==new['preparation']['sha256'],'unchanged preparation CUDA')
    allowed={'research/lp-billion-lowbit/'+p for p in
             ['src/billion.rs','src/operator.rs','src/tensor.rs','tests/contracts.rs']}
    exact=[];changed=[]
    for item in load(resolve(old['source_manifest']))['sources']:
        name=item['original']['path']
        if not (name.endswith(('.rs','.cu')) or Path(name).name.startswith('Cargo.')):continue
        resolve(item['retained'])
        current=ref(ROOT/name)
        if current!=item['original']:
            require(name in allowed,'unapproved numerical source change '+name)
            changed.append(dict(before=item['retained'],after=current))
        else:exact.append(item['original'])
    require(len(exact)+len(changed)==293 and len(changed)==4,'complete numerical source coverage')
    for item in load(resolve(new['source_manifest']))['sources']:
        name=item['original']['path']
        if name.endswith(('.rs','.cu')) or Path(name).name.startswith('Cargo.'):
            resolve(item['original']);resolve(item['retained'])
    admissions=[]
    for kind in ['gpu','memcheck','racecheck','initcheck','synccheck']:
        name=gate_identity(kind,4);result_path=BASE/name/'result.json';result=load(result_path)
        settlement_path=BASE/'resources'/(name+'.settlement.json');settlement=load(settlement_path)
        require(settlement['status']=='passed' and settlement['cleanup_empty'] and not settlement['overrun'],'complete admission '+name)
        require(result['status']=='passed' and result['image']==ref(BASE/'image-v4/binding.json'),'admitted image '+name)
        require(len(result['rows'])==(60 if kind=='gpu' else 20),'continuation coverage')
        scalar=0
        for row in result['rows']:
            require(row['exact'],'exact admission transcript');resolve(row['response'])
            for proof in row['serial']:resolve(proof);scalar+=1
        preparation=result['preparation']
        admissions.append(dict(identity=name,result=ref(result_path),settlement=ref(settlement_path),
                               continuations=len(result['rows']),scalar_checks=scalar,preparation=preparation))
    cohorts=[]
    for tag in ['64m','256m','512m']:
        path=BASE/('paired-'+tag+'-v3-v4.json');d=load(path)
        comparison_settlement=BASE/'resources'/('comparison-ladder-'+tag+'-v4.settlement.json')
        audit_settlement=BASE/'resources'/('audit-'+tag+'-v4.settlement.json')
        for receipt in [comparison_settlement,audit_settlement]:
            checked=load(receipt)
            require(checked['status']=='passed' and checked['cleanup_empty'] and not checked['overrun'],'supervised full comparison and audit')
        require(d['status']=='passed','paired exact comparison')
        cells=[]
        for p in d['pairs']:
            a,b=p['before'],p['after']
            require(p['exact'] and p['timing_eligible'],'valid paired timing')
            require(array_transcript(load(resolve(a['response'])))==array_transcript(load(resolve(b['response']))),'full exact numerical transcript')
            require(a['logical']==b['logical']==100,'fixed work')
            for record in [a,b]:
                for key in ['resource','final_check','audit']:resolve(record[key])
            cells.append(dict(family=p['family'],before_peak_rss_bytes=a['peak_rss_bytes'],after_peak_rss_bytes=b['peak_rss_bytes'],
                peak_rss_ratio=a['peak_rss_bytes']/b['peak_rss_bytes'],saved_rss_bytes=a['peak_rss_bytes']-b['peak_rss_bytes'],
                preparation_ratio=p['preparation_ratio'],assessment_ratio=p['assessment_ratio'],complete_ratio=p['complete_ratio'],
                before_complete_ns=a['complete_ns'],after_complete_ns=b['complete_ns'],certified=b['certified'],
                exact=True,logical=b['logical'],accepted_fp4_share=b['accepted_fp4_share'],
                before_response=a['response'],after_response=b['response'],resource=b['resource'],final_check=b['final_check'],audit=b['audit']))
        cohorts.append(dict(scale=tag,comparison=ref(path),comparison_settlement=ref(comparison_settlement),
            audit_settlement=ref(audit_settlement),cells=cells,
            median_peak_rss_ratio=statistics.median(c['peak_rss_ratio'] for c in cells),
            median_preparation_ratio=d['median_preparation_ratio'],median_assessment_ratio=d['median_assessment_ratio'],
            median_complete_ratio=d['median_complete_ratio']))
    failures=[]
    for path in sorted((BASE/'resources').glob('*.settlement.json')):
        result=load(path)
        if result['status']!='passed':failures.append(dict(settlement=ref(path),cpu_ns=result['cpu_ns'],gpu_ns=result['gpu_ns']))
    cpu,gpu=accounting()
    put(BASE/(identity+'.json'),dict(status='borrowed_storage_admitted_and_measured',image=ref(BASE/'image-v4/binding.json'),
        previous_image=ref(BASE/'image-v3/binding.json'),prior_checkpoint=ref(BASE/'preparation-device-checkpoint-v2.json'),
        admissions=admissions,cohorts=cohorts,
        original_numerical_bindings=len(exact)+len(changed),unchanged_numerical_bindings=len(exact),changed=changed,
        unchanged_numerical_sources=exact,failed_reservations=failures,cpu_ns_including_active=sum(cpu.values()),
        gpu_ns_including_active=sum(gpu.values()),cpu_caps=CPU_CAPS,gpu_caps=GPU_CAPS,
        billion_host_gate=ref(BASE/'billion-host-availability-v2.json'),billion_solve_measurements=0,
        source=ref(__file__),strict_certificates_unchanged=True,
        limitation='Descriptive single 100-update capacity runs; all failures and regressions retained. No certified-solve, broad FP4 or billion-scale performance claim.'))
    print(dict(status='passed',cohorts=len(cohorts),cells=sum(len(c['cells']) for c in cohorts)),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--id',required=True);report(p.parse_args().id)
