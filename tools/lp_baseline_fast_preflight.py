"""New CPU conversion gate against retained large canonical bytes; no solve."""
import json
from pathlib import Path
import time

from lp_baseline_common_v4 import BASE, ROOT, digest, load, put, ref, require
from lp_baseline_fast import install
from lp_baseline_contract import canonicalize


def main():
    install()
    proposal=load(ROOT/'benchmarks/configs/lp-external-baseline-proposal-v2.json')
    instance=next(i for i in proposal['instances'] if i['id']=='gpup-extension-dense_block-65536')
    model=ROOT/instance['model']['path']
    retained=ROOT/'artifacts/gpup-external-baseline-v3/jobs/screening-gpup-extension-dense_block-65536-0-highs-cpu/solve/canonical.json'
    started=time.monotonic_ns()
    document=canonicalize(model.read_bytes())
    encoded=(json.dumps(document,sort_keys=True,indent=2,allow_nan=False)+'\n').encode()
    require(digest(encoded)==ref(retained)['sha256'],'compiled conversion changed canonical bytes')
    elapsed=time.monotonic_ns()-started
    put(BASE/'compiled-conversion-preflight.json',dict(status='passed',original=ref(model),
        retained_canonical=ref(retained),canonical_bytes=len(encoded),elapsed_ns=elapsed,
        source=ref(Path(__file__)),validator=ref(ROOT/'tools/lp_baseline_fast.py'),
        original_checker_rerun=False,solver_calls=0,gpu_calls=0))
    print('Exact retained canonical bytes:',len(encoded),'elapsed seconds:',elapsed/1e9,flush=True)


if __name__=='__main__': main()
