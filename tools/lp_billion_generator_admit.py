"""Validate streaming generation and original construction against the unchanged checker."""
import json
import subprocess
import numpy as np
from lp_billion_common import BASE, ROOT, put, ref, require, load
from lp_billion_arrays import read
from lp_billion_generate import generate, FAMILIES
from lp_general_oracle import settings


def document(manifest):
    arrays={k:read(BASE,v) for k,v in manifest['arrays'].items()}
    finite=lambda value: dict(kind='finite',value=float(value)) if np.isfinite(value) else dict(kind='negative_infinity' if value<0 else 'positive_infinity')
    n,m=manifest['columns'],manifest['rows'];ids=arrays['column_ids'];o=arrays['offsets']
    return dict(schema_version=1,model_id=manifest['model_id'],variables=[dict(id=int(ids[j]),domain='continuous',lower=finite(arrays['column_lower'][j]),upper=finite(arrays['column_upper'][j])) for j in range(n)],
        constraints=[dict(id=int(arrays['row_ids'][i]),lower=finite(arrays['row_lower'][i]),upper=finite(arrays['row_upper'][i]),terms=[dict(variable_id=int(ids[arrays['indices'][k]]),coefficient=float(arrays['values'][k])) for k in range(int(o[i]),int(o[i+1]))]) for i in range(m)],
        objective=dict(sense=manifest['sense'],offset=manifest['offset'],terms=[dict(variable_id=int(ids[j]),coefficient=float(c)) for j,c in zip(arrays['objective_indices'],arrays['objective_values'])]))


def run(identity):
    out=BASE/identity;out.mkdir(exist_ok=False);rows=[]
    binary=BASE/'image-v1/executor';old=ROOT/'artifacts/gpup-general-v1/scale-image-v14/executor'
    for family in FAMILIES:
        name=identity+'-'+family
        generate(name,family,16384,861199)
        model=BASE/name/'model.json';witness=load(BASE/name/'construction.json')
        doc=document(load(model));path=out/(family+'.json');put(path,doc)
        # A separate sparse graph routine checks the whole small incidence graph.
        n,m=load(model)['columns'],load(model)['rows'];parent=list(range(n+m))
        def find(a):
            while parent[a]!=a:parent[a]=parent[parent[a]];a=parent[a]
            return a
        for i,row in enumerate(doc['constraints']):
            for term in row['terms']:parent[find(n+i)]=find(term['variable_id'])
        require(len({find(i) for i in range(n+m)})==1,'small independent graph connectivity')
        request=dict(settings=settings('native'),endpoint=witness)
        a=subprocess.run([str(binary),'assess',str(model),str(BASE)],input=json.dumps(request)+'\n',capture_output=True,text=True)
        require(a.returncode==0,'construction array check '+a.stderr)
        response=json.loads(a.stdout);put(out/(family+'.response.json'),response)
        x=read(BASE,witness['primal']).tolist();y=read(BASE,witness['dual']).tolist()
        b=subprocess.run([str(old),'assess',str(path)],input=json.dumps(dict(settings=settings('native'),primal=x,dual=y))+'\n',capture_output=True,text=True)
        require(b.returncode==0,'original construction check '+b.stderr)
        prior=json.loads(b.stdout)
        for k in ['accepted','feasible','objective','bound','gap_upper']:require(prior[k]==response[k],'construction certificate equality '+k)
        require(response['accepted'],'strict generated construction certificate')
        put(out/(family+'.original.json'),prior)
        rows.append(dict(family=family,model=ref(model),response=ref(out/(family+'.response.json')),original=ref(out/(family+'.original.json')),connected=True))
    put(out/'result.json',dict(status='passed',rows=rows,generator=ref(ROOT/'tools/lp_billion_generate.py')))

if __name__=='__main__':run('generator-admission-v1')
