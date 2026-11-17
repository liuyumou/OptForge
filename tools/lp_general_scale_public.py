"""Bounded public MPS import, independently compared before LP relaxation."""
import argparse
import gzip
from pathlib import Path
import shutil
import urllib.request
import numpy as np
from lp_general_common import BASE,put,ref,require
from lp_general_scale_io import write,memory_estimate

SOURCES={
    'square31':'https://miplib.zib.de/WebData/instances/square31.mps.gz',
    'pds-100':'https://plato.asu.edu/ftp/lptestset/pds/pds-100.bz2',
    'scpm1':'https://plato.asu.edu/ftp/lptestset/scpm1.mps.bz2',
}

def bounded_copy(source,dest,limit):
    total=0
    while block:=source.read(1<<20):
        total+=len(block);require(total<=limit,'public input byte ceiling');dest.write(block)

def convert(path,output,name):
    import coptpy as cp
    from scipy import sparse
    from scipy.optimize._highspy import _core
    h=_core._Highs();h.setOptionValue('output_flag',False);h.setOptionValue('threads',4)
    h.setOptionValue('small_matrix_value',1e-12)
    require(h.readModel(str(path))==_core.HighsStatus.kOk,'independent MPS reader')
    lp=h.getLp();m,n=lp.num_row_,lp.num_col_;a=lp.a_matrix_
    require(a.format_==_core.MatrixFormat.kColwise,'independent original column order')
    require(h.getModel().hessian_.dim_==0,'linear original only')
    hm=sparse.csc_matrix((a.value_,a.index_,a.start_),shape=(m,n)).tocsr();hm.sort_indices()
    estimate=memory_estimate(m,n,hm.nnz)
    require(estimate['admits_domain'] and estimate['host_allowance_bytes']<15<<30 and estimate['device_allowance_bytes']<12<<30,'public memory/domain preflight')
    env=cp.Envr();model=env.createModel();model.setParam('Logging',0);model.setParam('Threads',4);model.setParam('MatrixTol',0.)
    model.read(str(path));cm=model.getA().tocsr();cm.sort_indices()
    require(cm.shape==hm.shape and np.array_equal(cm.indptr,hm.indptr) and np.array_equal(cm.indices,hm.indices) and np.array_equal(cm.data.view('u8'),hm.data.view('u8')),'independent original matrix mismatch')
    def bound(values):
        a=np.asarray(values,dtype=np.float64);return np.where(a>=cp.COPT.INFINITY,np.inf,np.where(a<=-cp.COPT.INFINITY,-np.inf,a))
    cols=model.getVars();rows=model.getConstrs()
    data=dict(model_id='public-'+name+'-continuous-original',shape=(m,n),column_ids=np.arange(n,dtype=np.uint32),row_ids=np.arange(m,dtype=np.uint32),
        pointers=cm.indptr,indices=cm.indices,values=cm.data,
        lower=bound(model.getInfo('LB',cols)),upper=bound(model.getInfo('UB',cols)),row_lower=bound(model.getInfo('LB',rows)),row_upper=bound(model.getInfo('UB',rows)),
        sense='minimize' if model.ObjSense==cp.COPT.MINIMIZE else 'maximize',offset=model.ObjConst)
    for key,expected in [('lower',lp.col_lower_),('upper',lp.col_upper_),('row_lower',lp.row_lower_),('row_upper',lp.row_upper_)]:
        require(np.array_equal(data[key],np.asarray(expected)),'independent original bounds '+key)
    c=np.asarray(model.getInfo('Obj',cols));require(np.array_equal(c,np.asarray(lp.col_cost_)),'independent original objective')
    require(data['offset']==lp.offset_ and (model.ObjSense==cp.COPT.MINIMIZE)==(lp.sense_==_core.ObjSense.kMinimize),'objective sense/offset')
    data['objective_indices']=np.flatnonzero(c).astype(np.uint32);data['objective_values']=c[c!=0]
    integral=sum(int(t)!=0 for t in lp.integrality_)
    write(output,data)
    return dict(name=name,family='public-'+name,source_group='MIPLIB-square' if name.startswith('square') else 'Mittelmann-'+name,status='generated',
        model=ref(output),original=ref(path),rows=m,columns=n,nonzeros=cm.nnz,memory=estimate,partition='development',
        relaxed_integral_columns=integral,presolve_applied=False,independent_readers=dict(copt='8.0.6',highs=h.version()),
        exact_original_arrays_agree=True)

def run(identity,names):
    out=BASE/identity;out.mkdir(exist_ok=False);results=[]
    for name in names:
        url=SOURCES[name];archive=out/(name+('.mps.gz' if url.endswith('.gz') else '.mps.bz2'))
        try:
            with urllib.request.urlopen(url,timeout=30) as response,archive.open('xb') as dest:bounded_copy(response,dest,100<<20)
        except Exception as error:
            results.append(dict(name=name,status='inaccessible',url=url,reason=str(error)));continue
        path=out/(name+'.mps')
        import bz2
        compressed=out/(name+'.mpc') if name=='pds-100' else path
        with (gzip.open if url.endswith('.gz') else bz2.open)(archive,'rb') as src,compressed.open('xb') as dest:bounded_copy(src,dest,1<<30)
        expansion=None
        if name=='pds-100':
            import subprocess
            source=out/'emps.c';url_source='https://netlib.org/lp/data/emps.c'
            with urllib.request.urlopen(url_source,timeout=15) as src,source.open('xb') as dest:bounded_copy(src,dest,1<<20)
            binary=out/'emps';subprocess.run(['cc','-O2','-std=gnu89',str(source),'-o',str(binary)],check=True)
            with path.open('xb') as dest:
                # Inherit the admitted supervisor's 512 MiB file ceiling.
                subprocess.run([str(binary),str(compressed)],stdout=dest,check=True)
            expansion=dict(source=ref(source),url=url_source,compressed=ref(compressed),binary=ref(binary))
        row=convert(path,out/(name+'.lpcsr'),name);row.update(url=url,archive=ref(archive),expansion=expansion);results.append(row)
        print({k:row[k] for k in ['name','rows','columns','nonzeros']},flush=True)
    put(out/'manifest.json',dict(status='complete',models=results,source=ref(__file__),scope='Original public continuous relaxations; no MIP presolve. Inaccessible inputs remain recorded.'))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--id',required=True);p.add_argument('--names',nargs='+',choices=list(SOURCES),default=list(SOURCES));a=p.parse_args();run(a.id,a.names)
