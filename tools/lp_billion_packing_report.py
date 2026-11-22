"""Verify exact indexed-packing admission and retain every preparation timing."""
import argparse
import statistics
from pathlib import Path
from lp_billion_common import BASE,ROOT,load,put,ref,resolve,require,CPU_CAPS,GPU_CAPS
from lp_billion_budget import accounting
from lp_billion_admit import gate_identity
from lp_billion_results import canonical


def numerical(name):
    return name.endswith(('.rs','.cu')) or Path(name).name.startswith('Cargo.')


def passed(path):
    result=load(path)
    require(result['status']=='passed' and result['cleanup_empty'] and not result['overrun'],
            'complete supervised reservation '+str(path))
    resolve(result['resource'])
    return result


def report(identity):
    old=load(BASE/'image-v4/binding.json');new=load(BASE/'image-v7/binding.json')
    for key in ['cuda','preparation']:
        require(old[key]['sha256']==new[key]['sha256'],'unchanged CUDA '+key)
        resolve(old[key]);resolve(new[key])
    allowed={'research/lp-billion-lowbit/'+p for p in
             ['src/billion.rs','src/lib.rs','src/tensor.rs','tests/contracts.rs']}
    exact=[];changed=[];previous=set();current=[]
    for item in load(resolve(old['source_manifest']))['sources']:
        name=item['original']['path']
        if not numerical(name):continue
        previous.add(name);resolve(item['retained'])
        latest=ref(ROOT/name)
        if latest!=item['original']:
            require(name in allowed,'unexpected numerical source change '+name)
            changed.append(dict(before=item['retained'],after=latest))
        else:exact.append(item['original'])
    require(len(exact)+len(changed)==293 and len(changed)==4,'prior numerical source coverage')
    for item in load(resolve(new['source_manifest']))['sources']:
        if numerical(item['original']['path']):
            resolve(item['original']);resolve(item['retained']);current.append(item['original'])
    added=[p for p in current if p['path'] not in previous]
    require(len(current)==296 and [p['path'] for p in added]==
            ['research/lp-billion-lowbit/diagnostics/packing.rs','research/lp-billion-lowbit/src/tensor_prepare.rs','research/lp-billion-lowbit/src/tensor_prepare_encode.rs'],'new numerical module coverage')
    operational=[]
    for name in ['packing-quality-v5','operational-cpu-v15','seal-packing-v3','packing-idle-v4','operational-gpu-v15']:
        path=BASE/'resources'/(name+'.settlement.json');passed(path);operational.append(ref(path))
    interrupted=BASE/'resources/operational-gpu-v11.settlement.json'
    failed=load(interrupted)
    require(failed['status']=='refused' and failed['cleanup_empty'] and not failed['overrun'] and
            failed['cpu_ns']==480_000_000_000 and failed['gpu_ns']==120_000_000_000,
            'retained full operational failure charge')
    cleanup=BASE/'operational-gpu-v11/cleanup-verification.json'
    from lp_confirmation2_supervisor import same_process
    require(not any(same_process(p) for p in load(cleanup)['identities']),'interrupted process remains')
    idle_history=[]
    for name in ['packing-idle-v1','packing-idle-v2','packing-idle-v3','packing-idle-v4']:
        settlement=BASE/'resources'/(name+'.settlement.json');passed(settlement)
        idle_history.append(dict(result=ref(BASE/name/'result.json'),settlement=ref(settlement)))
    require(load(BASE/'packing-idle-v2/result.json')['status']=='idle_gate_not_met','retained interrupted idle span')
    require(load(BASE/'packing-idle-v4/result.json')['status']=='observed_idle','fresh complete idle observation')
    admissions=[]
    for kind in ['gpu','memcheck','racecheck','initcheck','synccheck']:
        name=gate_identity(kind,7);path=BASE/name/'result.json';result=load(path)
        settlement_path=BASE/'resources'/(name+'.settlement.json');settlement=passed(settlement_path)
        require(result['status']=='passed' and result['image']==ref(BASE/'image-v7/binding.json'),'admitted image')
        require(len(result['rows'])==(60 if kind=='gpu' else 20),'complete continuation suite')
        scalar=0
        for row in result['rows']:
            require(row['exact'],'exact admission transcript');resolve(row['response'])
            for proof in row['serial']:resolve(proof);scalar+=1
        preparation=result['preparation'];backends={}
        require(preparation['exact_preparations']==(66 if kind=='gpu' else 8),'complete preparation suite')
        for item in preparation['results']:
            check=load(resolve(item));require(check['exact'],'bitwise preparation')
            backend=check['preparation']['backend'];backends[backend]=backends.get(backend,0)+1
        require(scalar==(130 if kind=='gpu' else 60),'complete independent scalar checking')
        resource=load(resolve(settlement['resource']))
        admissions.append(dict(identity=name,result=ref(path),settlement=ref(settlement_path),
            continuations=len(result['rows']),scalar_checks=scalar,preparation=preparation,
            preparation_backends=backends,gpu_ns=settlement['gpu_ns'],
            peak_rss_bytes=resource['result']['peak_rss_bytes']))
    cohorts=[]
    for tag,count in [('64m',6),('256m',2),('512m',2)]:
        path=BASE/('paired-'+tag+'-v4-v7.json');d=load(path)
        comparison_settlement=BASE/'resources'/('comparison-ladder-'+tag+'-v7.settlement.json')
        audit_settlement=BASE/'resources'/('audit-'+tag+'-v7.settlement.json')
        for receipt in [comparison_settlement,audit_settlement]:passed(receipt)
        require(d['status']=='passed' and len(d['pairs'])==count,'complete paired cohort')
        cells=[]
        for pair in d['pairs']:
            a,b=pair['before'],pair['after']
            require(pair['exact'] and pair['timing_eligible'],'valid paired timing')
            before=load(resolve(a['response']));after=load(resolve(b['response']))
            require(canonical(before)==canonical(after),'full exact numerical transcript')
            require(a['logical']==b['logical']==100 and not a['certified'] and not b['certified'],'fixed-work limit')
            detail=after['preparation_detail_ns']
            require(set(detail)=={'engine','operator','packing','control_initialization'} and
                    all(isinstance(v,int) and v>=0 for v in detail.values()),'preparation partitions')
            require(sum(detail.values())==b['cost_ns']['host_preparation'],'complete preparation coverage')
            for record in [a,b]:
                for key in ['resource','final_check','audit']:resolve(record[key])
            cells.append(dict(family=pair['family'],preparation_detail_ns=detail,
                preparation_ratio=pair['preparation_ratio'],assessment_ratio=pair['assessment_ratio'],
                process_ratio=pair['process_ratio'],complete_ratio=pair['complete_ratio'],
                before_input_ns=a['input_ns'],after_input_ns=b['input_ns'],
                before_preparation_ns=a['cost_ns']['host_preparation'],after_preparation_ns=b['cost_ns']['host_preparation'],
                before_process_ns=a['process_ns'],after_process_ns=b['process_ns'],
                before_complete_ns=a['complete_ns'],after_complete_ns=b['complete_ns'],
                before_peak_rss_bytes=a['peak_rss_bytes'],after_peak_rss_bytes=b['peak_rss_bytes'],
                exact=True,logical=b['logical'],certified=b['certified'],accepted_fp4_share=b['accepted_fp4_share'],
                before_response=a['response'],after_response=b['response'],resource=b['resource'],
                final_check=b['final_check'],audit=b['audit']))
        cohorts.append(dict(scale=tag,comparison=ref(path),comparison_settlement=ref(comparison_settlement),
            audit_settlement=ref(audit_settlement),cells=cells,
            median_preparation_ratio=d['median_preparation_ratio'],median_assessment_ratio=d['median_assessment_ratio'],
            median_process_ratio=d['median_process_ratio'],median_complete_ratio=d['median_complete_ratio'],
            median_peak_rss_ratio=statistics.median(c['before_peak_rss_bytes']/c['after_peak_rss_bytes'] for c in cells)))
    failures=[]
    for path in sorted((BASE/'resources').glob('*.settlement.json')):
        result=load(path)
        if result['status']!='passed':failures.append(dict(settlement=ref(path),cpu_ns=result['cpu_ns'],gpu_ns=result['gpu_ns']))
    cpu,gpu=accounting()
    put(BASE/(identity+'.json'),dict(status='indexed_packing_admitted_and_measured',image=ref(BASE/'image-v7/binding.json'),
        previous_image=ref(BASE/'image-v4/binding.json'),prior_checkpoint=ref(BASE/'memory-results-v1.json'),
        operational=operational,admissions=admissions,cohorts=cohorts,
        idle_history=idle_history,idle_proof=ref(BASE/'availability/operational-gpu-v15.json'),
        operational_plan=ref(BASE/'operational-readmissions/v15.json'),
        interrupted_operational_admission=ref(interrupted),interrupted_cleanup=ref(cleanup),
        original_numerical_bindings=293,unchanged_numerical_bindings=len(exact),changed=changed,added=added,
        current_numerical_bindings=len(current),current_numerical_sources=current,
        failed_reservations=failures,cpu_ns_including_active=sum(cpu.values()),gpu_ns_including_active=sum(gpu.values()),
        cpu_caps=CPU_CAPS,gpu_caps=GPU_CAPS,billion_host_gate=ref(BASE/'billion-host-availability-v3.json'),
        billion_solve_measurements=0,source=ref(__file__),strict_certificates_unchanged=True,
        limitation='Descriptive sequential 100-update capacity runs, all uncertified; regressions and failures retained. No certified-solve or broad FP4 superiority claim.'))
    print(dict(status='passed',cohorts=len(cohorts),cells=sum(len(c['cells']) for c in cohorts)),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--id',required=True);report(p.parse_args().id)
