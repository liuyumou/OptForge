"""Exact compact original-model transport; bounded arrays, no coefficient rounding."""
import hashlib
import json
import math
from pathlib import Path
import struct
import numpy as np

MAGIC=b'LPCSRA01'
MAX_DIMENSION=1<<20
MAX_NONZEROS=1<<26

def write(path, data):
    """Write canonical CSR and sparse objective, preserving explicit zero terms."""
    n,m=map(int,data['shape'][::-1]); z=len(data['values']); q=len(data['objective_indices'])
    identity=data['model_id'].encode(); assert 0<len(identity)<=1024
    if max(n,m)>MAX_DIMENSION or z>MAX_NONZEROS or q>n:raise ValueError('compact resource domain')
    with Path(path).open('xb') as f:
        f.write(struct.pack('<8sQQQQdQQ',MAGIC,n,m,z,{'minimize':0,'maximize':1}[data['sense']],data['offset'],len(identity),q));f.write(identity)
        for key,dt,size in [('column_ids','<u4',n),('row_ids','<u4',m),('lower','<f8',n),('upper','<f8',n),
                           ('row_lower','<f8',m),('row_upper','<f8',m),('pointers','<u8',m+1),
                           ('indices','<u4',z),('values','<f8',z),('objective_indices','<u4',q),('objective_values','<f8',q)]:
            a=np.asarray(data[key],dtype=dt)
            if a.shape!=(size,):raise ValueError('compact array shape '+key)
            a.tofile(f)
    return read(path)

def read(path):
    """Validate all transport domains before handing arrays to any native library."""
    path=Path(path)
    with path.open('rb') as f:
        header=f.read(64)
        if len(header)!=64:raise ValueError('compact short header')
        magic,n,m,z,sense,offset,idlen,q=struct.unpack('<8sQQQQdQQ',header)
        if magic!=MAGIC or max(n,m)>MAX_DIMENSION or z>MAX_NONZEROS or q>n or not 1<=idlen<=1024 or sense>1 or not math.isfinite(offset):raise ValueError('compact header domain')
        expected=64+idlen+20*(n+m)+8*(m+1)+12*(z+q)
        if path.stat().st_size!=expected:raise ValueError('compact byte length')
        identity=f.read(idlen).decode()
        if not identity.strip():raise ValueError('compact empty identity')
    data=dict(model_id=identity,shape=(m,n),sense=['minimize','maximize'][sense],offset=offset)
    at=64+idlen
    for key,dt,size in [('column_ids','<u4',n),('row_ids','<u4',m),('lower','<f8',n),('upper','<f8',n),
                       ('row_lower','<f8',m),('row_upper','<f8',m),('pointers','<u8',m+1),
                       ('indices','<u4',z),('values','<f8',z),('objective_indices','<u4',q),('objective_values','<f8',q)]:
        data[key]=np.memmap(path,mode='r',dtype=dt,offset=at,shape=(size,)) if size else np.empty(0,dtype=dt)
        at+=np.dtype(dt).itemsize*size
    for key in ['column_ids','row_ids','objective_indices']:
        a=data[key]
        if np.any(a[1:]<=a[:-1]):raise ValueError('compact canonical '+key)
    for key in ['values','objective_values']:
        if not np.isfinite(data[key]).all():raise ValueError('compact finite '+key)
    for lo,hi in [('lower','upper'),('row_lower','row_upper')]:
        a,b=data[lo],data[hi]
        if np.isnan(a).any() or np.isnan(b).any() or np.isposinf(a).any() or np.isneginf(b).any() or np.any(a>b):raise ValueError('compact bounds')
    p=data['pointers'];i=data['indices']
    if p[0]!=0 or p[-1]!=z or np.any(p[1:]<p[:-1]) or np.any(i>=n) or np.any(data['objective_indices']>=n):raise ValueError('compact CSR domain')
    # Check in bounded chunks: row starts are the only permitted non-increases.
    for lo in range(0,z,1<<20):
        hi=min(z,lo+(1<<20));bad=np.flatnonzero(i[max(1,lo):hi]<=i[max(1,lo)-1:hi-1])+max(1,lo)
        if len(bad):
            where=np.searchsorted(p,bad)
            if np.any(p[where]!=bad):raise ValueError('compact row positions not canonical')
    return data

def from_document(doc):
    if doc['schema_version']!=1:raise ValueError('model version')
    variables=sorted(doc['variables'],key=lambda x:x['id']);rows=sorted(doc['constraints'],key=lambda x:x['id'])
    if any(v['domain']!='continuous' for v in variables):raise ValueError('continuous original model required')
    ids={v['id']:j for j,v in enumerate(variables)}
    if len(ids)!=len(variables):raise ValueError('duplicate column ID')
    if any(type(v['id']) is not int or not 0<=v['id']<=0xffffffff for v in variables+rows):raise ValueError('model ID domain')
    def b(v):
        if v['kind']=='finite':return v['value']
        if v['kind'] not in ['negative_infinity','positive_infinity']:raise ValueError('bound kind')
        return -math.inf if v['kind']=='negative_infinity' else math.inf
    ind=[];values=[];p=[0]
    for row in rows:
        for t in sorted(row['terms'],key=lambda t:t['variable_id']):ind.append(ids[t['variable_id']]);values.append(t['coefficient'])
        p.append(len(ind))
    obj=sorted(doc['objective']['terms'],key=lambda t:t['variable_id'])
    return dict(model_id=doc['model_id'],shape=(len(rows),len(variables)),sense=doc['objective']['sense'],offset=doc['objective']['offset'],
        column_ids=[v['id'] for v in variables],row_ids=[r['id'] for r in rows],lower=[b(v['lower']) for v in variables],upper=[b(v['upper']) for v in variables],
        row_lower=[b(r['lower']) for r in rows],row_upper=[b(r['upper']) for r in rows],pointers=p,indices=ind,values=values,
        objective_indices=[ids[t['variable_id']] for t in obj],objective_values=[t['coefficient'] for t in obj])

def digest(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        while b:=f.read(1<<20):h.update(b)
    return h.hexdigest()

def memory_estimate(rows,columns,nonzeros,objective_terms=None):
    """Conservative preflight allowances, not measured RSS or a peak enclosure."""
    q=columns if objective_terms is None else objective_terms
    return dict(compact_bytes=1100+20*(rows+columns)+8*(rows+1)+12*(nonzeros+q),
        host_allowance_bytes=180*nonzeros+1000*(rows+columns)+(512<<20),
        device_allowance_bytes=64*nonzeros+512*(rows+columns)+(64<<20),
        admits_domain=max(rows,columns)<=MAX_DIMENSION and nonzeros<=MAX_NONZEROS,
        note='Allowance assumes sequential solver/checker processes. Tile padding and actual buffer accounting must independently fit before execution.')
