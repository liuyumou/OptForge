"""Source-bound exact small continuations, original serial checking and sanitizers."""
import argparse
import copy
import json
from pathlib import Path
import shutil
import subprocess
from lp_billion_common import BASE, ROOT, put, load, ref, resolve, require
from lp_billion_arrays import read, write
from lp_general_models import generate
from lp_general_oracle import settings

OLD = ROOT/'artifacts/gpup-general-v1/scale-image-v14'
SERIAL = ROOT/'artifacts/gpup-checker2-v1/build-v5/executor'
IMAGE = BASE/'image-v1'

def gate_identity(kind,version):
    # The first v3 memcheck reservation stopped on its CPU-only fallback fixture.
    # Its failed receipt remains; the corrected harness has a fresh identity.
    if version==9:return f'bounded-memory-{kind}-v1'
    if version==8:return f'timing-{kind}-v1'
    if version in [5,6,7]:return f'packing-{kind}-v{version-4}'
    if version==4:return f'memory-{kind}-v1'
    if version==3 and kind=='racecheck':return 'array-racecheck-v6'
    return 'array-memcheck-v4' if (kind,version)==('memcheck',3) else f'array-{kind}-v{version}'

def call(command, requests, out, name):
    request=out/(name+'.request.json');put(request,requests)
    p=subprocess.run(list(map(str,command)),input=''.join(json.dumps(r)+'\n' for r in requests),text=True,capture_output=True)
    (out/(name+'.stdout.jsonl')).write_text(p.stdout);(out/(name+'.stderr')).write_text(p.stderr)
    require(p.returncode==0,'admission process '+name+': '+p.stderr[-1000:])
    result=[json.loads(line) for line in p.stdout.splitlines()]
    require(len(result)==len(requests),'response coverage '+name)
    return result

def seal(version=1):
    quality = {1:'array-quality-v4',2:'array-quality-v5',3:'array-quality-v6',4:'memory-quality-v1',5:'packing-quality-v1',6:'packing-quality-v2',7:'packing-quality-v5',8:'timing-quality-v3',9:'bounded-memory-quality-v1'}[version]
    require(load(BASE/'resources'/(quality+'.settlement.json'))['status']=='passed', 'array admission')
    ownership = 'gpu-ownership-v1' if version == 1 else 'ownership-audit-v2'
    require(load(BASE/'resources'/(ownership+'.settlement.json'))['status']=='passed','operational GPU ownership admission')
    for item in load(BASE/'sources'/quality/'manifest.json')['sources']:
        if item['original']['path'].endswith(('.rs','.cu')) or Path(item['original']['path']).name.startswith('Cargo.'):
            resolve(item['original']);resolve(item['retained'])
    IMAGE.mkdir(exist_ok=False)
    for source,name in [(BASE/'target/release/billion','executor'),(BASE/'target/release/lp-billion-lowbit','legacy-interface'),(OLD/'tensor.cubin','tensor.cubin')]:
        shutil.copyfile(source,IMAGE/name);(IMAGE/name).chmod(0o755 if name!='tensor.cubin' else 0o644)
    require(ref(IMAGE/'tensor.cubin')['sha256']==ref(ROOT/'artifacts/gpup-general-v1/fast-image-v10/tensor.cubin')['sha256'],'unchanged CUDA image')
    binding=dict(executor=ref(IMAGE/'executor'),legacy=ref(IMAGE/'legacy-interface'),cuda=ref(IMAGE/'tensor.cubin'),
        source_manifest=ref(BASE/'sources'/quality/'manifest.json'),old_executor=ref(OLD/'executor'),cpu_tests={1:48,2:49,3:51,4:52,5:53,6:53,7:54,8:57,9:58}[version],clippy_passed=True,
        ownership_admission=ref(BASE/'resources'/(ownership+'.settlement.json')))
    if version>=3:
        built=load(BASE/({3:'build-prepare-v3',4:'build-memory-v1',5:'build-packing-v1',6:'build-packing-v2',7:'build-packing-v5',8:'build-timing-v3',9:'build-bounded-memory-v1'}[version]+'/result.json'))
        require(built['status']=='passed' and built['quality'],'GPU preparation CPU quality')
        binding['cpu_tests']=built['rust_tests']
        require(built['cuda_source']==ref(ROOT/'research/lp-billion-lowbit/cuda/prepare.cu'),'compiled preparation source binding')
        shutil.copyfile(resolve(built['cuda']),IMAGE/'prepare.cubin')
        binding['preparation']=ref(IMAGE/'prepare.cubin')
        binding['preparation_source']=ref(ROOT/'research/lp-billion-lowbit/cuda/prepare.cu')
    put(IMAGE/'binding.json',binding)

def unpack(r):
    r=copy.deepcopy(r)
    for e in [*r.get('assessments',[]),r]:
        if 'endpoint' in e:
            ep=e.pop('endpoint')
            e.update(primal=read(BASE,ep['primal']).tolist(),dual=read(BASE,ep['dual']).tolist())
        cert=e.get('certificate',{})
        if 'certificate_dual_array' in cert:cert['certificate_dual']=read(BASE,cert.pop('certificate_dual_array')).tolist()
    return r

def canonical(r):
    result={k:v for k,v in unpack(r).items() if k not in ['model_sha256','input_ns','elapsed_ns','cost_ns','cached_assessments','device_bytes_upper','gpu_preparation','preparation_detail_ns','solver_profile']}
    if 'fast_config' in result:result['fast_config'].pop('gpu_preparation',None)
    return result

def validate_timings(response, required_profile=False):
    require(not required_profile or 'solver_profile' in response, 'requested solver profile missing')
    if 'solver_profile' in response:
        from lp_billion_timing import validate_profile
        validate_profile(response)
    if 'preparation_detail_ns' in response:
        detail=response['preparation_detail_ns']
        require(set(detail)=={'engine','operator','packing','control_initialization'} and
                all(type(v) is int and v>=0 for v in detail.values()),'preparation timing partitions')
        require(sum(detail.values())==response['cost_ns']['host_preparation'],'complete preparation timing coverage')

def serial(model,e,t,out,name):
    endpoint=out/(name+'.endpoint.json');result=out/(name+'.serial.json')
    put(endpoint,dict(model_sha256=ref(model)['sha256'],primal=e['primal'],dual=e['certificate'].get('certificate_dual',e['dual']),transport='completed'))
    p=subprocess.run([str(SERIAL),'check-serial',str(model),str(endpoint),'certified-'+('1e-9' if t==1e-9 else '1e-7'),str(result)],text=True,capture_output=True)
    require(p.returncode==0,'original serial checking '+p.stderr)
    proof=load(result)
    for k in ['accepted','feasible','objective','bound','gap_upper']:require(proof[k]==e['certificate'][k],'original serial differs '+k)
    return ref(result)

def gpu(identity,sanitizer=None):
    require(load(BASE/'resources/billion-native-v2.settlement.json')['status']=='passed','fresh native acceptance')
    out=BASE/identity;out.mkdir(exist_ok=False);rows=[]
    preparation=None
    if 'preparation' in load(IMAGE/'binding.json'):
        from lp_billion_prepare_admit import suite
        preparation=suite(out,IMAGE,sanitizer)
    for family,size in [('dense',257),('irregular',4097),('rectangular',4097),('ill_scaled',65),('dense_blocks',129)]:
        doc,_=generate(family,size,861700+size);model=out/(family+'.json');put(model,doc)
        p=subprocess.run([str(IMAGE/'executor'),'convert',str(model),str(BASE)],text=True,capture_output=True)
        require(p.returncode==0,'array conversion '+p.stderr)
        compact=out/(family+'.arrays.json');put(compact,json.loads(p.stdout))
        for fmt in ['native','fp32','fp4x1','fp4x2']:
            for fault in ([None] if sanitizer else [None,'force_recovery_after','cancel_after']):
                s={**settings(fmt),'iteration_limit':32,'check_interval':16}
                if fault:s[fault]=3
                r=dict(settings=s,tensor=dict(control_interval=8,min_tile_nnz=128),fast=dict(host_reductions=True,host_preparation=True,host_certificates=True,auto_schedule=True))
                name=f'{family}-{fmt}-{fault}'
                cmd=[str(IMAGE/'executor'),'solve',str(compact),str(BASE),str(IMAGE/'tensor.cubin')]
                if sanitizer:
                    from lp_billion_prepare_admit import instrument
                    cmd=instrument(cmd,sanitizer,out/(name+'.sanitizer'))
                candidate=copy.deepcopy(r)
                if preparation is not None:candidate['fast']['gpu_preparation']=True
                if IMAGE.name in ['image-v8','image-v9']:candidate['profile']=True
                after=call(cmd,[candidate],out,name+'-new')[0]
                validate_timings(after, candidate.get('profile',False))
                if preparation is not None:
                    require(after.get('gpu_preparation',{}).get('backend')=='gpu-fp64','actual GPU preparation '+name)
                before=call([OLD/'executor','gpu-fast',model,OLD/'tensor.cubin'],[r],out,name+'-old')[0]
                require(canonical(before)==canonical(after),'exact original continuation differs '+name)
                response=out/(name+'.response.json');put(response,after)
                decoded=unpack(after)
                proofs=[serial(model,e,s['tolerance'],out,name+'-'+str(i)) for i,e in enumerate([*decoded['assessments'],decoded])]
                if sanitizer:
                    text=(out/(name+'.sanitizer')).read_text()
                    require('ERROR SUMMARY: 0 errors' in text or 'RACECHECK SUMMARY: 0 hazards' in text,'sanitizer summary')
                rows.append(dict(case=name,response=ref(response),serial=proofs,exact=True))
    put(out/'result.json',dict(status='passed',sanitizer=sanitizer,rows=rows,image=ref(IMAGE/'binding.json'),preparation=preparation))
    print(dict(status='passed',comparisons=len(rows),sanitizer=sanitizer),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['seal','gpu']);p.add_argument('--id');p.add_argument('--version',type=int,choices=[1,2,3,4,5,6,7,8,9],default=1);p.add_argument('--sanitizer',choices=['memcheck','racecheck','initcheck','synccheck']);a=p.parse_args()
    IMAGE=BASE/f'image-v{a.version}'
    if a.action=='seal':seal(a.version)
    else:gpu(a.id,a.sanitizer)
