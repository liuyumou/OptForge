"""Frozen 28-model, three-lane, three-rotation original-LP confirmation.

Seven family reservations amortize idle observation while retaining separate
fresh processes and deadlines for all 252 cells. Audits have CPU reservations.
An attempted scientific identity is never restarted after an interruption.
"""
import argparse
import json
from pathlib import Path
import sys
import time
from lp_sp_pricing_budget import BASE,ROOT,put,binding,run,accounting,CPU,GPU,NS
from lp_sp_pricing_baselines import PYTHON,portable,launch,audit,images
from lp_sp_pricing_study import generated,capacity,FAMILIES


def read(path):return json.loads(Path(path).read_text())


def verify(item):
    if binding(item['path'])!=item:raise RuntimeError('frozen binding changed: '+item['path'])


def freeze(identity):
    out=BASE/identity;out.mkdir(exist_ok=False)
    protocol=read(BASE/'protocol-v1.json')
    development=[]
    for name,gpu in [('cpu-ladder-v4',False),('gpu-ladder-v2',True)]:
        path=BASE/name/'result.json';data=read(path)
        rows=data['rows']
        if len(rows)!=21:raise RuntimeError('complete separate-seed ladder required')
        development.append(dict(identity=name,gpu=gpu,source=binding(path),
            accepted=sum(r['accepted'] and r['elapsed_ns']<=10*NS for r in rows),
            capped_complete_ns=sum(min(10*NS,r['elapsed_ns']) for r in rows)))
    selected=min(development,key=lambda r:(-r['accepted'],r['capped_complete_ns'],r['gpu']))
    config=dict(gpu=selected['gpu'],precision='fp32x2',batch=32,sparse=True)
    admissions=[BASE/'baseline-seal-v1/result.json',BASE/'flow-market-sanitizers-v1/binding.json',
        BASE/'auxiliary-sanitizers-v2/binding.json',BASE/'gpu-admission-v5.json']
    for path in admissions:
        if read(path)['status']!='passed':raise RuntimeError('admission did not pass: '+str(path))
    from lp_sp_pricing_gpu_admission import validate
    validate(ROOT/'research/lp-sp-pricing/target/release/liblp_sp_pricing.so')
    sources=list(sorted((ROOT/'research/lp-sp-pricing/python').rglob('*.py')))
    sources += list(sorted((ROOT/'research/lp-sp-pricing/native').glob('*.*')))
    sources += [ROOT/'research/lp-sp-pricing/src/lib.rs',ROOT/'research/lp-sp-pricing/build.rs',
        ROOT/'research/lp-sp-pricing/Cargo.toml',ROOT/'research/lp-sp-pricing/target/release/liblp_sp_pricing.so',
        ROOT/'research/lp-sp-pricing/target/cpu/libsp_market.so',ROOT/'research/lp-sp-pricing/target/cpu/libsp_auxiliary.so',
        Path('/usr/lib/x86_64-linux-gnu/libgmp.so.10.4.1')]
    sources += [ROOT/'tools'/name for name in ['lp_sp_pricing_campaign.py','lp_sp_pricing_baselines.py',
        'lp_sp_pricing_run.py','lp_sp_pricing_verify.py','lp_sp_pricing_study.py','lp_sp_pricing_budget.py','lp_sp_pricing_guard.py']]
    models=[];cells=[]
    for index,original in enumerate(protocol['roster']):
        directory=out/'models'/original['id'];directory.mkdir(parents=True)
        begin=time.monotonic_ns();model,construction=generated(original)
        rational=directory/'rational.json';native=directory/'portable.json'
        put(rational,model);put(directory/'construction.json',construction);portable(model,native)
        encoding_ns=time.monotonic_ns()-begin
        nonzeros=read(native)['nonzeros'];gate=capacity(original['rows'],original['columns'],nonzeros)
        model_item=dict(**original,rational=binding(rational),portable=binding(native),encoding_ns=encoding_ns,capacity=gate)
        models.append(model_item)
        for rep in range(3):
            lanes=original['lanes'];shift=(index+rep)%3
            for lane in lanes[shift:]+lanes[:shift]:
                cells.append(dict(id=f"{original['id']}-r{rep}-{lane}",model_index=index,lane=lane,repetition=rep,
                    family=original['family'],status='unsupported_capacity' if lane=='practical' and gate['status']=='unsupported' else 'pending'))
    # Every solve-process maximum plus one idle/finalization allowance per
    # family fits the unchanged phase totals, even if every cell times out.
    gpu_reserve=7*1680;cpu_reserve=4*(gpu_reserve+7*120)
    cpu_used=gpu_used=0
    for path in (BASE/'resources').glob('*.reservation.json'):
        if read(path)['phase']!='confirmation':continue
        receipt=read(path.with_name(path.name.replace('.reservation.','.settlement.')))
        if not receipt['cleanup_empty'] or receipt['overrun']:raise RuntimeError('unresolved confirmation reservation')
        cpu_used+=receipt['cpu_ns'];gpu_used+=receipt['gpu_ns']
    if cpu_used+cpu_reserve*NS>CPU['confirmation']*NS:raise RuntimeError('whole CPU roster does not fit')
    if gpu_used+gpu_reserve*NS>GPU['confirmation']*NS:raise RuntimeError('whole GPU roster does not fit')
    put(out/'freeze.json',dict(schema=1,status='frozen',protocol=binding(BASE/'protocol-v1.json'),models=models,cells=cells,
        configuration=config,development_selection=development,selection_rule='maximize timely exact certificates, then minimize capped complete development cost',
        sources=[binding(p) for p in sources],admissions=[binding(p) for p in admissions],images=images(),
        reservation=dict(solve_seconds_per_family=1680,audit_seconds_per_family=120,gpu_seconds=gpu_reserve,cpu_seconds=cpu_reserve),
        timing='cold solve process plus common model encoding plus all mandatory independent endpoint audits; idle and resource finalization excluded',
        certificate='unchanged original-model 1e-9 checker; exact rational tier reported separately',
        comparisons='ratios only for jointly timely strictly accepted cells; all refusals and failures remain'))
    print(json.dumps(dict(status='frozen',models=len(models),cells=len(cells),configuration=config)),flush=True)


def validate(f):
    verify(f['protocol'])
    for item in f['sources']+f['admissions']:verify(item)
    if images()!=f['images']:raise RuntimeError('retained baseline image changed')


def solve_family(path,family):
    f=read(path);validate(f);out=path.parent
    for cell in f['cells']:
        if cell['family']!=family:continue
        model=f['models'][cell['model_index']];directory=out/'cells'/cell['id']
        verify(model['rational']);verify(model['portable'])
        if directory.exists():raise RuntimeError('attempt identity already exists: '+cell['id'])
        if cell['status']=='unsupported_capacity':
            directory.mkdir(parents=True);put(directory/'unsupported.json',dict(reasons=model['capacity']['reasons'],attempted=False))
            continue
        process=launch(cell['lane'],Path(model['portable']['path']),Path(model['rational']['path']),directory,
            model['native_seconds'],model['outer_seconds'],f['configuration'])
        print(json.dumps(dict(cell=cell['id'],process=process)),flush=True)
    put(out/(family+'-solves-complete.json'),dict(status='all_admitted_cells_attempted',family=family))


def audit_family(path,family):
    f=read(path);validate(f);out=path.parent;rows=[]
    for cell in f['cells']:
        if cell['family']!=family:continue
        model=f['models'][cell['model_index']];directory=out/'cells'/cell['id']
        if cell['status']=='unsupported_capacity':
            rows.append(dict(cell=cell['id'],lane=cell['lane'],status='unsupported_capacity',accepted=False,timely=False,attempted=False));continue
        if not directory.exists():
            rows.append(dict(cell=cell['id'],lane=cell['lane'],status='unattempted_after_interruption',accepted=False,timely=False,attempted=False));continue
        process=read(directory/'process.json') if (directory/'process.json').exists() else {}
        checked=audit(cell['lane'],Path(model['portable']['path']),Path(model['rational']['path']),directory)
        response=read(directory/'response.json') if (directory/'response.json').exists() else {}
        native=response.get('solve_ns') if cell['lane']=='practical' else response.get('native_ns') if cell['lane']=='copt_scale_off' else response.get('elapsed_ns')
        timely=(process.get('returncode')==0 and not process.get('timed_out',True) and
            process.get('elapsed_ns',float('inf'))<=model['outer_seconds']*NS and
            native is not None and native<=model['native_seconds']*NS)
        row=dict(cell=cell['id'],lane=cell['lane'],model=model['id'],family=family,repetition=cell['repetition'],
            status=response.get('status','missing_response'),reason=response.get('reason'),attempted=True,
            accepted=checked['accepted'],timely=timely,exact=checked.get('exact'),
            native_ns=native,process_ns=process.get('elapsed_ns'),input_encoding_ns=model['encoding_ns'],audit_ns=checked['elapsed_ns'],
            complete_ns=model['encoding_ns']+process.get('elapsed_ns',0)+checked['elapsed_ns'],
            gpu_confirmed=response.get('gpu_confirmed',response.get('gpu_work',cell['lane']=='retained_image_v11')),
            queries=response.get('queries'),phases=response.get('phase_ns'),
            audit=binding(directory/'audit.json'),response=binding(directory/'response.json') if response else None)
        rows.append(row);print(json.dumps({k:row[k] for k in ['cell','status','accepted','timely','complete_ns']}),flush=True)
    put(out/(family+'-audit.json'),dict(status='all_available_endpoints_checked',rows=rows))


def execute(path):
    f=read(path);validate(f)
    for family in FAMILIES:
        for action,seconds,gpu in [('solve',1680,True),('audit',120,False)]:
            identity=path.parent.name+'-'+family+'-'+action
            reserved=BASE/'resources'/(identity+'.reservation.json')
            settled=BASE/'resources'/(identity+'.settlement.json')
            if reserved.exists():
                if not settled.exists():raise RuntimeError('active reservation; do not launch another')
                receipt=read(settled)
            else:
                receipt=run(identity,'confirmation',seconds,[str(PYTHON),'-B',__file__,action,str(path),family],16,gpu=gpu)
            print(json.dumps(dict(identity=identity,settlement=receipt)),flush=True)
            if not receipt['cleanup_empty'] or receipt['overrun']:raise RuntimeError('unresolved resource failure')
            if action=='audit' and receipt['status']!='passed':raise RuntimeError('audit incomplete; preserve partial results')
    put(path.parent/'completed.json',dict(status='full_frozen_roster_accounted_and_available_endpoints_audited',freeze=binding(path)))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['freeze','execute','solve','audit']);p.add_argument('target')
    p.add_argument('family',nargs='?');a=p.parse_args()
    if a.action=='freeze':freeze(a.target)
    elif a.action=='execute':execute(Path(a.target))
    elif a.action=='solve':solve_family(Path(a.target),a.family)
    else:audit_family(Path(a.target),a.family)
