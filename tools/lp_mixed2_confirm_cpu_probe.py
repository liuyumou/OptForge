"""Fixed CPU-only whole-file/streaming hash probes; no scientific timing claim."""
import argparse
import hashlib
import time
from lp_mixed2_confirm_common import BASE, ROOT, load, put, ref, require


def run(method):
    out=BASE/('hash-'+method+'-v1');out.mkdir(exist_ok=False)
    freeze=load(BASE/'confirmation-freeze.json')
    inputs=[p for group in freeze['groups'].values() for p in group]
    put(out/'manifest.json',dict(source=ref(__file__),inputs=inputs,method=method,rounds=12,
        scientific_timing=False,order='whole then streaming; diagnostic, not randomized causal evidence'))
    rows=[]
    for index in range(12):
        started=time.monotonic_ns()
        for item in inputs:
            p=ROOT/item['path']
            if method=='whole':digest=hashlib.sha256(p.read_bytes()).hexdigest()
            else:
                h=hashlib.sha256()
                with p.open('rb') as stream:
                    while block:=stream.read(1<<20):h.update(block)
                digest=h.hexdigest()
            require(digest==item['sha256'],'original model bytes changed')
        row=dict(round=index,elapsed_ns=time.monotonic_ns()-started,models=len(inputs))
        put(out/f'round-{index:02d}.json',row);rows.append(row)
        print(row,flush=True)
    put(out/'result.json',dict(status='passed',rounds=rows,method=method,scientific_timing=False))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('method',choices=['whole','streaming']);run(p.parse_args().method)
