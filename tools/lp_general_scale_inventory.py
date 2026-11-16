"""Measured input structure and prospective capacity; no solver-outcome selection."""
import argparse
import numpy as np
from lp_general_common import BASE,put,load,ref,require
from lp_general_scale_io import read,memory_estimate

def describe(item):
    from scipy import sparse
    from scipy.sparse.csgraph import connected_components
    from lp_general_common import ROOT
    p=ROOT/item['model']['path'];require(ref(p)==item['model'],'inventory original bytes')
    d=read(p);m,n=d['shape'];z=len(d['values'])
    def distribution(a):
        return dict(min=int(a.min()),p50=float(np.median(a)),p90=float(np.quantile(a,.9)),p99=float(np.quantile(a,.99)),max=int(a.max()),mean=float(a.mean()),zeros=int(np.sum(a==0)))
    rows=np.diff(d['pointers']);columns=np.bincount(d['indices'],minlength=n)
    a=sparse.csr_matrix((np.ones(z,dtype=np.int8),d['indices'],d['pointers']),shape=(m,n))
    graph=sparse.bmat([[None,a],[a.T,None]],format='csr')
    count,labels=connected_components(graph,directed=False);sizes=np.bincount(labels)
    magnitude=np.abs(d['values']);positive=magnitude[magnitude>0]
    return dict(**item,row_degree=distribution(rows),column_degree=distribution(columns),bipartite_components=int(count),
        largest_component=int(sizes.max()),isolated_vertices=int(np.sum(sizes==1)),nontrivial_components=int(np.sum(sizes>1)),
        coefficient_min_abs=float(positive.min()),coefficient_max_abs=float(positive.max()),explicit_zero_terms=int(np.sum(magnitude==0)),
        equality_rows=int(np.sum(d['row_lower']==d['row_upper'])),finite_variable_bounds=int(np.sum(np.isfinite(d['lower'])&np.isfinite(d['upper']))))

def run(identity,version):
    out=BASE/identity;out.mkdir(exist_ok=False);models=[];unavailable=[]
    for name in [f'scale-models-1000000-v{version}',f'scale-models-4000000-v{version}','scale-public-v1','scale-public-pds-v2']:
        for item in load(BASE/name/'manifest.json')['models']:
            if item['status']=='generated':
                row=describe(item)
                if version>1 and 'construction' in item:require(row['bipartite_components']==1,'coupled construction gate')
                models.append(row)
            else:unavailable.append(item)
    capacity=[]
    for target in [1000000,4000000,16000000,64000000,128000000,256000000,512000000,1000000000,2000000000,8000000000]:
        for family,degree,aspect in [('irregular',16,1),('wide',16,4),('tall',16,.25),('coupled_blocks',64,1)]:
            m=target//degree;n=max(64,int(m*aspect));e=memory_estimate(m,n,m*degree)
            failures=[]
            if not e['admits_domain']:failures.append('current dimension/nonzero domain')
            if e['compact_bytes']>512<<20:failures.append('current per-file output ceiling')
            if e['host_allowance_bytes']>=15<<30:failures.append('host allowance')
            if e['device_allowance_bytes']>=12<<30:failures.append('device allowance')
            capacity.append(dict(target=target,family=family,rows=m,columns=n,estimate=e,unsupported_reasons=failures,execution_admitted=False))
    put(out/'result.json',dict(status='complete',models=models,unavailable=unavailable,capacity=capacity,source=ref(__file__),
        note='Structure measured before full scale comparisons; all generated seeds retained. Capacity allowances are not measured peaks or permission to run.'))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--id',required=True);p.add_argument('--version',type=int,default=1);a=p.parse_args();run(a.id,a.version)
