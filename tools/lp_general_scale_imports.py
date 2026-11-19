"""Bind reused exact-checker sources without changing historical budget receipts."""
import argparse
from lp_general_common import ROOT,BASE,put,ref,require,load
SOURCES=['research/lp-mixed2-checker2/src/exact_math.rs','research/lp-mixed2-checker2/src/cached_certificate.rs',
         'research/lp-fp4-checker/src/prepared_feasibility.rs','crates/optimizer-lp/src/outward.rs','crates/optimizer-lp/src/reduce.rs',
         'research/lp-general-lowbit/src/host-lp/Cargo.toml']

def snapshot(identity):
    out=BASE/'sources'/identity/'checker-imports';out.mkdir(exist_ok=False);rows=[]
    for name in SOURCES:
        p=ROOT/name;q=out/name;q.parent.mkdir(parents=True,exist_ok=True);q.write_bytes(p.read_bytes())
        rows.append(dict(original=ref(p),retained=ref(q)))
    put(out/'manifest.json',dict(sources=rows,source=ref(__file__)))

def validate(identity):
    p=BASE/'sources'/identity/'checker-imports/manifest.json'
    for row in load(p)['sources']:
        require(ref(ROOT/row['original']['path'])==row['original'],'imported checker changed')
        require(ref(ROOT/row['retained']['path'])==row['retained'],'retained checker changed')
    return ref(p)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--id',required=True);snapshot(p.parse_args().id)
