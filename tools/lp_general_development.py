"""Prospective broad development roster; all failures and full costs retained.

This is a diagnostic pilot, not a powered confirmation or policy selection rule.
Every model is already designated development. A subsequent version is a new
experiment; an existing cell identity is never rerun or replaced.
"""
import argparse
import json
import random
import subprocess
import time
from pathlib import Path
from lp_general_common import ROOT,BASE,load,put,ref,require
from lp_general_oracle import settings
from lp_general_device import BINARY,serial

def freeze(identity,image,admission,extended=False):
    out=BASE/identity;out.mkdir(parents=True,exist_ok=False)
    admitted=load(admission)
    require(admitted['status']=='passed' and admitted['kind']=='general-device-admission','device admission missing')
    require(set(admitted['sanitizers'])=={'memcheck','racecheck','initcheck','synccheck'},'four sanitizer admissions missing')
    require(admitted['binary']==ref(BINARY) and admitted['image']==ref(image),'admission identity differs')
    selected=[]
    generated=load(BASE/'models-development-v1/manifest.json')['models']
    for family in sorted({r['family'] for r in generated}):
        rows=[r for r in generated if r['family']==family]
        for size in [min(r['size'] for r in rows),max(r['size'] for r in rows)]:
            selected.append(min((r for r in rows if r['size']==size),key=lambda r:r['seed']))
    selected+=load(BASE/'public-development-v1/manifest.json')['models']
    if extended:selected+=load(BASE/'models-large-v1/manifest.json')['models']
    cells=[]
    for i,item in enumerate(selected):
        configurations=[(f,t) for f in ['native','fp32','fp4x1','fp4x2'] for t in [1e-7,1e-9]]
        random.Random(790090+i).shuffle(configurations)
        for order,(format,tolerance) in enumerate(configurations):
            s=settings(format);s.update(tolerance=tolerance,iteration_limit=20000 if extended else 2000,wall_ms=30000 if extended else 10000)
            if extended:s['check_interval']=500
            cells.append(dict(id=f'm{i:02d}-c{order}',model=item['model'],family=item['family'],settings=s,position=order,model_index=i))
    preflight=None
    if extended:
        from lp_general_budget import accounting
        from lp_general_common import CPU_CAPS,GPU_CAPS,NS
        cpu,gpu=accounting();cpu_reserve=len(selected)*480*4;gpu_reserve=len(selected)*480
        require(cpu['development']+cpu_reserve*NS <= CPU_CAPS['development']*NS,'complete extended CPU preflight')
        require(gpu['development']+gpu_reserve*NS <= GPU_CAPS['development']*NS,'complete extended GPU preflight')
        preflight=dict(model_jobs=len(selected),seconds_per_job=480,cpu_seconds=cpu_reserve,gpu_seconds=gpu_reserve,
            observed_charged_cpu_ns=cpu['development'],observed_charged_gpu_ns=gpu['development'])
    put(out/'freeze.json',dict(schema_version=1,kind='general-development-pilot',scientific_confirmation=False,
        selection='smallest/largest original size, lowest seed per generated family; all four public development LPs'+('; six larger independent operators' if extended else ''),
        primary='fresh-process original-certified single-solve wall time',
        cells=cells,binary=ref(BINARY),image=ref(image),admission=ref(admission),
        timing_repetitions=1,scope='diagnostic only; no inferential value pass',completion_preflight=preflight,
        failures='all failed/uncertified/deadline cells retained; no successful-only aggregate'))

def run(identity,index):
    out=BASE/identity;manifest=load(out/'freeze.json');require(ref(BINARY)==manifest['binary'],'frozen executable differs')
    image=ROOT/manifest['image']['path'];require(ref(image)==manifest['image'],'frozen image differs')
    cells=[r for r in manifest['cells'] if r['model_index']==index];require(len(cells)==8,'model roster')
    directory=out/f'm{index:02d}';directory.mkdir(exist_ok=False)
    rows=[]
    for cell in cells:
        model=ROOT/cell['model']['path'];require(ref(model)==cell['model'],'model differs')
        request=json.dumps(dict(settings=cell['settings']))+'\n'
        begin=time.monotonic_ns()
        p=subprocess.run([str(BINARY),'gpu',str(model),str(image)],input=request,text=True,capture_output=True)
        complete=time.monotonic_ns()-begin
        archive_started=time.monotonic_ns()
        raw=directory/(cell['id']+'.response.jsonl');raw.write_text(p.stdout)
        (directory/(cell['id']+'.stderr.txt')).write_text(p.stderr)
        # Process errors remain scientific outcomes; the enclosing resource job
        # can complete while preserving their explicit failure records.
        result=None;error=None
        try:
            require(p.returncode==0,'process failure');result=json.loads(p.stdout)
            require(sum(result['attempted'])==result['physical'] and sum(result['accepted'])==result['logical'],'work accounting')
        except (ValueError,KeyError) as exc:error=str(exc)
        row=dict(**cell,process_returncode=p.returncode,complete_ns=complete,response=ref(raw),error=error)
        if result is not None:
            row.update(status=result['status'],certified=result['certified'],physical=result['physical'],logical=result['logical'],
                accepted=result['accepted'],attempted=result['attempted'],recoveries=result['recoveries'],cost_ns=result['cost_ns'],
                nonzeros=result['nonzeros'],rows=result['rows'],columns=result['columns'],internal_ns=result['elapsed_ns'],
                unassigned_internal_ns=result['elapsed_ns']-sum(result['cost_ns'].values()),outer_ns=complete-result['elapsed_ns'],
                accepted_matvec_nonzeros=[2*result['nonzeros']*n for n in result['accepted']])
            proofs=[]
            for j,endpoint in enumerate([*result['assessments'],result]):
                proofs.append(serial(model,{**endpoint,'bound_proof':result.get('bound_proof',[])},cell['settings']['tolerance'],directory,f'{cell["id"]}-assessment-{j}'))
            row['independent_certificates']=proofs
        row['archive_and_independent_replay_ns']=time.monotonic_ns()-archive_started
        put(directory/(cell['id']+'.cell.json'),row);rows.append(row)
        print(dict(id=cell['id'],family=cell['family'],format=cell['settings']['format'],
            status=row.get('status',error),complete_ms=complete/1e6,accepted=row.get('accepted')),flush=True)
    put(directory/'result.json',dict(status='complete',cells=rows,freeze=ref(out/'freeze.json')))
    require(all(r['error'] is None for r in rows),'process failures retained; full reservation must be charged')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('command',choices=['freeze','run']);p.add_argument('--id',required=True)
    p.add_argument('--image',type=Path);p.add_argument('--admission',type=Path);p.add_argument('--index',type=int)
    p.add_argument('--extended',action='store_true')
    a=p.parse_args();freeze(a.id,a.image,a.admission,a.extended) if a.command=='freeze' else run(a.id,a.index)
