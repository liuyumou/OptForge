"""Recover only untouched frozen confirmation cells after launcher setup failures.

The original manifest, numerical sources, deadlines, failed full charges and
existing endpoints remain exact. CPU-selected candidates require no GPU lease.
GPU chunks stop prospectively before their remaining process/cleanup allowance
could be exhausted; no active scientific child is restarted.
"""
import argparse
import json
from pathlib import Path
import sys
import time
from lp_sp_pricing_budget import BASE,ROOT,CPU,GPU,NS,binding,put,run,accounting
from lp_sp_pricing_campaign import read,validate,verify
from lp_sp_pricing_baselines import PYTHON,launch,audit


def freeze(identity,original):
    source=read(original);validate(source)
    if not (original.parent/'completed.json').exists():raise RuntimeError('original driver has not finished')
    out=BASE/identity;out.mkdir(exist_ok=False);(out/'cells').mkdir()
    untouched=[];retained=[]
    for cell in source['cells']:
        directory=original.parent/'cells'/cell['id']
        if (directory/'started.json').exists():
            retained.append(dict(id=cell['id'],started=binding(directory/'started.json')))
        elif directory.exists():
            if not (directory/'unsupported.json').exists():raise RuntimeError('ambiguous existing cell')
            retained.append(dict(id=cell['id'],unsupported=binding(directory/'unsupported.json')))
        else:untouched.append(cell)
    # All six failures occurred at directory creation, before a started marker
    # or a scientific child. Validate those exact receipts, including charges.
    failures=[]
    for family in ['dense','irregular','wide','tall','coupled','ill_scaled']:
        path=BASE/'resources'/f'confirmation-v1-{family}-solve.settlement.json';receipt=read(path)
        if receipt['status']!='refused' or not receipt['cleanup_empty'] or receipt['overrun']:
            raise RuntimeError('unexpected original launcher disposition')
        if receipt['cpu_ns']<6720*NS or receipt['gpu_ns']<1680*NS:raise RuntimeError('missing original full charge')
        failures.append(binding(path))
    if source['configuration']['gpu']:raise RuntimeError('recovery requires the preselected CPU candidate')
    put(out/'freeze.json',dict(schema=1,status='untouched_frozen_cells_only',original=binding(original),
        cells=untouched,retained=retained,failures=failures,source=binding(__file__),
        models=source['models'],configuration=source['configuration'],
        numerical_sources_unchanged=True,process_windows_unchanged=True,
        scheduling='sequential CPU candidate block; sequential GPU baseline chunks; cold independent CPU audits',
        order_deviation='six untouched families preserve models, repetitions and per-lane order but lose cross-lane interleaving; report descriptive timings with this limitation',
        output_parent_precreated=True))
    print(json.dumps(dict(untouched=len(untouched),retained=len(retained))),flush=True)


def validated(path):
    f=read(path);verify(f['source']);verify(f['original']);validate(read(f['original']['path']))
    if not (path.parent/'cells').is_dir():raise RuntimeError('missing output parent before reserving solves')
    return f


def pending(f,out,gpu):
    return [c for c in f['cells'] if (c['lane']!='practical')==gpu and c['status']=='pending'
            and not (out/'cells'/c['id']).exists()]


def worker(path,gpu,allowance,chunk):
    f=validated(path);out=path.parent;start=time.monotonic();completed=[]
    for cell in pending(f,out,gpu):
        model=f['models'][cell['model_index']]
        # Allow process deadline + owned-child termination + publication margin.
        if time.monotonic()-start+model['outer_seconds']+35>allowance:break
        directory=out/'cells'/cell['id']
        if directory.exists():raise RuntimeError('scientific cell already started')
        process=launch(cell['lane'],Path(model['portable']['path']),Path(model['rational']['path']),directory,
            model['native_seconds'],model['outer_seconds'],f['configuration'])
        completed.append(cell['id']);print(json.dumps(dict(cell=cell['id'],process=process)),flush=True)
    put(out/(chunk+'-completed.json'),dict(attempted=completed,remaining=len(pending(f,out,gpu)),gpu=gpu))


def audit_all(path):
    f=validated(path);out=path.parent;rows=[]
    for cell in f['cells']:
        model=f['models'][cell['model_index']];directory=out/'cells'/cell['id']
        if cell['status']=='unsupported_capacity':
            rows.append(dict(cell=cell['id'],lane=cell['lane'],status='unsupported_capacity',accepted=False,timely=False,attempted=False));continue
        if not (directory/'started.json').exists():raise RuntimeError('untouched cell still pending: '+cell['id'])
        process=read(directory/'process.json') if (directory/'process.json').exists() else {}
        checked=audit(cell['lane'],Path(model['portable']['path']),Path(model['rational']['path']),directory)
        response=read(directory/'response.json') if (directory/'response.json').exists() else {}
        native=response.get('solve_ns') if cell['lane']=='practical' else response.get('native_ns') if cell['lane']=='copt_scale_off' else response.get('elapsed_ns')
        timely=(process.get('returncode')==0 and not process.get('timed_out',True) and
            process.get('elapsed_ns',float('inf'))<=model['outer_seconds']*NS and native is not None and native<=model['native_seconds']*NS)
        rows.append(dict(cell=cell['id'],lane=cell['lane'],model=model['id'],family=cell['family'],repetition=cell['repetition'],
            status=response.get('status','missing_response'),reason=response.get('reason'),attempted=True,
            accepted=checked['accepted'],timely=timely,exact=checked.get('exact'),native_ns=native,
            process_ns=process.get('elapsed_ns'),input_encoding_ns=model['encoding_ns'],audit_ns=checked['elapsed_ns'],
            complete_ns=model['encoding_ns']+process.get('elapsed_ns',0)+checked['elapsed_ns'],
            gpu_confirmed=response.get('gpu_confirmed',response.get('gpu_work',cell['lane']=='retained_image_v11')),
            queries=response.get('queries'),phases=response.get('phase_ns'),audit=binding(directory/'audit.json'),
            response=binding(directory/'response.json') if response else None))
    put(out/'audit.json',dict(status='all_untouched_cells_accounted_and_available_endpoints_audited',rows=rows))
    print(json.dumps(dict(status='passed',rows=len(rows),accepted=sum(r['accepted'] for r in rows))),flush=True)


def execute(path):
    f=validated(path);out=path.parent
    # No completed driver is repeated. Chunks are bounded and each next block
    # checks the source-bound remaining set before its reservation is created.
    for gpu,initial in [(False,3000),(True,900)]:
        index=0
        while pending(f,out,gpu):
            identity=out.name+('-gpu-' if gpu else '-cpu-')+str(index)
            settled=BASE/'resources'/(identity+'.settlement.json')
            if settled.exists():
                receipt=read(settled)
                if not receipt['cleanup_empty'] or receipt['overrun']:raise RuntimeError('unresolved recovery reservation')
                index+=1;continue
            cpu=accounting(BASE);device=accounting(BASE,True)
            remaining_cpu=(CPU['confirmation']*NS-cpu['confirmation'])//(4*NS)
            remaining_gpu=(GPU['confirmation']*NS-device['confirmation'])//NS if gpu else remaining_cpu
            seconds=min(initial if index==0 else 300,int(remaining_cpu),int(remaining_gpu))
            if seconds<(120 if gpu else 120):raise RuntimeError('remaining phase cannot admit untouched tail')
            # GPU idle time is outside the worker allowance; leave 15 seconds
            # beyond the worker's own 35-second cleanup/publication margin.
            allowance=seconds-(45 if gpu else 15)
            command=[str(PYTHON),'-B',__file__,'gpu' if gpu else 'cpu',str(path),'--allowance',str(allowance),'--chunk',identity]
            receipt=run(identity,'confirmation',seconds,command,16,gpu=gpu)
            print(json.dumps(dict(identity=identity,settlement=receipt)),flush=True)
            if receipt['status']!='passed':raise RuntimeError('recovery chunk failed; inspect before any further launch')
            if not read(out/(identity+'-completed.json'))['attempted']:raise RuntimeError('no cell fits remaining guarded chunk')
            index+=1
    identity=out.name+'-audit'
    if not (BASE/'resources'/(identity+'.reservation.json')).exists():
        receipt=run(identity,'confirmation',240,[str(PYTHON),'-B',__file__,'audit',str(path)],16)
        if receipt['status']!='passed':raise RuntimeError('recovery audit failed')
    if not (out/'audit.json').exists():raise RuntimeError('recovery audit incomplete')
    put(out/'completed.json',dict(status='all_original_unattempted_cells_completed_or_capacity_refused',freeze=binding(path)))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['freeze','execute','cpu','gpu','audit']);p.add_argument('target')
    p.add_argument('--original',type=Path);p.add_argument('--allowance',type=float);p.add_argument('--chunk');a=p.parse_args()
    if a.action=='freeze':freeze(a.target,a.original.resolve())
    elif a.action=='execute':execute(Path(a.target).resolve())
    elif a.action=='audit':audit_all(Path(a.target).resolve())
    else:worker(Path(a.target).resolve(),a.action=='gpu',a.allowance,a.chunk)
