"""Frozen fresh-process LP cells with explicit capacity refusals and portable endpoints."""
import argparse
import json
import math
import subprocess
import time
from pathlib import Path
from lp_billion_common import BASE, ROOT, put, load, ref, resolve, require
from lp_billion_arrays import DTYPES
from lp_general_oracle import settings

IMAGE=BASE/'image-v1'
GIB=1<<30

def endpoint_bytes(model,iterations):
    return (math.ceil(iterations/500)+2)*8*(model['columns']+2*model['rows'])

def capacity(model, lane):
    m,n,z=model['rows'],model['columns'],model['nonzeros']
    nzcap=1<<(max(1,z)-1).bit_length()
    ncap=1<<max(1,n).bit_length();mcap=1<<max(1,m).bit_length()
    dim=m+n;tiles=model['canonical_tiles'] if lane=='fp4x2' else 0
    residual=z-model['covered_nnz'] if tiles else z
    # Original arrays, exact-length transpose, engine values and operator copies.
    resident=40*z+24*nzcap+56*m+84*n
    # Two controller states (live + checkpoint), product workspace, unscaled
    # endpoint and the original serial enclosure's term and reduction copies.
    workspace=14*max(m,n)+16*ncap+8*mcap
    certificate=max(48*dim+8*m,24*ncap+24*n+128)
    solve_peak=resident+32*dim+workspace+8*dim+certificate
    packed=0
    if lane=='fp4x2':
        # BTreeMap coefficients/codes, up to doubled output Vec capacities,
        # both residuals, coverage flags, cursors and half-tile lists.
        cap=lambda size:1<<(max(4,size)-1).bit_length()
        # Each orientation is appended independently; capacities follow the
        # frozen Rust Vec doubling schedule. Account for each actual array.
        packed=(8*cap(256*tiles)+8*cap(4*tiles)+8*cap(2*tiles)
                +4*(cap((m+15)//16+1)+cap((n+15)//16+1))
                +4*dim+4*(cap(m+1)+cap(n+1))+24*cap(residual))
        packing_peak=resident+(10496+8+256)*tiles+packed+2*z+5*n+2*dim
        solve_peak+=packed if tiles else 0
    else:packing_peak=resident
    # Includes allocator growth, CUDA context host storage and 32 MiB I/O chunks.
    host=max(solve_peak,packing_peak)+8*GIB
    # Original CSR/CSC, reference vectors, state/encoding and problem vectors.
    device=24*z+56*dim+32*n+16*m+40*((n+31)//32+(m+31)//32)+256
    if lane!='native':device+=8*residual
    if tiles:
        device+=4*dim+8*residual+4*((m+15)//16+(n+15)//16+2)
        device+=4*tiles*(524+64) # Includes partial products even if combined.
    device+=256<<20
    physical_index=2*tiles*2*128
    admitted=host<=128*GIB and device<=80*GIB and physical_index<2**32
    endpoint_max=endpoint_bytes(model,5000)
    return dict(host_bytes=host,device_bytes=device,endpoint_bytes_upper=endpoint_max,
        host_gib=math.ceil(host/GIB),device_gib=math.ceil(device/GIB),
        admitted=admitted,physical_fragment_index_upper=physical_index,
        reason=None if admitted else 'complete host/device/index allowance exceeds approved ceiling',
        original_nonzeros=z,canonical_tiles=tiles,formula_version=2)

def freeze(identity, model_paths, lanes, iterations, wall_ms, seconds, ladder=False, version=1):
    out=BASE/identity;require(not out.exists(),'fresh cohort identity')
    require(version in [1,2,3], 'admitted image version')
    image=BASE/f'image-v{version}'
    proofs=[]
    from lp_billion_admit import gate_identity
    if version==3:
        cpu=BASE/'resources/operational-cpu-v9.settlement.json'
        require(load(cpu)['status']=='passed','post-observation CPU readmission')
        proofs.append(ref(cpu))
        observation=BASE/'resources/idle-confirmation-v5.settlement.json'
        stopped=load(observation)
        require(stopped['status']=='refused' and stopped['cleanup_empty'] and not stopped['overrun'],'retained observation interruption')
        proofs.append(ref(observation))
    for identity in (['array-memcheck-v3','array-racecheck-v3','array-racecheck-v4'] if version==3 else []):
        failed=BASE/'resources'/(identity+'.settlement.json')
        failure=load(failed)
        require(failure['status']=='refused' and failure['cleanup_empty'] and not failure['overrun'],'retained sanitizer harness failure')
        proofs.append(ref(failed))
    for name in ['billion-native-v2',*[gate_identity(k,version) for k in ['gpu','memcheck','racecheck','initcheck','synccheck']],'generator-admission-v1','ownership-audit-v2']:
        p=BASE/'resources'/(name+'.settlement.json');require(load(p)['status']=='passed','admission '+name);proofs.append(ref(p))
    for p in sorted((BASE/'resources').glob('*.cleanup-disposition.json')):
        disposition=load(p);proofs.append(ref(p))
        for name in [disposition['cpu_admission_job'],disposition['admission_job']]:
            q=BASE/'resources'/(name+'.settlement.json')
            require(load(q)['status']=='passed','operational readmission '+name)
            proofs.append(ref(q))
    plans=sorted((BASE/'operational-readmissions').glob('*.json'))
    superseded=set()
    superseded_failed=set()
    for p in plans:
        names=load(p).get('supersedes_never_started',[])
        superseded.update([names] if isinstance(names,str) else names)
        superseded_failed.update(load(p).get('supersedes_failed',[]))
    for name in superseded:
        require(not (BASE/'resources'/(name+'.reservation.json')).exists(),'superseded job was already attempted')
    for name in superseded_failed:
        failed=BASE/'resources'/(name+'.settlement.json')
        require(load(failed)['status']=='refused','superseded failed admission status')
        proofs.append(ref(failed))
    for p in plans:
        plan=load(p);proofs.append(ref(p))
        for name in [plan['cpu_admission_job'],plan['admission_job']]:
            if name in superseded or name in superseded_failed:
                continue
            q=BASE/'resources'/(name+'.settlement.json')
            require(load(q)['status']=='passed','prospective readmission '+name)
            proofs.append(ref(q))
    cells=[]
    for index,path in enumerate(model_paths):
        model=load(path);require(model['status']=='generated','complete generated input')
        original=resolve(model['model']);proof_path=original.parent/'construction-check.json'
        proof=load(proof_path)
        require(proof['accepted'] and proof['model']==model['model'],'strict original construction check')
        order=lanes[index%len(lanes):]+lanes[:index%len(lanes)]
        for lane in order:
            cell_seconds=seconds if isinstance(seconds,int) else seconds[model['family']]
            cell_wall=wall_ms if isinstance(wall_ms,int) else wall_ms[model['family']]
            memory=capacity(model,lane)
            # Capacity pilots have fewer endpoint snapshots than the final cohort.
            memory['endpoint_bytes_upper']=endpoint_bytes(model,iterations)
            cell=dict(id=f'{identity}-{index}-{lane}',model=model['model'],model_result=ref(path),construction_check=ref(proof_path),lane=lane,memory=memory,
                status='pending' if memory['admitted'] else 'unsupported_capacity',seconds=cell_seconds,
                request=dict(settings={**settings(lane),'iteration_limit':iterations,'check_interval':500,'wall_ms':cell_wall},
                    tensor=dict(control_interval=100,min_tile_nnz=128),
                    fast=dict(host_reductions=True,host_preparation=True,host_certificates=True,auto_schedule=True)))
            if version==3:cell['request']['fast']['gpu_preparation']=True
            cells.append(cell)
    from lp_billion_budget import accounting
    from lp_billion_common import CPU_CAPS,GPU_CAPS,NS,disk_bytes,DISK_LIMIT
    cpu,gpu=accounting();planned=sum(c['seconds'] for c in cells if c['status']=='pending')
    require(cpu['development']+4*planned*NS<=CPU_CAPS['development']*NS,'whole-cohort CPU admission')
    require(gpu['development']+planned*NS<=GPU_CAPS['development']*NS,'whole-cohort GPU admission')
    endpoint_storage=sum(c['memory']['endpoint_bytes_upper'] for c in cells if c['status']=='pending')
    require(disk_bytes()+endpoint_storage+(2<<30)<=DISK_LIMIT,'whole-cohort owned storage admission')
    out.mkdir(exist_ok=False)
    put(out/'freeze.json',dict(schema_version=1,status='frozen',development=True,ladder=ladder,cells=cells,admission=proofs,
        image=ref(image/'binding.json'),harness=ref(__file__),plan=ref(ROOT/'docs/plans/lp-billion-execution.md'),
        amendments=[ref(p) for p in sorted((ROOT/'docs/specifications').glob('SPEC-0046-amendment-*.md'))],
        claim='Single fresh-process solves, one rotated repetition; no confirmation.'))
    return out/'freeze.json'

def worker(freeze_path, index):
    manifest=load(freeze_path);cell=manifest['cells'][index]
    require(cell['status']=='pending','capacity refusal is not executable')
    model=resolve(cell['model'])
    binding=load(resolve(manifest['image']));executor=resolve(binding['executor']);cuda=resolve(binding['cuda'])
    if 'preparation' in binding:
        require(resolve(binding['preparation'])==cuda.with_name('prepare.cubin'),'preparation module binding')
    out=BASE/cell['id'];out.mkdir(exist_ok=False)
    put(out/'request.json',cell['request'])
    started=time.monotonic_ns()
    p=subprocess.run([str(executor),'solve',str(model),str(BASE),str(cuda)],
        input=json.dumps(cell['request'])+'\n',text=True,capture_output=True)
    returned=time.monotonic_ns()
    (out/'stdout.jsonl').write_text(p.stdout);(out/'stderr').write_text(p.stderr)
    require(p.returncode==0,'LP process failed: '+p.stderr[-1000:])
    response=json.loads(p.stdout)
    require(response['model_sha256']==cell['model']['sha256'],'original model binding')
    require(response['nonzeros']==load(model)['nonzeros'],'original matrix size')
    require(response['device_bytes_upper']<=cell['memory']['device_bytes'],'actual allocation exceeds preflight')
    require(response.get('gpu_preparation',{}).get('allocated_bytes',0)<=cell['memory']['device_bytes'],'preparation allocation exceeds preflight')
    require(sum(response['attempted'])==response['physical'] and sum(response['accepted'])==response['logical'],'complete work accounting')
    require(all(r['restored_exact'] for r in response['recoveries']),'recovery exactness')
    from lp_billion_portable import arrays
    chunks={c['sha256']:c['bytes'] for a in arrays(response) for c in a['chunks']}
    endpoint_storage=sum(chunks.values())
    require(endpoint_storage<=cell['memory']['endpoint_bytes_upper'],'complete endpoint and certificate witness storage')
    put(out/'response.json',response)
    put(out/'result.json',dict(status='measured',cell=cell['id'],response=ref(out/'response.json'),freeze=ref(freeze_path),
        process_ns=returned-started,response_transport_ns=time.monotonic_ns()-returned,
        fresh_process_ns=time.monotonic_ns()-started,solver_status=response['status'],certified=response['certified'],endpoint_bytes=endpoint_storage))
    print(dict(cell=cell['id'],status=response['status'],logical=response['logical'],physical=response['physical'],
        seconds=(returned-started)/1e9,cost_ns=response['cost_ns'],device_bytes=response['device_bytes_upper']),flush=True)

def check(identity,response_path,model_path,all_endpoints=False):
    out=BASE/identity;out.mkdir(exist_ok=False);r=load(response_path)
    endpoints=[*r['assessments'],r] if all_endpoints else [r]
    requests=[dict(settings=r['settings'],endpoint=e['endpoint']) for e in endpoints]
    put(out/'requests.json',requests)
    start=time.monotonic_ns()
    p=subprocess.run([str(IMAGE/'executor'),'assess',str(model_path),str(BASE)],input=''.join(json.dumps(q)+'\n' for q in requests),text=True,capture_output=True)
    elapsed=time.monotonic_ns()-start
    (out/'stdout.jsonl').write_text(p.stdout);(out/'stderr').write_text(p.stderr)
    require(p.returncode==0,'independent original-array check '+p.stderr)
    results=[json.loads(line) for line in p.stdout.splitlines()];require(len(results)==len(endpoints),'assessment coverage')
    for a,e in zip(results,endpoints):
        require(a['model_sha256']==ref(model_path)['sha256'],'assessment model binding')
        for k,v in e['certificate'].items():require(a[k]==v,'original serial certificate differs '+k)
    put(out/'result.json',dict(status='passed',response=ref(response_path),model=ref(model_path),checks=len(results),
        final_only=not all_endpoints,elapsed_ns=elapsed,results=results,checker_image=ref(IMAGE/'binding.json'),certificate_source=ref(ROOT/'crates/optimizer-lp/src/certify.rs')))

def construction(model_path):
    out=model_path.parent
    request=dict(settings=settings('native'),endpoint=load(out/'construction.json'))
    started=time.monotonic_ns()
    p=subprocess.run([str(IMAGE/'executor'),'assess',str(model_path),str(BASE)],input=json.dumps(request)+'\n',text=True,capture_output=True)
    elapsed=time.monotonic_ns()-started
    (out/'construction-check.stdout').write_text(p.stdout);(out/'construction-check.stderr').write_text(p.stderr)
    require(p.returncode==0,'construction checking process '+p.stderr)
    proof=json.loads(p.stdout)
    require(proof['model_sha256']==ref(model_path)['sha256'],'construction original identity')
    put(out/'construction-check.json',dict(accepted=proof['accepted'],model=ref(model_path),certificate=proof,elapsed_ns=elapsed))
    require(proof['accepted'],'strict original construction certificate refused')
    print(dict(model=str(model_path),construction_certified=True,seconds=elapsed/1e9),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();sub=p.add_subparsers(dest='action',required=True)
    w=sub.add_parser('worker');w.add_argument('freeze',type=Path);w.add_argument('index',type=int)
    c=sub.add_parser('check');c.add_argument('--id',required=True);c.add_argument('--response',type=Path,required=True);c.add_argument('--model',type=Path,required=True);c.add_argument('--all',action='store_true')
    k=sub.add_parser('construction');k.add_argument('model',type=Path)
    a=p.parse_args()
    if a.action=='worker':worker(a.freeze,a.index)
    elif a.action=='check':check(a.id,a.response,a.model,a.all)
    else:construction(a.model)
