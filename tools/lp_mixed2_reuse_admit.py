"""Reuse/state-switch contracts and independent serial original-model authority."""
import argparse
import json
import os
from pathlib import Path
import subprocess
from lp_mixed2_reuse_common import BASE, OLD, ROOT, BINARY, IMAGE, load, put, ref, require
from lp_mixed2_reuse_transport import Service
from lp_mixed2_reuse_study import execute_session
from lp_delivery2_study import bits


def numerical(r):
    result = {k:r[k] for k in ('status','certified','lane','final_lane','tier','window_max',
        'fixed_audit','physical','logical','attempted','model_sha256','row_scale','shift',
        'endpoint','certificate','audits','events','checkpoint','terminal')}
    def strip(x):
        if isinstance(x,dict):
            return {k:strip(v) for k,v in x.items() if k not in ('checker_binary_sha256','elapsed_ns','assessment_ns','gpu_us')}
        if isinstance(x,list): return [strip(v) for v in x]
        return x
    return bits(strip(result))


def serial_check(out, item, result, index):
    old = OLD/'build-v10/executor'
    checked = 0
    for j, (endpoint, certificate) in enumerate([(result['endpoint'], result['certificate'])]+
            [(a['endpoint'], a['certificate']) for a in result['audits']]):
        ep=out/f'{index}-a{j}.endpoint.json'; dest=out/f'{index}-a{j}.certificate.json'
        put(ep,endpoint)
        subprocess.run([str(old),'check-serial',str(ROOT/item['path']),str(ep),result['tier'],str(dest)],
                       capture_output=True,check=True,timeout=120)
        clean=lambda x:{k:v for k,v in x.items() if k!='checker_binary_sha256'}
        require(bits(clean(load(dest)))==bits(clean(certificate)), 'original serial checker differs')
        checked += 1
    return checked


def scenarios(out, sanitizer=None, large=False, family=None):
    out.mkdir(exist_ok=False)
    if sanitizer: os.environ['AI_OPTIMIZER_SANITIZER']=sanitizer
    models=load(BASE/'models/manifest.json');rows=[];checked=0
    families=[family] if family else (sorted(models['groups']) if large else ['dense-coupled-33'])
    put(out/'manifest.json',dict(binary=ref(BINARY),image=ref(IMAGE),models=ref(BASE/'models/manifest.json'),
                                sanitizer=sanitizer,families=families))
    for family in families:
        for tier in ['certified-1e-7','certified-1e-9']:
            for lane in ['native','fp4x2']:
                cell=dict(id=f'{family}-{tier}-{lane}',family=family,tier=tier,lane=lane)
                row=execute_session(out,cell,models,count=8)
                for index in range(4):
                    item=models['groups'][family][index]
                    s=Service(IMAGE,ROOT/item['path'],out/(cell['id']+f'-fresh{index}.log'))
                    try:
                        fresh,_=s.solve_to_file(out/(cell['id']+f'-fresh{index}.json'),lane=lane,tier=tier,
                            **(models['settings']|dict(fixed_audit=True,window_max=32 if lane=='native' else 16)))
                    finally:s.close()
                    require(numerical(fresh)==numerical(load(ROOT/row['records'][index]['result']['path'])),
                            'cached scenario differs from fresh session')
                    require(numerical(fresh)==numerical(load(ROOT/row['records'][index+4]['result']['path'])),
                            'return to scenario differs')
                    # Serial reassessment is CPU-only and separately charged later.
                rows.append(row)
    if sanitizer:
        logs=list(out.glob('*.sanitizer'));require(logs,'missing scenario sanitizer logs')
        for path in logs:
            text=path.read_text()
            require('ERROR SUMMARY: 0 errors' in text or
                    (sanitizer=='racecheck' and 'RACECHECK SUMMARY: 0 hazards' in text),
                    'scenario sanitizer failure: '+str(path))
    put(out/'result.json',dict(status='passed',sessions=rows,fresh_comparisons=len(rows)*8))


def invalid(out):
    out.mkdir(exist_ok=False);models=load(BASE/'models/manifest.json')
    paths=models['groups']['dense-coupled-33'];rows=[]
    cases=['unknown','duplicate','generation','active','capacity','operator','cancelled']
    for case in cases:
        s=Service(IMAGE,ROOT/paths[0]['path'],out/(case+'.log'))
        fields=dict(op='select_model',solve_id=0,generation=0,model_hash='0'*64)
        if case=='duplicate':fields=dict(op='cache_model',model_path=str(ROOT/paths[0]['path']))
        if case=='generation':fields.update(model_hash=paths[0]['sha256'],generation=1)
        if case=='active':s.call('debug_reset',lane='fp4x2',max_updates=1);fields.update(model_hash=paths[0]['sha256'])
        if case=='capacity':
            for p in paths[1:]:s.call('cache_model',model_path=str(ROOT/p['path']))
            fields=dict(op='cache_model',model_path=str(ROOT/paths[0]['path']))
        if case=='operator':fields=dict(op='cache_model',model_path=str(ROOT/models['groups']['dense-generic-1024'][0]['path']))
        if case=='cancelled':
            r=s.call('solve',lane='fp4x2',tier='certified-1e-9',cancel_after=0)
            require(not r['certified'] and r['status']=='cancelled','cancelled solve accepted')
            fields.update(solve_id=1,model_hash=paths[0]['sha256'])
        s.write(fields);s.close(expected=1);rows.append(dict(case=case,exit=1))
    put(out/'result.json',dict(status='passed',rows=rows))


def recovery(out):
    out.mkdir(exist_ok=False);models=load(BASE/'models/manifest.json')
    paths=models['groups']['dense-coupled-33'];rows=[]
    s=Service(IMAGE,ROOT/paths[0]['path'],out/'cached.log')
    try:
        for p in paths[1:]:s.call('cache_model',model_path=str(ROOT/p['path']))
        for i,(scenario,fault) in enumerate([(1,'local_budget'),(2,'conversion_failure'),(3,None),(0,None)]):
            item=paths[scenario];s.call('select_model',model_hash=item['sha256'])
            fields=dict(lane='fp4x2',tier='certified-1e-9',fixed_audit=True,window_max=16)
            if fault:fields['fault']=fault
            cached,_=s.solve_to_file(out/f'{i}-cached.json',**fields)
            fresh=Service(IMAGE,ROOT/item['path'],out/f'{i}-fresh.log')
            try:r,_=fresh.solve_to_file(out/f'{i}-fresh.json',**fields)
            finally:fresh.close()
            require(cached['certified'] and numerical(cached)==numerical(r),'scenario recovery differs from fresh execution')
            if fault:require(any(e['kind']=='recovery' for e in cached['events']),'fault did not exercise recovery')
            rows.append(dict(scenario=scenario,fault=fault,result=ref(out/f'{i}-cached.json')))
    finally:s.close()
    put(out/'result.json',dict(status='passed',rows=rows))


def sanitizer_switches(out, sanitizer):
    """Exercise cache uploads/reset/restore at tails and largest shape.

    Full certified trajectories are admitted separately. Under racecheck those
    trajectories take seconds per solve, so this suite targets the new switching
    boundary with bounded device work and exact fresh-state comparisons.
    """
    out.mkdir(exist_ok=False);os.environ['AI_OPTIMIZER_SANITIZER']=sanitizer
    models=load(BASE/'models/manifest.json');rows=[]
    put(out/'manifest.json',dict(binary=ref(BINARY),image=ref(IMAGE),sanitizer=sanitizer,
        source=ref(__file__),purpose='bounded scenario switch/reset/restore versus fresh engines',
        families=['dense-coupled-33','dense-generic-2048'],lanes=['native','fp4x2','fp4x4'],
        final_certificate_claim=False))
    for family,scenarios in [('dense-coupled-33',range(4)),('dense-generic-2048',range(2))]:
        paths=models['groups'][family];s=Service(IMAGE,ROOT/paths[0]['path'],out/(family+'-cached.log'))
        try:
            for index in list(scenarios)[1:]:s.call('cache_model',model_path=str(ROOT/paths[index]['path']))
            for lane in ['native','fp4x2','fp4x4']:
                for scenario in scenarios:
                    item=paths[scenario];s.call('select_model',model_hash=item['sha256'])
                    s.call('debug_reset',lane=lane,max_updates=3)
                    before=s.call('debug_export');s.call('debug_step',count=1,limit=1e20)
                    observed=s.call('debug_export');s.call('debug_restore');restored=s.call('debug_export')
                    require(bits(before['raw'])==bits(restored['raw']) and restored['logical']==0,'scenario exact restore')
                    s.call('debug_finish')
                    name=f'{family}-{lane}-s{scenario}'
                    fresh=Service(IMAGE,ROOT/item['path'],out/(name+'-fresh.log'))
                    try:
                        fresh.call('debug_reset',lane=lane,max_updates=3)
                        fresh.call('debug_step',count=1,limit=1e20);expected=fresh.call('debug_export')
                        fresh.call('debug_finish')
                    finally:fresh.close()
                    require(bits(observed)==bits(expected),'sanitized switch differs from fresh state')
                    row=dict(family=family,lane=lane,scenario=scenario,observed=observed,restored=restored)
                    put(out/(name+'.json'),row);rows.append(dict(family=family,lane=lane,scenario=scenario))
        finally:s.close()
    logs=list(out.glob('*.sanitizer'));require(logs,'missing switch sanitizer logs')
    for path in logs:
        text=path.read_text()
        require('ERROR SUMMARY: 0 errors' in text or
                (sanitizer=='racecheck' and 'RACECHECK SUMMARY: 0 hazards' in text),'switch sanitizer errors')
    put(out/'result.json',dict(status='passed',comparisons=len(rows),rows=rows,sanitizer=sanitizer,logs=len(logs)))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['scenarios','invalid','recovery','switches']);p.add_argument('out',type=Path)
    p.add_argument('--sanitizer');p.add_argument('--large',action='store_true');p.add_argument('--family');a=p.parse_args()
    if a.action=='scenarios':scenarios(a.out,a.sanitizer,a.large,a.family)
    elif a.action=='invalid':invalid(a.out)
    elif a.action=='switches':sanitizer_switches(a.out,a.sanitizer)
    else:recovery(a.out)
