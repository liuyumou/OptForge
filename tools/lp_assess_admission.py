"""CPU common-trajectory admission and independent scheduling replay (ADR-0039)."""
import argparse
import copy
import json
import math
from pathlib import Path
import resource
import shutil
import subprocess
import time
from benchmark_lp import source_identity,prepare_execution,provenance,reference
from lp_protocol import ROOT,read_json,write_json,file_hash,checked_reference

DEVICE='GPU-dfb2449a-9eff-e868-3597-2c448c9a8e48'

def movement(previous,current):
    if len(previous)!=len(current):raise ValueError('motion dimensions')
    if any(not math.isfinite(v) for v in previous+current):return None
    return max((abs(a/max(1.,abs(a),abs(b))-b/max(1.,abs(a),abs(b))) for a,b in zip(previous,current)),default=0.)

def replay(frames,initial,closed,final_iteration=None,final_closed=None):
    previous=initial['scaled_primal']+initial['scaled_dual'];last=0;reference_q=None;selected=[];decisions=[]
    for i,frame in enumerate(frames):
        iteration=frame['point']['iteration']
        if iteration!=(i+1)*200:raise ValueError('noncontiguous common trajectory')
        current=frame['scaled_primal']+frame['scaled_dual'];q=movement(previous,current);previous=current
        reason='first' if last==0 else 'invalid_indicator' if q is None else 'maximum_spacing' if iteration-last>=800 else 'movement' if reference_q is not None and reference_q>0 and q<=reference_q/2 else 'defer'
        due=reason!='defer';decisions.append(dict(iteration=iteration,movement=q,assess=due,reason=reason))
        if due:selected.append(i);last=iteration;reference_q=q
    fixed=next((i for i,c in enumerate(closed) if c),None)
    bounded=next((i for i in selected if closed[i]),None)
    fixed_iteration=None if fixed is None else (fixed+1)*200
    bounded_iteration=None if bounded is None else (bounded+1)*200
    if final_iteration is None and frames:
        final_iteration=frames[-1]['point']['iteration'];final_closed=closed[-1]
    if final_closed:
        if fixed_iteration is None:fixed_iteration=final_iteration
        if bounded_iteration is None:bounded_iteration=final_iteration
    return dict(decisions=decisions,selected=[(i+1)*200 for i in selected],saved_assessments=len(frames)-len(selected),
        first_fixed_success=fixed_iteration,first_bounded_success=bounded_iteration,
        added_updates=None if fixed_iteration is None or bounded_iteration is None else bounded_iteration-fixed_iteration,
        missed_transient_success=fixed_iteration is not None and bounded_iteration is None,horizon_censored=bounded_iteration is None)

def synthetic():
    def f(i,x):return dict(point=dict(iteration=i),scaled_primal=[x],scaled_dual=[])
    zero=dict(scaled_primal=[0.],scaled_dual=[])
    frames=[f(200*i,0.) for i in range(1,10)]
    cases=[]
    for truth in [[False]*9,[i==1 for i in range(9)],[i>=1 for i in range(9)],[True]*9]:
        r=replay(frames,zero,truth);assert r['selected']==[200,1000,1800];cases.append(r)
    assert cases[1]['missed_transient_success'] and cases[2]['added_updates']==600
    assert movement([float.fromhex('0x1.fffffffffffffp+1023')],[-float.fromhex('0x1.fffffffffffffp+1023')])==2.
    assert movement([0.],[float.fromhex('0x0.0000000000001p-1022')])>0.
    return cases

def run(output,binary):
    parent=read_json(ROOT/'benchmarks/configs/lp-exec-v1.json');models={i['id']:i for ref in parent['manifests'] for i in read_json(checked_reference(ROOT,ref))['instances']}
    output.mkdir(parents=True,exist_ok=False)
    identity=provenance(binary,DEVICE);prepare_execution(output,identity);frozen=output/'lp_precision_assess';shutil.copy2(binary,frozen)
    write_json(output/'contract.json',dict(decision=reference(ROOT,ROOT/'docs/decisions/ADR-0039-bounded-assessment-scheduling.md'),models=parent['timing_instances'],work=4000,gpu_seconds=0))
    rows=[];start=time.monotonic();before=resource.getrusage(resource.RUSAGE_CHILDREN)
    try:
        for name in parent['timing_instances']:
            for arithmetic in ['tuned_fp64','accumulation_fp32']:
                key=name+'-'+arithmetic;directory=output/key;directory.mkdir()
                req=dict(schema_version=1,identity='lp-assess-v1',arithmetic=arithmetic,policy='fixed_200',model_sha256=models[name]['model']['sha256'],source_tree_sha256=identity['source_tree_sha256'],executable_sha256=file_hash(frozen),code_object_sha256=file_hash(ROOT/'target/native/cuda/lp_pdhg_tuned.cubin'),device=DEVICE,options=dict(parent['solve'],iteration_limit=4000,time_limit_ms=30000),method=dict(parent['lp_settings'],iteration_limit=4000),diagnostic=True,device_buffer_bytes=1<<30)
                request=directory/'request.json';endpoint=directory/'endpoint.json';write_json(request,req)
                model=checked_reference(ROOT,models[name]['model'])
                command=[str(frozen),'trace-cpu',str(model),str(request),str(endpoint)]
                t=time.monotonic();r=subprocess.run(command,capture_output=True,text=True,timeout=1800)
                (directory/'trace.stdout').write_text(r.stdout);(directory/'trace.stderr').write_text(r.stderr)
                if r.returncode:raise ValueError('CPU trace failed '+key+': '+r.stderr[:2000])
                checked=subprocess.run([str(frozen),'replay-trace',str(model),str(request),str(endpoint)],capture_output=True,text=True,timeout=1800)
                (directory/'replay.stdout').write_text(checked.stdout);(directory/'replay.stderr').write_text(checked.stderr)
                if checked.returncode:raise ValueError('CPU trace authority failed '+key+': '+checked.stderr[:2000])
                e=read_json(endpoint);frames=[read_json(directory/ref['name']) for ref in e['witness']['traces']];assessments=json.loads(checked.stdout)
                replayed=replay(frames,e['witness']['initial'],[a['gap_closed'] for a in assessments])
                row=dict(instance=name,arithmetic=arithmetic,status=e['witness']['outcome']['status'],physical_steps=e['witness']['outcome']['physical_steps'],trace=reference(ROOT,endpoint),assessments=assessments,elapsed_seconds=time.monotonic()-t,**replayed)
                rows.append(row);write_json(output/'progress.json',dict(rows=rows));print(key,row['status'],row['saved_assessments'],flush=True)
        after=resource.getrusage(resource.RUSAGE_CHILDREN)
        result=dict(identity='gpup-assess-cpu-admission-v1',status='passed',source_tree_sha256=identity['source_tree_sha256'],executable_sha256=file_hash(frozen),oracle_sha256=file_hash(Path(__file__)),gpu_seconds=0,rows=rows,synthetic=synthetic(),elapsed_seconds=time.monotonic()-start,cpu_seconds=after.ru_utime+after.ru_stime-before.ru_utime-before.ru_stime,max_child_rss_bytes=after.ru_maxrss*1024)
        write_json(output/'admission.json',result);return result
    except BaseException as error:
        write_json(output/'failure.json',dict(reason=str(error),rows=rows,source_tree_sha256=identity['source_tree_sha256']));raise

def main():
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,default=ROOT/'artifacts/gpup-assess-v1/admission');p.add_argument('--binary',type=Path,default=ROOT/'target/release/examples/lp_precision_assess');a=p.parse_args();r=run(a.output,a.binary);print(json.dumps({k:v for k,v in r.items() if k not in ['rows','synthetic']}))
if __name__=='__main__':main()
