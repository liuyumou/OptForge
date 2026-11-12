"""Device lifecycle and failure admission; every case retains its evidence."""
import argparse
from pathlib import Path
from lp_fp4_accel_common import ROOT,put,ref,require
from lp_fp4_accel_model import model
from lp_fp4_accel_run import Service,BINARY,compact

LANES=('native','fp4x2','fp4x4','scalarfp4x2','scalarfp4x4','gridnative','gridfp4x2','gridfp4x4')


def run(image,out):
    out=Path(out);out.mkdir(parents=True,exist_ok=False);rows=[];serial=0
    put(out/'manifest.json',dict(image=ref(image),binary=ref(BINARY),source=ref(Path(__file__)),lanes=LANES))
    def service(family='dense-generic-128'):
        nonlocal serial
        serial+=1;path=out/(family+'.json')
        if not path.exists():compact(path,model(family)[0])
        return Service(image,path,out/f'{serial:03d}.stderr')
    def record(case,**v):rows.append(dict(case=case,**v));put(out/f'case-{len(rows):03d}.json',rows[-1])
    for family in ('irregular-tail-33','dense-generic-512'):
        s=service(family)
        try:
            for lane in LANES:
                s.call('debug_reset',lane=lane,max_updates=1000)
                initial=s.call('debug_export');r=s.call('debug_step',count=8,limit=1.)
                require(r['physical']==8 and r['logical']==8,'physical accounting')
                s.call('debug_save');accepted=s.call('debug_saved');live=s.call('debug_export')
                require(all(accepted[k]==live[k] for k in ('raw','codes','exponents','pairs','logical')),'saved raw view is stale')
                s.call('debug_step',count=32,limit=1.)
                s.call('debug_restore');restored=s.call('debug_export')
                require(all(restored[k]==accepted[k] for k in ('raw','codes','exponents','pairs','logical')),'incomplete restore')
                require(restored['generation']==1,'generation not advanced');s.call('debug_finish')
                s.call('debug_reset',lane=lane);fresh=s.call('debug_export')
                require(all(fresh[k]==initial[k] for k in ('raw','codes','exponents','pairs','logical')),'fresh solve contaminated')
                s.call('debug_finish');record('checkpoint-fresh',family=family,lane=lane,restore_exact=True)
        finally:s.close()
    for lane in ('native','fp4x4','gridnative','gridfp4x4'):
        s=service()
        try:
            a=s.call('solve',lane=lane,tier='certified-1e-9');b=s.call('solve',lane=lane,tier='certified-1e-9')
            require(a['certified'] and b['certified'],'fresh solve failed')
            require(a['endpoint']==b['endpoint'] and a['physical']==b['physical'],'prepared numerical state leaked')
            require(b['physical_total']==a['physical']+b['physical'],'ledger reset between solves')
            record('repeat-certified',lane=lane,first=a,second=b)
        finally:s.close()
    for lane in ('fp4x2','gridfp4x2'):
        for fault in ('local_budget','conversion_failure'):
            s=service()
            try:
                r=s.call('solve',lane=lane,tier='certified-1e-9',fault=fault)
                recoveries=[e for e in r['events'] if e['kind']=='recovery']
                require(r['certified'] and recoveries,'recovery did not certify')
                require(r['physical']>r['logical'],'lost work not charged')
                if fault=='conversion_failure':require(any(e['kind']=='conversion_failure' for e in r['events']),'conversion fault not exercised')
                record('recovery',lane=lane,fault=fault,result=r)
            finally:s.close()
    for lane in ('fp4x4','gridfp4x4'):
        for cancel in (0,7,200):
            s=service()
            r=s.call('solve',lane=lane,tier='certified-1e-9',cancel_after=cancel)
            require(r['status']=='cancelled' and not r['certified'] and r['physical']==cancel,'cancellation lost to certificate')
            require(r['terminal']['raw']==r['checkpoint']['device']['raw'],'cancel did not restore')
            try:s.call('solve',lane=lane,tier='certified-1e-9');raise AssertionError('cancelled service restarted')
            except RuntimeError:pass
            s.close(expected=1);record('terminal-cancel',lane=lane,cancel=cancel,result=r)
    for case,fields in [('deadline',dict(wall_ms=0)),('physical-limit',dict(max_updates=7)),('external-cancel',dict(cancel_file=str(out/'cancel')) )]:
        if case=='external-cancel':(out/'cancel').touch()
        s=service()
        try:
            r=s.call('solve',lane='gridfp4x4',tier='certified-1e-9',**fields)
            require(not r['certified'],'premature terminal certificate')
            if case=='deadline':require(r['status']=='deadline' and r['physical']==0,'deadline')
            if case=='physical-limit':require(r['physical']==7,'physical limit')
            if case=='external-cancel':require(r['status']=='cancelled' and r['physical']==0,'external cancellation')
            record(case,result=r)
        finally:s.close()
    s=service();s.generation=1
    try:s.call('solve',lane='auto',tier='certified-1e-9');raise AssertionError('stale solve generation accepted')
    except RuntimeError:pass
    s.close(expected=1);record('stale-solve-generation',rejected=True)
    for case in ('stale-generation','stale-solve','active-reset','physical-cap','audit-cap','invalid-count','faulted-adoption'):
        s=service();s.call('debug_reset',lane='gridfp4x4',max_updates=1000)
        if case=='stale-generation':s.call('debug_restore');s.generation=0
        if case=='stale-solve':s.solve_id+=1
        if case=='audit-cap':
            for count in (32,32,32,32,32,32,8):s.call('debug_step',count=count,limit=1.)
        if case=='physical-cap':
            s.call('debug_finish');s.call('debug_reset',lane='gridfp4x4',max_updates=7)
        if case=='faulted-adoption':
            r=s.call('debug_step',count=32,limit=1e-30)
            require(any(r['step']['flags']),'local fault missing')
        try:
            if case=='active-reset':s.call('debug_reset',lane='gridfp4x4')
            elif case=='faulted-adoption':s.call('debug_save')
            else:s.call('debug_step',count=33 if case=='invalid-count' else 8 if case=='physical-cap' else 1,limit=1.)
            raise AssertionError('unsafe operation accepted: '+case)
        except RuntimeError:pass
        s.close(expected=1);record(case,rejected=True)
    s=service('infinite-bound-refusal')
    try:
        r=s.call('solve',lane='fp4x4',tier='certified-1e-7');require(r['status']=='unbounded_direction' and not r['certified'] and r['physical']==0,'refusal');record('unbounded-refusal',result=r)
    finally:s.close()
    put(out/'result.json',dict(status='passed',cases=len(rows),rows=rows));print(dict(status='passed',cases=len(rows)),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--image',required=True);p.add_argument('--output',required=True);a=p.parse_args();run(Path(a.image),Path(a.output))
