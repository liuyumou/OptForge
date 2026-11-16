"""Bounded array generation for coupled, independently seeded scale fixtures."""
import argparse
import numpy as np
from lp_general_common import BASE,put,ref,require
from lp_general_scale_io import write,memory_estimate

FAMILIES=('irregular','wide','tall','coupled_blocks','ill_scaled','degenerate')

def generate(family,target,seed):
    require(family in FAMILIES and 256<=target<=64000000,'generator domain')
    rng=np.random.default_rng(seed)
    average=64 if family=='coupled_blocks' else 16
    degree=24 if family=='irregular' else average
    m=max(32,target//average)
    n=max(64,m*4 if family=='wide' else (m//4 if family=='tall' else m))
    estimate=memory_estimate(m,n,m*degree)
    require(estimate['admits_domain'],'generator dimension domain; retain unsupported scale')
    require(estimate['host_allowance_bytes']<15<<30 and estimate['device_allowance_bytes']<12<<30,'generator memory preflight')
    lengths=np.resize(np.array([8,16,24,16]),m) if family=='irregular' else np.full(m,degree)
    keep=np.arange(degree)[None,:]<lengths[:,None]
    if family=='coupled_blocks':
        # 48 nearby positions plus 16 long-range positions, with every row
        # independently sampled. Duplicate positions are avoided algebraically.
        n=((n+63)//64)*64
        starts=(np.arange(m,dtype=np.int64)//32*64)%n
        local=(starts[:,None]+np.arange(48))%n
        remote=(starts[:,None]+64*(1+rng.integers(0,max(1,n//64-1),size=(m,1)))+np.arange(48,64))%n
        indices=np.sort(np.concatenate([local,remote],axis=1),axis=1)
    else:
        # A backbone covers every variable and connects the rows; independent
        # global links prevent interval/permutation construction from splitting
        # a large wide model into many independent small problems.
        indices=np.empty((m,degree),dtype=np.int64)
        if family=='wide':
            indices[:,:4]=4*np.arange(m)[:,None]+np.arange(4)
            indices[:,4]=4*((np.arange(m)+1)%m);fixed=5
        else:
            indices[:,:3]=(np.arange(m)[:,None]+np.arange(3))%n;fixed=3
        for j in range(fixed,degree):
            candidate=rng.integers(0,n,size=m)
            while True:
                bad=np.any(indices[:,:j]==candidate[:,None],axis=1)
                if not np.any(bad):break
                candidate[bad]=(candidate[bad]+1)%n
            indices[:,j]=candidate
        # Keep the short-row backbone before sorting the retained positions.
        indices=np.where(keep,indices,n)
        indices.sort(axis=1)
        indices=np.where(keep,indices,0)
    values=rng.uniform(-1.,1.,size=(m,degree))
    values=np.where(np.abs(values)<.03125,np.copysign(.03125,values),values)
    scale=np.exp2((np.arange(m)%17-8)*2) if family=='ill_scaled' else np.ones(m)
    values*=scale[:,None]
    values=np.where(keep,values,0.)
    if family=='degenerate':
        indices[2::3]=indices[1:m-1:3];values[2::3]=values[1:m-1:3]
    x=rng.choice([0.,.25,.5,.75,1.],size=n)
    # Original sequential row activities are used, not BLAS/dot order.
    activity=np.zeros(m)
    for j in range(degree):activity+=values[:,j]*x[indices[:,j]]
    side=np.arange(m)%4
    y=np.where(side==0,rng.uniform(.1,1.,m)/scale,np.where(side==1,-rng.uniform(.1,1.,m)/scale,0.))
    lower=np.where(side==0,activity,activity-scale)
    upper=np.where(side==1,activity,activity+scale)
    lower[side==2]=-np.inf;upper[side==3]=np.inf
    c=np.zeros(n)
    # np.add.at traverses the supplied row-major order without duplicate
    # coalescing. The independent serial certificate checks construction.
    np.add.at(c,indices.reshape(-1),(values*y[:,None]).reshape(-1))
    reduced=rng.uniform(.1,1.,n)
    c+=np.where(x==0,reduced,np.where(x==1,-reduced,0.))
    data=dict(model_id=f'scale2-{family}-{target}-{seed}',shape=(m,n),sense='minimize',offset=3.25,
        column_ids=np.arange(n,dtype=np.uint32),row_ids=np.arange(m,dtype=np.uint32),lower=np.zeros(n),upper=np.ones(n),
        row_lower=lower,row_upper=upper,pointers=np.r_[0,np.cumsum(lengths)].astype(np.uint64),
        indices=indices[keep].astype(np.uint32),values=values[keep],objective_indices=np.flatnonzero(c).astype(np.uint32),objective_values=c[c!=0])
    return data,x,y

def materialize(identity,target,seeds):
    out=BASE/identity;out.mkdir(exist_ok=False);rows=[]
    for family in FAMILIES:
        for seed in seeds:
            try:data,x,y=generate(family,target,seed)
            except ValueError as error:
                rows.append(dict(family=family,target=target,seed=seed,status='unsupported',reason=str(error)));continue
            path=out/(data['model_id']+'.lpcsr');write(path,data)
            witness=out/(data['model_id']+'.witness.npz');np.savez_compressed(witness,primal=x,dual=y)
            row=dict(family=family,target=target,seed=seed,status='generated',model=ref(path),construction=ref(witness),
                rows=data['shape'][0],columns=data['shape'][1],nonzeros=len(data['values']),memory=memory_estimate(*data['shape'],len(data['values'])),
                partition='development',source_group='general-scale-'+family,construction_not_solver_input=True)
            rows.append(row);print({k:row[k] for k in ['family','seed','rows','columns','nonzeros']},flush=True)
    put(out/'manifest.json',dict(status='complete',models=rows,generator=ref(__file__),claim='Coupled structural fixtures; not independent application families or certified solver results.'))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--id',required=True);p.add_argument('--target',type=int,required=True);p.add_argument('--seeds',type=int,nargs='+',default=[831001,831002,831003]);a=p.parse_args()
    materialize(a.id,a.target,a.seeds)
