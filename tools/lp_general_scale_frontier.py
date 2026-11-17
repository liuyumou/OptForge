"""Capacity-selected 16 M extension, declared before any solver outcome."""
import argparse
import numpy as np
from lp_general_common import BASE,ROOT,put,load,ref,require
from lp_general_scale_io import memory_estimate,write,read
from lp_general_scale_models import FAMILIES,generate
from lp_general_scale_inventory import describe


def run(identity,retained=None):
    out=BASE/identity;out.mkdir(exist_ok=False);models=[];target=16000000
    if retained:
        require(load(BASE/'resources'/(retained+'.settlement.json'))['status']=='refused','retained preparation must remain failed')
        original=BASE/'sources'/retained/'tools/lp_general_scale_models.py'
        require(original.read_bytes()==(ROOT/'tools/lp_general_scale_models.py').read_bytes(),'retained generator differs')
    for family in FAMILIES:
        degree=64 if family=='coupled_blocks' else 16
        m=target//degree;n=m*4 if family=='wide' else m//4 if family=='tall' else m
        if family=='coupled_blocks':n=((n+63)//64)*64
        estimate=memory_estimate(m,n,target);host=estimate['host_allowance_bytes']+192*(m+n)*42;raw=64*(m+n)*42+(1<<20)
        reasons=[]
        if not estimate['admits_domain']:reasons.append('current dimension/nonzero domain')
        if host>=15<<30:reasons.append('complete solver/trajectory/audit host allowance')
        if raw>=4<<30:reasons.append('bounded response transport allowance')
        if estimate['device_allowance_bytes']>=12<<30:reasons.append('device allowance')
        if estimate['compact_bytes']>=512<<20:reasons.append('individual original-model file ceiling')
        for seed in [831001,831002,831003]:
            row=dict(family=family,target=target,seed=seed,rows=m,columns=n,nonzeros=target,memory=estimate,
                host_pipeline_allowance_bytes=host,raw_response_allowance_bytes=raw,partition='development',source_group='general-scale-'+family)
            if reasons:
                models.append(dict(**row,status='unsupported',reasons=reasons,planned_lanes=['native','fp32','fp4x2','copt-cpu-auto','copt-gpu-tight'],tolerance=1e-9))
                continue
            name=f'scale2-{family}-{target}-{seed}'
            existing=BASE/retained/(name+'.lpcsr') if retained else None
            if existing is not None and existing.exists():
                path=existing;witness=path.with_suffix('.witness.npz');require(witness.exists(),'retained construction witness missing')
                data=read(path)
                require(data['model_id']==name and data['shape']==(m,n) and len(data['values'])==target,'retained original dimensions differ')
                row['retained_preparation']=retained
                del data
            else:
                data,x,y=generate(family,target,seed)
                require(data['shape']==(m,n) and len(data['values'])==target,'prospective dimensions differ')
                path=out/(data['model_id']+'.lpcsr');write(path,data)
                witness=out/(data['model_id']+'.witness.npz');np.savez_compressed(witness,primal=x,dual=y)
                del data,x,y
            row.update(status='generated',model=ref(path),construction=ref(witness),construction_not_solver_input=True)
            row=describe(row);require(row['bipartite_components']==1,'frontier construction disconnected');models.append(row)
            print(dict(family=family,seed=seed,status='generated',components=row['bipartite_components']),flush=True)
    require(sum(m['status']=='generated' for m in models)==6 and len(models)==18,'prospective 16 M coverage differs')
    put(out/'manifest.json',dict(status='complete',models=models,generator=ref(__file__),structural_generator=ref(ROOT/'tools/lp_general_scale_models.py'),
        retained_preparation=ref(BASE/'resources'/(retained+'.settlement.json')) if retained else None,
        claim='All six families and three seeds retained. Six models admitted solely by current dimension and complete pipeline allowances; twelve unsupported models are not performance-selected.'))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--id',required=True);p.add_argument('--retained');a=p.parse_args();run(a.id,a.retained)
