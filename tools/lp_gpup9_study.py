"""Immutable complete-cost trials with original-model certificate ownership."""
import argparse
import os
import subprocess
import sys
import time
from lp_gpup9_common import (BASE, ROOT, BINARY, IMAGE, TIER, SETTINGS, configs,
                            load, put, ref, checked, require)
from lp_gpup9_protocol import STAGES, verify_design, schedule
from lp_mixed2_confirm2_confirmation import environment_snapshot
import lp_mixed2_reuse_transport as transport


def execute(out, cell, cfg, models):
    out.mkdir(parents=True,exist_ok=True)
    prefix=out/cell['id']
    put(str(prefix)+'.intent.json',dict(cell=cell,configuration=cfg))
    paths=models['groups'][cell['group']]['models']
    for item in paths:checked(item)
    transport.BINARY=BINARY
    image_digest=ref(IMAGE)['sha256'];binary_digest=ref(BINARY)['sha256']
    started=time.monotonic_ns();service=None;records=[]
    try:
        service=transport.Service(IMAGE,ROOT/paths[0]['path'],str(prefix)+'.log',equilibrate=cfg['equilibrate'])
        require(service.ready['model_sha256']==paths[0]['sha256'],'initial original model')
        if cell['endpoint']=='prepared':
            for item in paths[1:]:
                response=service.call('cache_model',model_path=str(ROOT/item['path']))
                require(response['cached_model_sha256']==item['sha256'],'cached original model')
        service.call('prepare',lane=cfg['lane'])
        setup=time.monotonic_ns()-started
        for index in range(cell['count']):
            begin=time.monotonic_ns();scenario=index%4 if cell['endpoint']=='prepared' else 0
            item=paths[scenario]
            response=service.call('select_model',model_hash=item['sha256'])
            require(response['selected_model_sha256']==item['sha256'],'scenario ownership')
            dest=out/(cell['id']+f'-r{index:02d}.json')
            r,solve_ns=service.solve_to_file(dest,lane=cfg['lane'],tier=TIER,
                                           **(SETTINGS|dict(window_max=cfg['window_max'])))
            complete=time.monotonic_ns()-begin
            require(r['model_sha256']==item['sha256'] and r['certificate']['model_sha256']==item['sha256'],'original certificate binding')
            require(r['image_sha256']==image_digest and r['checker_binary_sha256']==binary_digest,'executable binding')
            require(r['lane']==cfg['lane'] and r['tier']==TIER and r['window_max']==cfg['window_max'] and r['fixed_audit'],'response configuration')
            require(r['physical']==sum(r['attempted'].values()),'physical work accounting')
            require(r['certified']==r['certificate']['accepted'],'certificate classification')
            records.append(dict(index=index,scenario=scenario,result=ref(dest),model=item,
                certified=r['certified'],complete_ns=complete,solve_ns=solve_ns,
                physical=r['physical'],logical=r['logical'],attempted=r['attempted'],
                gpu_us=r['gpu_us'],costs_ns=r['costs_ns'],final_lane=r['final_lane'],
                recoveries=[e for e in r['events'] if e['kind']=='recovery']))
        before=time.monotonic_ns();service.close();teardown=time.monotonic_ns()-before
        total=time.monotonic_ns()-started
        row=dict(schema_version=1,kind='gpup9-session',**cell,setup_ns=setup,teardown_ns=teardown,complete_session_ns=total,records=records)
        from lp_gpup9_schema import validate_session
        validate_session(row)
        put(str(prefix)+'.session.json',row)
        print(dict(cell=cell['id'],seconds=round(total/1e9,3),certified=sum(r['certified'] for r in records)),flush=True)
        return row
    except BaseException as error:
        put(str(prefix)+'.failure.json',dict(cell=cell,error=type(error).__name__,message=str(error),
            elapsed_ns=time.monotonic_ns()-started,retained_responses=[r['result'] for r in records]))
        raise
    finally:
        if service is not None:service.close()


def pilot():
    verify_design(load(BASE/'design-v2.json'))
    models=load(BASE/'models-v2/admission/manifest.json');rows=[]
    for group,data in models['groups'].items():
        for key in ['native-w32-s1','fp4x2-w16-s1']:
            cell=dict(id=group+'-'+key,block=0,group=group,family=data['descriptor']['family'],
                endpoint='prepared',config=key,position=0,count=32)
            rows.append(execute(BASE/'pilot-v3',cell,configs()[key],models))
    require(all(x['certified'] for row in rows for x in row['records']),'pilot certificate refusal')
    put(BASE/'pilot-v3/result.json',dict(status='passed',sessions=rows,scientific=False))


def block(stage,index):
    verify_design(load(BASE/'design-v2.json'))
    f=load(BASE/f'{stage}-freeze.json')
    require(f['stage']==stage and f['design']==ref(BASE/'design-v2.json'),'frozen stage binding')
    require(f['implementation']==ref(BASE/'implementation-v5.json'),'frozen implementation changed')
    require(f['cells']==schedule(stage,f['configurations']),'frozen schedule changed')
    for item in f['admissions']:checked(item)
    model_path=BASE/'models-v2'/stage/'manifest.json'
    if f['models'] is not None:require(ref(model_path)==f['models'],'model manifest changed')
    else:
        binding=load(BASE/'holdout-model-binding.json')
        require(binding['freeze']==ref(BASE/'holdout-freeze.json') and binding['manifest']==ref(model_path),'holdout materialization binding changed')
    models=load(model_path)
    require(models['design']==f['design'] and models['partition']==stage,'partition binding')
    out=BASE/stage/f'b{index:02d}';out.mkdir(parents=True,exist_ok=False)
    put(out/'environment-before.json',environment_snapshot());rows=[]
    for cell in f['cells']:
        if cell['block']==index:rows.append(execute(out,cell,f['configurations'][cell['config']],models))
    put(out/'result.json',dict(status='passed',sessions=rows,environment=environment_snapshot()))


def run(stage):
    f=load(BASE/f'{stage}-freeze.json')
    require(not list((BASE/'resources').glob(stage+'-b*.reservation.json')),'scientific stage already attempted')
    for index in range(f['blocks']):
        identity=f'{stage}-b{index:02d}'
        command=[sys.executable,'tools/lp_gpup9_budget.py','--id',identity,'--phase',stage,
            '--seconds',str(f['seconds']),'--gpu','--',sys.executable,'tools/lp_mixed2_reuse_place.py',
            sys.executable,__file__,'block','--stage',stage,'--index',str(index)]
        code=subprocess.run(command,cwd=ROOT).returncode
        settlement=load(BASE/'resources'/(identity+'.settlement.json'))
        print(dict(stage=stage,block=index,status=settlement['status']),flush=True)
        require(code==0 and settlement['status']=='passed' and not settlement['overrun'],
                'study stops on resource/process refusal; no scientific retry')


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('command',choices=['pilot','run','block']);p.add_argument('--stage',choices=STAGES);p.add_argument('--index',type=int);a=p.parse_args()
    if a.command=='pilot':pilot()
    elif a.command=='run':run(a.stage)
    else:block(a.stage,a.index)
