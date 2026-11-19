"""Bounded streaming generation of connected LPs; construction witnesses stay separate."""
import argparse
import time
import numpy as np
from lp_billion_common import BASE, put, ref, require
from lp_billion_arrays import Writer, write

FAMILIES = ('irregular','wide','tall','coupled_blocks','ill_scaled','degenerate')
BATCH = 49152  # divisible by 3, 4 and 64; immutable generator version parameter

def generate(identity, family, target, seed):
    require(family in FAMILIES and 4096<=target<=1_000_000_000 and target%64==0,'generator domain')
    started=time.monotonic_ns()
    out=BASE/identity;out.mkdir(exist_ok=False)
    average=64 if family=='coupled_blocks' else 16
    m=target//average
    n=m*4 if family=='wide' else m//4 if family=='tall' else m
    n=max(64,n)
    if family=='coupled_blocks':n=max(128,(n+63)//64*64)
    rng=np.random.default_rng(seed)
    x=rng.integers(0,5,size=n,dtype=np.uint8).astype(np.float64)*.25
    y=np.empty(m);objective=np.zeros(n)
    writers={k:Writer(BASE,typ) for k,typ in [('offsets','u64le'),('indices','u32le'),('values','f64le'),('row_lower','f64le'),('row_upper','f64le')]}
    nnz=0;canonical_tiles=0;covered_nnz=0;writers['offsets'].add([0]);min_abs=float('inf');max_abs=0.
    for begin in range(0,m,BATCH):
        end=min(m,begin+BATCH);r=np.arange(begin,end,dtype=np.int64);b=len(r)
        degree=24 if family=='irregular' else average
        lengths=np.array([8,16,24,16],dtype=np.int64)[r%4] if family=='irregular' else np.full(b,degree,dtype=np.int64)
        keep=np.arange(degree)[None,:]<lengths[:,None]
        indices=np.empty((b,degree),dtype=np.int64)
        if family=='coupled_blocks':
            blocks=n//64;own=(r//32)%blocks
            indices[:,:48]=own[:,None]*64+(7*(r%32)[:,None]+np.arange(48))%64
            indices[:,48]=((own+1)%blocks)*64+r%64
            fixed=49
        elif family=='wide':
            indices[:,:4]=4*r[:,None]+np.arange(4);indices[:,4]=4*((r+1)%m);fixed=5
        else:
            indices[:,:3]=(r[:,None]+np.arange(3))%n;fixed=3
        for j in range(fixed,degree):
            candidate=rng.integers(0,n,size=b)
            while True:
                bad=np.any(indices[:,:j]==candidate[:,None],axis=1)
                if family=='coupled_blocks':bad|=candidate//64==own
                if not np.any(bad):break
                candidate[bad]=(candidate[bad]+1)%n
            indices[:,j]=candidate
        indices=np.where(keep,indices,n);indices.sort(axis=1);indices=np.where(keep,indices,0)
        values=rng.uniform(-1.,1.,size=(b,degree))
        values=np.where(np.abs(values)<.03125,np.copysign(.03125,values),values)
        scale=np.exp2((r%17-8)*2) if family=='ill_scaled' else np.ones(b)
        values*=scale[:,None];values=np.where(keep,values,0.)
        if family=='degenerate':
            destination=np.flatnonzero(r%3==2)
            require(not len(destination) or destination[0]>0,'duplicate block alignment')
            indices[destination]=indices[destination-1];values[destination]=values[destination-1]
        # Structural admission is checked for every generated row, not sampled.
        require(np.all(np.diff(np.where(keep,indices,n+np.arange(degree)),axis=1)>0),'canonical positions')
        require(np.all(indices[keep]<n) and np.all(values[keep]!=0) and np.all(np.isfinite(values)),'original nonzero domain')
        if family=='wide':
            require(np.all(np.any(indices[:,:,None]==(4*r[:,None]+np.arange(4))[:,None,:],axis=1)),'wide coverage backbone')
            require(np.all(np.any(indices==4*((r+1)%m)[:,None],axis=1)),'wide connectivity backbone')
        elif family=='coupled_blocks':
            require(np.all(np.any(indices==(((own+1)%blocks)*64+r%64)[:,None],axis=1)),'coupled ring bridge')
            require(np.all(np.sum(indices//64==own[:,None],axis=1)==48),'coupled local coverage')
        else:
            source=r-(r%3==2) if family=='degenerate' else r
            require(np.all(np.any(indices[:,:,None]==((source[:,None]+np.arange(3))%n)[:,None,:],axis=1)),'connected row backbone')
        keys=((r//32-begin//32)[:,None]*((n+31)//32)+indices//32)[keep]
        _,counts=np.unique(keys,return_counts=True)
        canonical_tiles+=int(np.count_nonzero(counts>=128));covered_nnz+=int(counts[counts>=128].sum())
        activity=np.zeros(b)
        for j in range(degree):activity+=values[:,j]*x[indices[:,j]]
        side=r%4
        dual=np.where(side==0,rng.uniform(.1,1.,b)/scale,np.where(side==1,-rng.uniform(.1,1.,b)/scale,0.))
        y[begin:end]=dual
        lo=np.where(side==0,activity,activity-scale);hi=np.where(side==1,activity,activity+scale)
        lo[side==2]=-np.inf;hi[side==3]=np.inf
        np.add.at(objective,indices.ravel(),(values*dual[:,None]).ravel())
        for name,v in [('indices',indices[keep]),('values',values[keep]),('row_lower',lo),('row_upper',hi)]:writers[name].add(v)
        writers['offsets'].add(nnz+np.cumsum(lengths));nnz+=int(lengths.sum())
        min_abs=min(min_abs,float(np.min(np.abs(values[keep]))));max_abs=max(max_abs,float(np.max(np.abs(values[keep]))))
    require(nnz==target,'exact original nonzero count')
    for begin in range(0,n,BATCH):
        end=min(n,begin+BATCH);reduced=rng.uniform(.1,1.,end-begin)
        objective[begin:end]+=np.where(x[begin:end]==0,reduced,np.where(x[begin:end]==1,-reduced,0.))
    arrays={k:w.finish() for k,w in writers.items()}
    extra={k:Writer(BASE,dtype) for k,dtype in [('column_ids','u32le'),('row_ids','u32le'),('column_lower','f64le'),('column_upper','f64le'),('objective_indices','u32le'),('objective_values','f64le')]}
    for begin in range(0,n,BATCH):
        end=min(n,begin+BATCH);indices=np.arange(begin,end,dtype=np.uint32);c=objective[begin:end];nz=c!=0
        extra['column_ids'].add(indices);extra['column_lower'].add(np.zeros(end-begin));extra['column_upper'].add(np.ones(end-begin))
        extra['objective_indices'].add(indices[nz]);extra['objective_values'].add(c[nz])
    for begin in range(0,m,BATCH):extra['row_ids'].add(np.arange(begin,min(m,begin+BATCH),dtype=np.uint32))
    arrays.update({k:w.finish() for k,w in extra.items()})
    model=dict(schema_version=1,model_id=f'billion-{family}-{target}-{seed}',rows=m,columns=n,nonzeros=nnz,sense='minimize',offset=3.25,arrays=arrays)
    put(out/'model.json',model)
    put(out/'construction.json',dict(primal=write(BASE,x),dual=write(BASE,y)))
    result=dict(status='generated',family=family,target=target,seed=seed,model=ref(out/'model.json'),construction=ref(out/'construction.json'),
        rows=m,columns=n,nonzeros=nnz,canonical_tiles=canonical_tiles,covered_nnz=covered_nnz,coefficient_abs_range=[min_abs,max_abs],elapsed_ns=time.monotonic_ns()-started,
        generator=ref(__file__),batch_rows=BATCH,connectivity='all-row algebraic backbone verified; cyclic coupled block bridge and full local coverage',
        construction_not_solver_input=True,partition='development')
    put(out/'result.json',result);print(result,flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--id',required=True);p.add_argument('--family',choices=FAMILIES,required=True);p.add_argument('--target',type=int,required=True);p.add_argument('--seed',type=int,default=861119);a=p.parse_args()
    generate(a.id,a.family,a.target,a.seed)
