"""Seeded operator groups; all related scenarios remain in one partition."""
import argparse
import hashlib
import json
import numpy as np
from lp_gpup9_common import BASE, ROOT, load, put, ref, require
from lp_gpup9_protocol import descriptors, verify_design
from lp_mixed2_fp4_cpu import fixture


def operator(group):
    n=group['size'];rng=np.random.default_rng(group['seed'])
    a=np.eye(n)
    if group['family'].startswith('sparse'):
        a[np.arange(n),np.arange(n)]+=rng.integers(-18,19,size=n)/(73*n)
    else:
        # Independent signed perturbations, bounded row norm and finite exponents.
        a+=rng.integers(-18,19,size=(n,n))/(73*n)
    if group['family'].startswith(('coupled','sparse','small')):
        a[np.arange(n),(np.arange(n)+1)%n]+=.5
    return a,rng


def materialize(partition):
    d=verify_design(load(BASE/'design-v2.json'))
    if partition=='holdout':
        f=load(BASE/'holdout-freeze.json')
        require(f['design']==ref(BASE/'design-v2.json'),'holdout requires frozen finalists')
        require(not list((BASE/'resources').glob('holdout-*.reservation.json')),'holdout already attempted')
    out=BASE/'models-v2'/partition;out.mkdir(parents=True,exist_ok=False)
    groups={};digests=[]
    for group in d['partitions'][partition]:
        a,rng=operator(group)
        op_hash=hashlib.sha256(a.astype('<f8').tobytes()).hexdigest()
        require(op_hash not in digests,'duplicate operator in partition');digests.append(op_hash)
        for prior in (BASE/'models-v2').glob('*/manifest.json'):
            require(op_hash not in load(prior)['operator_hashes'],'operator split leakage')
        doc=fixture(a,group['id']);items=[]
        for scenario in range(4):
            x=rng.integers(-18,19,size=group['size'])/37
            y=rng.integers(-14,15,size=group['size'])/29
            rhs=a@x;c=a.T@y
            doc['model_id']=group['id']+f'-s{scenario}'
            for row,value in zip(doc['constraints'],rhs):
                row['lower']['value']=row['upper']['value']=float(value)
            doc['objective']['offset']=3.25+.125*scenario
            doc['objective']['terms']=[dict(variable_id=3*j+7,coefficient=float(v)) for j,v in enumerate(c) if v!=0]
            path=out/(doc['model_id']+'.json')
            with path.open('x') as stream:json.dump(doc,stream,separators=(',',':'),allow_nan=False)
            require(path.stat().st_size<=384<<20,'model exceeds admitted byte limit')
            items.append(ref(path))
        groups[group['id']]=dict(descriptor=group,operator_sha256=op_hash,models=items)
        del doc,a
        print(dict(partition=partition,group=group['id']),flush=True)
    put(out/'manifest.json',dict(schema_version=1,kind='gpup9-models',design=ref(BASE/'design-v2.json'),
        partition=partition,groups=groups,operator_hashes=digests,generator=ref(__file__)))
    if partition=='holdout':
        put(BASE/'holdout-model-binding.json',dict(freeze=ref(BASE/'holdout-freeze.json'),
            manifest=ref(out/'manifest.json')))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('partition',choices=['admission','screening','validation','holdout']);materialize(p.parse_args().partition)
