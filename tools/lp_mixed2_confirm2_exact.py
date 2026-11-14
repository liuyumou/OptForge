"""Verify every retained numerical trajectory against source-bound admission."""
import hashlib
import json
from lp_mixed2_confirm2_common import BASE, ROOT, load, put, ref, require
from lp_mixed2_reuse_admit import numerical


def main():
    freeze=load(BASE/'confirmation-freeze.json')
    pilot=BASE/'resource-pilot-v1/result.json'
    require(ref(pilot) in freeze['admissions'],'pilot binding missing')
    expected={};controls=[]
    for session in load(pilot)['sessions']:
        for record in session['records'][:4]:
            item=record['result'];raw=(ROOT/item['path']).read_bytes()
            require(hashlib.sha256(raw).hexdigest()==item['sha256'],'admitted response changed')
            r=json.loads(raw);key=(r['model_sha256'],r['tier'],r['lane'])
            require(key not in expected,'duplicate admitted scenario')
            expected[key]=numerical(r);controls.append(item)
    require(len(expected)==64,'admitted scenario coverage')
    rows=[];counts={}
    for index in range(32):
        paths=sorted((BASE/f'confirmation-b{index:02d}').glob('*-r[0-9][0-9].json'))
        for p in paths:
            raw=p.read_bytes();r=json.loads(raw);key=(r['model_sha256'],r['tier'],r['lane'])
            require(key in expected and numerical(r)==expected[key],'retained trajectory differs from admission: '+str(p))
            counts[key]=counts.get(key,0)+1
            rows.append(dict(path=str(p.relative_to(ROOT)),sha256=hashlib.sha256(raw).hexdigest()))
        print(dict(block=index,responses=len(paths),exact=True),flush=True)
    put(BASE/'exact-final-v1.json',dict(status='passed',source=ref(__file__),comparison=ref(ROOT/'tools/lp_mixed2_reuse_admit.py'),
        controls=controls,responses=len(rows),records=rows,covered_scenarios=len(counts),
        contract='Exact numerical fields, endpoints, certificates, audits, recovery, checkpoints and work; timing and checker binary identity excluded by the admitted comparison.'))


if __name__=='__main__':main()
