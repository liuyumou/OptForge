"""Independent component/window oracle and checkpoints for the centered candidate."""
import argparse
from pathlib import Path
import numpy as np
from lp_fp4_accel_common import ROOT,put,ref,require
from lp_fp4_accel_model import model,reference,reference_centered
from lp_fp4_accel_run import Service,BINARY,compact


def qualify(image,out,grid=False):
    out=Path(out);out.mkdir(parents=True,exist_ok=False);rows=[]
    families=('coupled-equality','ranged-one-sided','fixed-active-bounds','ill-scaled-coupled',
              'irregular-tail-33','dense-rich-65','dense-generic-128','dense-generic-256','dense-generic-512')
    lanes=('gridnative','gridfp4x2','gridfp4x4') if grid else ('native','fp4x2','fp4x4')
    put(out/'manifest.json',dict(image=ref(image),binary=ref(BINARY),source=ref(Path(__file__)),
        oracle=ref(ROOT/'tools/lp_fp4_accel_model.py'),families=families,lanes=lanes,steps=[1,8,32],tolerance=5e-11))
    for family in families:
        doc,data=model(family);path=out/(family+'.json');compact(path,doc)
        s=Service(image,path,out/(family+'.stderr'))
        try:
            for lane in lanes:
                info=s.call('debug_reset',lane=lane,max_updates=600);initial=s.call('debug_export')
                raw=np.asarray(initial['raw']);p=len(raw)//5;n=len(data['c']);scale=np.asarray(info['row_scale']);scaled=data['a']*scale[:,None]
                for op in ('debug_forward','debug_transpose'):
                    got=np.asarray(s.call(op)['product'])[:n]
                    expected=scaled@raw[2*p:2*p+n] if op=='debug_forward' else scaled.T@raw[p:p+n]
                    error=float(np.max(abs(got-expected)));require(error<=5e-11,f'{family}/{lane}/{op} error {error}')
                    s.call('debug_restore');rows.append(dict(family=family,lane=lane,case=op,error=error))
                for steps in (1,8,32):
                    step=s.call('debug_step',count=steps,limit=1.)['step'];require(step['done']==steps and not any(step['flags']),f'{family}/{lane} flags {step}')
                    observed=s.call('debug_export')
                    expected=reference(data,raw,steps,info['shift'],scale) if lane.endswith('native') else reference_centered(data,raw,steps,info['shift'],scale,int(lane[-1]))
                    error=float(np.max(abs(np.asarray(observed['raw'])-expected)))
                    require(error<=5e-11,f'{family}/{lane}/{steps} component error {error}')
                    require(observed['raw'][3*p:]==initial['raw'][3*p:],'anchors changed')
                    s.call('debug_restore');restored=s.call('debug_export')
                    require(all(restored[k]==initial[k] for k in ('raw','codes','exponents','pairs','logical')),'complete rollback differs')
                    rows.append(dict(family=family,lane=lane,case='window',steps=steps,error=error,restore_exact=True))
                s.call('debug_finish')
        finally:s.close()
        print(dict(family=family,cases=len(rows)),flush=True)
    put(out/'result.json',dict(status='passed',rows=rows,global_enclosure=False))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--image',required=True);p.add_argument('--output',required=True);p.add_argument('--grid',action='store_true');a=p.parse_args();qualify(Path(a.image),Path(a.output),a.grid)
