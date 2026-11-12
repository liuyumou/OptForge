"""Independent device product/trajectory/complete-checkpoint checks for corrected FP4."""
import argparse
from pathlib import Path
import numpy as np
from lp_fp4_accel_common import ROOT,put,ref,require
from lp_fp4_accel_model import model,reference
from lp_fp4_accel_run import Service,BINARY,compact


def qualify(image,out):
    out=Path(out);out.mkdir(parents=True,exist_ok=False)
    families=('coupled-equality','ranged-one-sided','fixed-active-bounds','ill-scaled-coupled',
              'irregular-tail-33','dense-rich-65','dense-generic-128','dense-generic-256','dense-generic-512')
    put(out/'manifest.json',dict(image=ref(image),binary=ref(BINARY),families=families,
        lanes=['native','fp4x2','fp4x4'],steps=[1,8,32],native_tolerance=5e-12,corrected_tolerance=5e-11,
        source=ref(ROOT/'tools/lp_fp4_accel_qualify.py')))
    rows=[]
    for family in families:
        doc,data=model(family);path=out/(family+'.json');compact(path,doc)
        service=Service(image,path,out/(family+'.stderr'))
        try:
            for lane in ('native','fp4x2','fp4x4'):
                info=service.call('debug_reset',lane=lane,max_updates=600)
                initial=service.call('debug_export');raw=np.asarray(initial['raw']);p=len(raw)//5;n=len(data['c'])
                scaled=data['a']*np.asarray(info['row_scale'])[:,None]
                tol=5e-12 if lane=='native' else 5e-11
                for op in ('debug_forward','debug_transpose'):
                    got=np.asarray(service.call(op)['product'])[:n]
                    expected=(scaled@raw[2*p:2*p+n]) if op=='debug_forward' else scaled.T@raw[p:p+n]
                    error=float(np.max(abs(got-expected)))
                    require(error<=tol,f'{family}/{lane}/{op} error {error}')
                    service.call('debug_restore');rows.append(dict(family=family,lane=lane,case=op,error=error,tolerance=tol))
                for steps in (1,8,32):
                    step=service.call('debug_step',count=steps,limit=1.)['step']
                    require(step['done']==steps and not any(step['flags']),f'{family}/{lane} flags {step}')
                    endpoint=service.call('debug_export')
                    expected=reference(data,raw,steps,info['shift'],np.asarray(info['row_scale']))
                    error=float(np.max(abs(np.asarray(endpoint['raw'])-expected)))
                    require(error<=tol,f'{family}/{lane}/{steps} trajectory error {error}')
                    require(endpoint['raw'][3*p:]==initial['raw'][3*p:],'anchors changed')
                    service.call('debug_restore');restored=service.call('debug_export')
                    require(all(restored[k]==initial[k] for k in ('raw','codes','exponents','pairs','logical')),'full checkpoint changed')
                    rows.append(dict(family=family,lane=lane,case='steps',steps=steps,error=error,tolerance=tol,restore_exact=True))
                service.call('debug_finish')
        finally:service.close()
        print(dict(family=family,checks=len(rows)),flush=True)
    put(out/'result.json',dict(status='passed',rows=rows,certificate=False))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--image',required=True);p.add_argument('--output',required=True);a=p.parse_args()
    qualify(Path(a.image),Path(a.output))
