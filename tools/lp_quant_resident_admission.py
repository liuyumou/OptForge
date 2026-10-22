"""CPU admission on eight frozen models; useful-low refusals are never replaced."""
import concurrent.futures,json,resource,shutil,subprocess,time
from benchmark_lp import reference,source_identity
from lp_protocol import ROOT,read_json,write_json,checked_reference,file_hash
from lp_quant_admission import settings
from lp_quant_resident_common import freeze_cpu,numeric_sources
DEVICE='GPU-dfb2449a-9eff-e868-3597-2c448c9a8e48'
OUT=ROOT/'artifacts/gpup-quant-resident-v1/cpu-admission'
def configs():
    a=[dict(id=f+'-'+p,backend='lp-quant-resident-v1',settings=settings(f,p),layout='segmented') for f in ['fp16','e4m3','e5m2'] for p in ['uniform','selective']]
    a += [dict(id='resident-matched-fp64',backend='lp-quant-resident-v1',settings=settings('fp64','uniform'),layout='segmented'),dict(id='resident-bridge-fp64',backend='lp-quant-resident-v1',settings=settings('fp64','uniform'),layout='tuned')]
    a.append(dict(id='tuned-fp64',backend='cuda-lp-tuned',settings=settings('fp64','uniform'),layout='original_tuned',execution=read_json(ROOT/'benchmarks/configs/lp-quant-v1.json')['configurations'][-1]['execution']))
    return a
def make_request(c,model,binary,source,work=50000,horizon=0,seconds=30):
    parent=read_json(ROOT/'benchmarks/configs/lp-quant-v1.json');layout=c['layout']
    return dict(schema_version=1,identity='lp-quant-resident-v1',settings=c['settings'],model_sha256=file_hash(model),source_tree_sha256=source,executable_sha256=file_hash(binary),code_object_sha256=file_hash(ROOT/'target/native/cuda/lp_pdhg_quant_resident.cubin'),device=DEVICE,options=dict(parent['solve'],iteration_limit=work,time_limit_ms=seconds*1000),method=dict(parent['lp_settings'],iteration_limit=work),diagnostic=horizon!=0,layout=layout,horizon=horizon,guard='none-original-tuned-v1' if layout=='original_tuned' else 'global-then-coordinate-successor-rn-v1',reduction='segmented-serial-fp32-fp64-v1' if layout=='segmented' else 'tuned-warp32-v1',norm_policy='original-tuned-v1' if layout=='original_tuned' else 'twice-absolute-original-v1',device_buffer_bytes=1<<30)
def one(task):
    name,c,model,binary,source=task;d=OUT/(name+'-'+c['id']);d.mkdir()
    req=make_request(c,model,binary,source,work=400,horizon=400);write_json(d/'request.json',req)
    command=[str(binary),'trace-cpu',str(model),str(d/'request.json'),str(d/'endpoint.json')]
    r=subprocess.run(command,capture_output=True,text=True,timeout=900);(d/'stdout').write_text(r.stdout);(d/'stderr').write_text(r.stderr)
    row=dict(model=name,configuration=c['id'],eligible=False,useful_low=False,status='preparation_refusal',returncode=r.returncode,error=r.stderr[-2000:] if r.returncode else None)
    if r.returncode:
        if 'panicked' in r.stderr:raise ValueError('CPU admission implementation panic '+r.stderr)
        return row
    e=read_json(d/'endpoint.json');o=e['outcome'];core=o['core'];counts=o['counts']
    verify=subprocess.run([str(binary),'verify',str(model),str(d/'request.json'),str(d/'endpoint.json')],capture_output=True,text=True,timeout=900)
    (d/'verify.stdout').write_text(verify.stdout);(d/'verify.stderr').write_text(verify.stderr)
    if verify.returncode:raise ValueError('CPU independent endpoint rejection '+verify.stderr)
    accepted=core['stop'] in ['iteration_limit','work_horizon'];useful=counts['useful_windows']>0
    row.update(status=core['stop'],iterations=core['iterations'],physical=core['physical'],low_products=counts['low'],high_products=counts['high'],nonzero_low_products=counts['nonzero_t']+counts['nonzero_f'],accepted_nonzero_low_products=counts['accepted_nonzero_t']+counts['accepted_nonzero_f'],useful_windows=counts['useful_windows'],native=core['promotion']['native'],promotions=core['promotion']['transitions'],failure=core['failure'],useful_low=useful,eligible=accepted and (c['settings']['format']=='fp64' or useful),endpoint=reference(ROOT,d/'endpoint.json'))
    print(name,c['id'],row['status'],'useful',useful,flush=True)
    return row
def main():
    global OUT
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('--final',action='store_true');parser.add_argument('--accepted',action='store_true');args=parser.parse_args();args.final=args.final or args.accepted
    if args.final:OUT=ROOT/('artifacts/gpup-quant-resident-v1/accepted-admission' if args.accepted else 'artifacts/gpup-quant-resident-v1/final-admission')
    before=resource.getrusage(resource.RUSAGE_CHILDREN);own=time.process_time();start=time.monotonic();OUT.mkdir(parents=True,exist_ok=False)
    binary=OUT/'lp_precision_quant_resident';shutil.copy2(ROOT/'target/release/examples/lp_precision_quant_resident',binary)
    image=ROOT/'target/native/cuda/lp_pdhg_quant_resident.cubin';identity=freeze_cpu(OUT,binary,image,DEVICE);source=identity['source_tree_sha256'];numeric=numeric_sources();write_json(OUT/'numeric-sources.json',numeric);print('CPU source/executable/image cohort frozen',flush=True)
    parent=read_json(ROOT/'benchmarks/configs/lp-exec-v1.json');models={i['id']:i for ref in parent['manifests'] for i in read_json(checked_reference(ROOT,ref))['instances']}
    tasks=[(n,c,checked_reference(ROOT,models[n]['model']),binary,source) for n in parent['timing_instances'] for c in configs()]
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:rows=list(pool.map(one,tasks))
    after=resource.getrusage(resource.RUSAGE_CHILDREN)
    receipt=dict(identity='gpup-quant-resident-admission-v1',status='passed',rows=rows,source_tree_sha256=source,source_after=source_identity(),executable_sha256=file_hash(binary),image_sha256=file_hash(ROOT/'target/native/cuda/lp_pdhg_quant_resident.cubin'),cpu_seconds=time.process_time()-own+after.ru_utime+after.ru_stime-before.ru_utime-before.ru_stime,elapsed_seconds=time.monotonic()-start,max_child_rss_bytes=after.ru_maxrss*1024,gpu_seconds=0)
    if numeric!=numeric_sources():raise ValueError('CPU numerical sources changed during admission')
    receipt.update(numerical_sources=numeric,source_archive=reference(ROOT,OUT/'source.tar'))
    write_json(OUT/'admission.json',receipt)
    dest=ROOT/'docs/benchmarks/data/quant-resident';dest.mkdir(parents=True,exist_ok=True)
    if args.final:
        initial=ROOT/'artifacts/gpup-quant-resident-v1/cpu-admission/admission.json';shutil.copy2(initial,dest/'cpu-admission-initial.json')
        if args.accepted:shutil.copy2(ROOT/'artifacts/gpup-quant-resident-v1/final-admission/admission.json',dest/'cpu-admission-intermediate.json')
        old=read_json(initial);oldrows={(r['model'],r['configuration']):r for r in old['rows']}
        for row in rows:
            oldrow=oldrows[(row['model'],row['configuration'])]
            if row['eligible']!=oldrow['eligible']:raise ValueError('metadata-only admission eligibility changed')
            if 'endpoint' in row:
                left=read_json(checked_reference(ROOT,row['endpoint']))['outcome'];left.pop('first_certified_iteration',None)
                right=read_json(checked_reference(ROOT,oldrow['endpoint']))['outcome']
                if json.dumps(left,sort_keys=True)!=json.dumps(right,sort_keys=True):raise ValueError('metadata-only numerical/work outcome changed')
        receipt['initial_numerical_outcomes_identical']=True
    write_json(OUT/'admission.json',receipt)
    write_json(dest/'cpu-admission.json',receipt)
    print(json.dumps({k:v for k,v in receipt.items() if k!='rows'}),flush=True)
if __name__=='__main__':main()
