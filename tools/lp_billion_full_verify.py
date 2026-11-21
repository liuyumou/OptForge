"""Final CPU-only checks for the completed, source-bound billion comparison."""
import json,subprocess,sys
from lp_billion_common import BASE,ROOT,load,put,ref,resolve,require
from lp_confirmation2_supervisor import same_process


def main():
    output=BASE/'full-billion-verification-v1'
    output.mkdir(exist_ok=False)
    commands=[('harness',[sys.executable,'-B','-m','unittest','discover','-s','tests/integration','-p','test_lp_billion*.py']),
              ('documentation',['python3','-B','tools/build_docs.py']),
              ('diff',['git','diff','--check'])]
    receipts=[]
    for name,command in commands:
        p=subprocess.run(command,cwd=ROOT,capture_output=True,text=True,timeout=120)
        (output/(name+'.stdout')).write_text(p.stdout)
        (output/(name+'.stderr')).write_text(p.stderr)
        require(p.returncode==0,name+' validation failed; preserve logs')
        receipts.append(dict(name=name,command=command,stdout=ref(output/(name+'.stdout')),stderr=ref(output/(name+'.stderr'))))
        print(name,p.stdout[-500:],p.stderr[-500:],flush=True)
    previous=load(BASE/'complete-device-checkpoint-v1.json')
    numerical=previous['current_numerical_bindings']
    for item in numerical:resolve(item)
    require(len(numerical)==300,'all current numerical bindings')
    image=load(resolve(previous['image']))
    for key in ['cuda','executor','legacy','old_executor','preparation','preparation_source']:resolve(image[key])
    report=load(ROOT/'docs/benchmarks/lp-billion-full-results.json')
    seen=set()
    def verify_refs(value):
        if isinstance(value,dict):
            if {'namespace','path','sha256','bytes'}<=value.keys():
                key=(value['namespace'],value['path'],value['sha256'])
                if key not in seen:resolve(value);seen.add(key)
            else:
                for item in value.values():verify_refs(item)
        elif isinstance(value,list):
            for item in value:verify_refs(item)
    verify_refs(report)
    require(report['available_responses']==18 and report['strictly_certified']==3,'complete original project cohort')
    rows=report['cells']+report['supplemental']['cells']
    frozen=load(resolve(report['freeze']))
    extra=load(resolve(report['supplemental']['freeze']))
    for f in [frozen,extra]:
        for key in ['source','adapter','audit','child','checker','protocol']:
            if isinstance(f.get(key),dict):resolve(f[key])
    require(len(rows)==36,'retain all original and supplemental slots')
    identities={};settlements=[];cleanup_dispositions=[];assessment_claims=distinct_checks=0
    prefixes=('full-billion-v1-','copt-nopresolve-64m-v1-','copt-nopresolve-256m-v1-','copt-nopresolve-512m-v1-','copt-nopresolve-1b-v1-')
    for path in sorted((BASE/'resources').glob('*.settlement.json')):
        if not path.name.startswith(prefixes):continue
        settled=load(path)
        require(not settled['overrun'],'no new cohort overrun')
        if not settled['cleanup_empty']:
            from lp_billion_budget import cleared
            cleared(path,False,'reporting','full-billion-verification-v1')
            disposition=path.with_name(path.name.replace('.settlement.json','.cleanup-disposition.json'))
            cleanup_dispositions.append(ref(disposition))
            for identity in load(disposition)['identities']:
                identities[(identity['pid'],identity['start_ticks'])]=identity
        resource=load(resolve(settled['resource']))
        for identity in resource['result'].get('observed_processes',[]):
            identities[(identity['pid'],identity['start_ticks'])]=identity
        settlements.append(ref(path))
    alive=[x for x in identities.values() if same_process(x)]
    require(not alive,'all retained cohort-owned identities have exited')
    for row in rows:
        if 'audit' not in row:continue
        a=load(resolve(row['audit']))
        distinct_checks+=a.get('checks',0)
        assessment_claims+=a.get('covered_endpoints',0)
    from lp_billion_idle import Nvml
    sensor=Nvml()
    try:sample=sensor.sample()
    finally:sensor.close()
    put(output/'device-sample.json',sample)
    put(output/'result.json',dict(status='passed',commands=receipts,numerical_bindings=numerical,
        image=previous['image'],verified_compact_references=len(seen),report=ref(ROOT/'docs/benchmarks/lp-billion-full-results.json'),
        phase_csv=ref(ROOT/'docs/benchmarks/lp-billion-full-phases.csv'),rows=len(rows),
        actual_attempts=sum((BASE/'resources'/(r['id']+'.reservation.json')).exists() for r in rows),actual_responses=sum('response' in r for r in rows),strict_certificates=sum(r.get('certified',False) for r in rows),
        independent_checks=distinct_checks,recorded_assessment_claims=assessment_claims,
        process_identities_checked=len(identities),all_cohort_owned_identities_gone=True,settlements=settlements,cleanup_dispositions=cleanup_dispositions,
        final_device_observation=ref(output/'device-sample.json'),source=ref(__file__),fresh_full_portable_replay=False))
    print(dict(status='passed',numerical_bindings=len(numerical),references=len(seen),owned_identities_gone=len(identities)),flush=True)

if __name__=='__main__':main()
