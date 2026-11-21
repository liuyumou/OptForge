"""Final source/cleanup/proof verification for GPU packing, without historical rewrites."""
import subprocess,sys
from pathlib import Path
from lp_billion_common import BASE,ROOT,load,put,ref,resolve,require
from lp_confirmation2_supervisor import same_process
CHANGED={f'research/lp-billion-lowbit/{p}' for p in ['src/billion.rs','src/fast_device.rs','src/lib.rs','src/operator.rs','tests/contracts.rs']}
ADDED=[f'research/lp-billion-lowbit/{p}' for p in ['src/gpu_packing.rs','src/bin/packing_check.rs','cuda/pack.cu']]

def main():
    out=BASE/'gpu-pack-verification-v1';out.mkdir(exist_ok=False);commands=[]
    for name,cmd in [('harness',[sys.executable,'-B','-m','unittest','discover','-s','tests/integration','-p','test_lp_billion*.py']),('documentation',['python3','-B','tools/build_docs.py']),('diff',['git','diff','--check'])]:
        p=subprocess.run(cmd,cwd=ROOT,text=True,capture_output=True,timeout=120)
        (out/(name+'.stdout')).write_text(p.stdout);(out/(name+'.stderr')).write_text(p.stderr)
        require(p.returncode==0,name+' final verification failed')
        commands.append(dict(name=name,stdout=ref(out/(name+'.stdout')),stderr=ref(out/(name+'.stderr'))))
        print(name,p.stdout[-400:],p.stderr[-400:],flush=True)
    prior=load(BASE/'complete-device-checkpoint-v1.json');old_image=load(BASE/'image-v9/binding.json')
    old_sources={x['original']['path']:x for x in load(resolve(old_image['source_manifest']))['sources']}
    unchanged=[];changed=[];current=[]
    for item in prior['current_numerical_bindings']:
        if item['namespace']=='repo' and item['path'] in CHANGED:
            retained=old_sources[item['path']]['retained'];resolve(retained)
            require(retained['sha256']==item['sha256'],'exact historical source retained')
            new=ref(ROOT/item['path']);changed.append(dict(previous=item,retained=retained,current=new));current.append(new)
        else:resolve(item);unchanged.append(item);current.append(item)
    require({x['previous']['path'] for x in changed}==CHANGED,'exact scoped integration changes only')
    for p in ADDED:current.append(ref(ROOT/p))
    image=load(BASE/'image-v10/binding.json')
    for item in image['files'].values():resolve(item)
    for key in ['cuda','preparation']:require(image[key]['sha256']==old_image[key]['sha256'],'unchanged numerical CUDA '+key)
    for item in load(resolve(image['source_manifest']))['sources']:
        if item['original']['path'].endswith(('.rs','.cu')) or Path(item['original']['path']).name.startswith('Cargo.'):
            resolve(item['original']);resolve(item['retained'])
    counter=load(BASE/'disk-inventory-admission-v2/result.json')
    require(counter['status']=='passed','independent exact storage inventory audit')
    for key in ['binding','recompiled','source','retained_source']:resolve(counter[key])
    for name in ['operational-cpu-v26','operational-gpu-v21']:
        gate=load(BASE/'resources'/(name+'.settlement.json'))
        require(gate['status']=='passed' and gate['cleanup_empty'] and not gate['overrun'],'fresh resource-source operational admission')
    data=load(ROOT/'docs/benchmarks/lp-billion-gpu-packing-results.json');seen=set()
    def refs(v):
        if isinstance(v,dict):
            if {'namespace','path','sha256','bytes'}<=v.keys():
                key=(v['namespace'],v['path'],v['sha256'])
                if key not in seen:resolve(v);seen.add(key)
            else:
                for x in v.values():refs(x)
        elif isinstance(v,list):
            for x in v:refs(x)
    refs(data)
    identities={};settlements=[]
    operational={f'operational-cpu-v{i}' for i in range(22,27)} | {f'operational-gpu-v{i}' for i in range(19,22)}
    for p in sorted((BASE/'resources').glob('*.settlement.json')):
        identity=p.name.removesuffix('.settlement.json')
        if not identity.startswith(('gpu-pack-','disk-inventory-')) and identity not in operational:continue
        if identity.startswith('gpu-pack-verification-'):continue
        s=load(p);require(s['cleanup_empty'] and not s['overrun'],'packing reservation cleanup/overrun')
        r=load(resolve(s['resource']))
        def collect(v):
            if isinstance(v,dict):
                if 'pid' in v and 'start_ticks' in v:identities[(v['pid'],v['start_ticks'])]=v
                for x in v.values():collect(x)
            elif isinstance(v,list):
                for x in v:collect(x)
        collect(r);settlements.append(ref(p))
    require(not any(same_process(x) for x in identities.values()),'all retained owned packing identities gone')
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
        image=ref(BASE/'image-v10/binding.json'),storage_inventory_admission=ref(BASE/'disk-inventory-admission-v2/result.json'),verified_report_references=len(seen),independent_checks=proofs,assessment_claims=claims,
        owned_process_identities_checked=len(identities),all_owned_identities_gone=True,settlements=settlements,final_device_observation=ref(out/'device-sample.json'),
        report=ref(ROOT/'docs/benchmarks/lp-billion-gpu-packing-results.json'),phases=ref(ROOT/'docs/benchmarks/lp-billion-gpu-packing-phases.csv'),source=ref(__file__),fresh_full_portable_replay=False))
    print(dict(status='passed',numerical_bindings=len(current),old_exact=len(unchanged),scoped_changes=len(changed),proofs=proofs,claims=claims),flush=True)
if __name__=='__main__':main()
