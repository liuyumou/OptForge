"""Bind complete preparation admission while retaining every interruption."""
import argparse
import json
from lp_billion_common import BASE,load,put,ref,resolve,require


def report(identity):
    require(identity and '/' not in identity and identity not in ['.','..'],'report identity')
    results=[]
    for name in ['operational-gpu-v8','operational-gpu-v9','array-gpu-v3','array-memcheck-v4',
                 'array-racecheck-v6','array-initcheck-v3','array-synccheck-v3']:
        path=BASE/name/'result.json';result=load(path)
        resource=BASE/'resources'/(name+'.settlement.json');settlement=load(resource)
        require(settlement['status']=='passed' and settlement['cleanup_empty'] and not settlement['overrun'],'completed admission supervision')
        for row in result['rows']:
            response=load(resolve(row['response']))
            require(row['exact'],'exact continuation')
            endpoints=[*response['assessments'],response]
            require(len(endpoints)==len(row['serial']),'independent checker coverage')
            for endpoint,item in zip(endpoints,row['serial']):
                proof=load(resolve(item))
                for field in ['accepted','feasible','objective','bound','gap_upper']:
                    require(proof[field]==endpoint['certificate'][field],'strict original scalar comparison')
        backends={}
        for item in (result.get('preparation') or {}).get('results',[]):
            prepared=load(resolve(item));require(prepared['exact'],'bitwise preparation')
            backend=prepared['preparation']['backend'];backends[backend]=backends.get(backend,0)+1
            if backend=='host-fallback':
                require(bool(prepared['preparation']['reason']),'explicit CPU fallback reason')
        trace=BASE/'resources'/(name+'.resource.json.capacity.jsonl')
        samples=[json.loads(line)['gpu'] for line in trace.read_text().splitlines()]
        results.append(dict(identity=name,result=ref(path),settlement=ref(resource),trace=ref(trace),
            exact_continuations=len(result['rows']),scalar_checks=sum(len(r['serial']) for r in result['rows']),
            preparation_backends=backends,gpu_samples=len(samples),
            samples_with_owner=sum(bool(s['processes']) for s in samples),
            maximum_unattributed_bytes=max(s['used']-sum(s['processes'].values()) for s in samples)))
    failures=[]
    for name,reason in [('array-memcheck-v3','command_failed'),('array-racecheck-v3','sampled_rss_limit'),
                        ('array-racecheck-v4','unattributed GPU memory exceeds fixed idle allowance'),
                        ('array-racecheck-v5','guardian_cpu_wall_deadline')]:
        path=BASE/'resources'/(name+'.settlement.json');settlement=load(path)
        resource=load(resolve(settlement['resource']))
        require(settlement['status']=='refused' and settlement['cleanup_empty'] and not settlement['overrun'],'retained failed admission')
        require(settlement['cpu_ns']==960_000_000_000 and settlement['gpu_ns']==240_000_000_000,'full failed charge')
        require(resource['result']['reason']==reason,'interruption classification')
        from lp_confirmation2_supervisor import same_process
        coordinator=BASE/'resources'/(name+'.resource.json.coordinator-result.json')
        detail=resource['result'] if 'observed_processes' in resource['result'] else load(coordinator)
        identities=detail['observed_processes']
        require(not any(same_process(p) for p in identities),'failed admission process still alive')
        outputs=[ref(p) for p in sorted((BASE/name).glob('prepare-*.result.json'))]
        failures.append(dict(identity=name,settlement=ref(path),reason=reason,completed_preparation_results=outputs,
            retained_process_identities=len(identities),live_process_identities=0,
            peak_rss_bytes=detail.get('peak_rss_bytes'),
            supplemental_coordinator=ref(coordinator) if detail is not resource['result'] else None,
            partial_log=ref(BASE/'resources'/(name+'.resource.json.log'))))
    image=BASE/'image-v3/binding.json'
    for key in ['executor','legacy','cuda','preparation']:
        resolve(load(image)[key])
    observations=[]
    for version in range(2,7):
        name=f'idle-confirmation-v{version}';path=BASE/name/'result.json'
        settlement=BASE/'resources'/(name+'.settlement.json')
        if path.exists():
            result=load(path)
            for item in result['samples']:resolve(item)
            observations.append(dict(result=ref(path),status=result['status'],settlement=ref(settlement)))
        elif settlement.exists():
            stopped=load(settlement)
            require(stopped['status']=='refused' and stopped['cleanup_empty'] and not stopped['overrun'],'partial observation disposition')
            require(stopped['cpu_ns']==1920_000_000_000 and stopped['gpu_ns']==0,'full CPU observation charge')
            resource=load(resolve(stopped['resource']))
            observations.append(dict(result=None,status='interrupted',settlement=ref(settlement),
                reason=resource['result']['reason'],initial=ref(BASE/name/'initial.json'),
                partial_log=ref(BASE/'resources'/(name+'.resource.json.log')),
                previous_partial_report=ref(BASE/'preparation-progress-v1.json')))
    result=dict(status='gpu_preparation_admitted',image=ref(image),completed=results,failed=failures,
        observations=observations,monitor_handoffs=[ref(p) for p in sorted(BASE.glob('idle-handoff-v*/result.json'))],
        source=ref(__file__),operational_plan=ref(BASE/'operational-readmissions/v9.json'),
        cpu_acceptance=ref(BASE/'resources/operational-cpu-v9.settlement.json'),
        harness_acceptance=ref(BASE/'resources/preparation-harness-cpu-v6.settlement.json'),
        numerical_code_unchanged=True,strict_certificates_unchanged=True,
        limitation='Device acceptance is separate from performance evidence and does not establish billion-scale convergence or broad FP4 superiority.')
    put(BASE/(identity+'.json'),result)
    print(dict(status=result['status'],completed_admissions=len(results),retained_interruptions=len(failures)),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--id',required=True)
    report(parser.parse_args().id)
