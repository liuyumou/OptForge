"""Final source/cleanup/proof verification for GPU assessment/control, without historical rewrites."""
import argparse,subprocess,sys
from pathlib import Path
from lp_billion_common import BASE,ROOT,load,put,ref,resolve,require
from lp_confirmation2_supervisor import same_process
CHANGED={f'research/lp-billion-lowbit/{p}' for p in ['src/billion.rs','src/fast_device.rs','src/lib.rs','src/array_assessment.rs','src/control.rs','src/merit.rs','tests/contracts.rs']}
ADDED=[f'research/lp-billion-lowbit/{p}' for p in ['src/gpu_control.rs','src/bin/control_check.rs','cuda/control.cu']]

def main(identity):
    out=BASE/identity;out.mkdir(exist_ok=False);commands=[]
    for name,cmd in [('harness',[sys.executable,'-B','-m','unittest','discover','-s','tests/integration','-p','test_lp_billion*.py']),('documentation',['python3','-B','tools/build_docs.py']),('diff',['git','diff','--check'])]:
        p=subprocess.run(cmd,cwd=ROOT,text=True,capture_output=True,timeout=120)
        (out/(name+'.stdout')).write_text(p.stdout);(out/(name+'.stderr')).write_text(p.stderr)
        require(p.returncode==0,name+' final verification failed')
        commands.append(dict(name=name,stdout=ref(out/(name+'.stdout')),stderr=ref(out/(name+'.stderr'))))
        print(name,p.stdout[-400:],p.stderr[-400:],flush=True)
    prior=load(BASE/'gpu-pack-settled-checkpoint-v1.json');old_image=load(BASE/'image-v10/binding.json')
    old_sources={x['original']['path']:x for x in load(resolve(old_image['source_manifest']))['sources']}
    unchanged=[];changed=[];current=[]
    for item in prior['numerical_bindings']:
        if item['namespace']=='repo' and item['path'] in CHANGED:
            retained=old_sources[item['path']]['retained'];resolve(retained)
            require(retained['sha256']==item['sha256'],'exact historical source retained')
            new=ref(ROOT/item['path']);changed.append(dict(previous=item,retained=retained,current=new));current.append(new)
        else:resolve(item);unchanged.append(item);current.append(item)
    require({x['previous']['path'] for x in changed}==CHANGED,'exact scoped integration changes only')
    for p in ADDED:current.append(ref(ROOT/p))
    image=load(BASE/'image-v11/binding.json')
    for item in image['files'].values():resolve(item)
    for key in ['cuda','preparation','packing']:require(image[key]['sha256']==old_image[key]['sha256'],'unchanged numerical CUDA '+key)
    for item in load(resolve(image['source_manifest']))['sources']:
        if item['original']['path'].endswith(('.rs','.cu')) or Path(item['original']['path']).name.startswith('Cargo.'):
            resolve(item['original']);resolve(item['retained'])
    counter=load(BASE/'disk-inventory-admission-v2/result.json')
    require(counter['status']=='passed','independent exact storage inventory audit')
    for key in ['binding','recompiled','source','retained_source']:resolve(counter[key])
    for name in ['operational-cpu-v29','operational-gpu-v23']:
        gate=load(BASE/'resources'/(name+'.settlement.json'))
        require(gate['status']=='passed' and gate['cleanup_empty'] and not gate['overrun'],'fresh resource-source operational admission')
    data=load(ROOT/'docs/benchmarks/lp-billion-gpu-control-results.json');seen=set()
    # The immutable 64 M report predates the later retention-report additions.
    # Verify that exact source through its own reservation snapshot.
    original=data['cohorts'][0]['source']
    require(original==dict(namespace='repo',path='tools/lp_billion_gpu_control_report.py',bytes=7654,
        sha256='04462bb5a186efcb0db448f1b8a8776dfb123636a1e95af24049e68b15af1c32'),'only the recorded historical report source')
    reservation=BASE/'resources/gpu-control-report-64m-v1.reservation.json'
    source_manifest=load(reservation)['source_manifest'];snapshot=load(resolve(source_manifest))
    retained=[p['retained'] for p in snapshot['sources'] if p['original']==original]
    require(len(retained)==1 and all(retained[0][k]==original[k] for k in ['bytes','sha256']),'exact historical report source snapshot')
    resolve(retained[0])
    historical_source=dict(original=original,retained=retained[0],manifest=source_manifest,reservation=ref(reservation))
    def refs(v):
        if isinstance(v,dict):
            if {'namespace','path','sha256','bytes'}<=v.keys():
                key=(v['namespace'],v['path'],v['sha256'])
                if key not in seen:
                    resolve(retained[0] if v==original else v);seen.add(key)
            else:
                for x in v.values():refs(x)
        elif isinstance(v,list):
            for x in v:refs(x)
    refs(data)
    from lp_billion_gpu_control_report import canonical
    equal_update_comparisons=[]
    for cohort in data['cohorts']:
        rows={r['id']:r for r in cohort['cells']+cohort['historical_controls']}
        for pair in cohort['comparisons']:
            if not pair['both_timing_eligible'] or not pair.get('same_accepted_updates'):continue
            a=canonical(load(resolve(rows[pair['baseline']]['response'])))
            b=canonical(load(resolve(rows[pair['candidate']]['response'])))
            differences=sorted(k for k in a.keys()|b.keys() if a.get(k)!=b.get(k))
            require(differences in ([],['status']),'equal-update numerical fields remain exact')
            equal_update_comparisons.append(dict(scale=cohort['scale'],family=pair['family'],
                differing_fields=differences,numerical_fields_equal=True,
                baseline_status=a['status'],candidate_status=b['status'],
                full_transcript_flag_preserved=pair['exact_numerical_transcript']))
    identities={};settlements=[]
    operational={f'operational-cpu-v{i}' for i in range(27,30)} | {f'operational-gpu-v{i}' for i in range(22,24)}
    for p in sorted((BASE/'resources').glob('*.settlement.json')):
        identity=p.name.removesuffix('.settlement.json')
        if not identity.startswith(('gpu-control-','space-')) and identity not in operational:continue
        if p==BASE/'resources'/(out.name+'.settlement.json'):continue
        s=load(p);require(not s['overrun'],'assessment/control reservation overrun')
        if not s['cleanup_empty']:
            require(identity=='gpu-control-1b-v1-1-v11','only the retained wide cleanup failure')
            cleanup=load(p.with_name(identity+'.cleanup-disposition.json'))
            require(cleanup['status']=='cleanup_verified' and cleanup['settlement']==ref(p),'exact additive cleanup disposition')
            require(not any(same_process(v) for v in cleanup['identities']),'recorded failed-cell identities gone')
            resolve(cleanup['protocol']);resolve(cleanup['resource']);resolve(cleanup['journal'])
        r=load(resolve(s['resource']))
        def collect(v):
            if isinstance(v,dict):
                if 'pid' in v and 'start_ticks' in v:identities[(v['pid'],v['start_ticks'])]=v
                for x in v.values():collect(x)
            elif isinstance(v,list):
                for x in v:collect(x)
        collect(r);settlements.append(ref(p))
    require(not any(same_process(x) for x in identities.values()),'all retained owned assessment/control identities gone')
    proofs=claims=0
    for report in data['cohorts']:
        for row in report['cells']:
            if 'audit' in row:
                a=load(resolve(row['audit']));proofs+=a.get('checks',0);claims+=a.get('covered_endpoints',0)
    from lp_billion_idle import Nvml
    sensor=Nvml()
    try:sample=sensor.sample()
    finally:sensor.close()
    put(out/'device-sample.json',sample)
    put(out/'result.json',dict(status='passed',commands=commands,unchanged_numerical_bindings=unchanged,changed_bindings=changed,current_numerical_bindings=current,
        image=ref(BASE/'image-v11/binding.json'),storage_inventory_admission=ref(BASE/'disk-inventory-admission-v2/result.json'),verified_report_references=len(seen),independent_checks=proofs,assessment_claims=claims,
        owned_process_identities_checked=len(identities),all_owned_identities_gone=True,settlements=settlements,final_device_observation=ref(out/'device-sample.json'),
        data_retention=data['data_retention'],report=ref(ROOT/'docs/benchmarks/lp-billion-gpu-control-results.json'),phases=ref(ROOT/'docs/benchmarks/lp-billion-gpu-control-phases.csv'),source=ref(__file__),
        equal_update_comparisons=equal_update_comparisons,historical_report_source=historical_source,fresh_full_portable_replay=False))
    print(dict(status='passed',numerical_bindings=len(current),old_exact=len(unchanged),scoped_changes=len(changed),proofs=proofs,claims=claims),flush=True)
if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--id',required=True);main(parser.parse_args().id)
