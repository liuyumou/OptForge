"""Exact review-source bridge and CPU verification of retained refinement evidence.

The bridge projects declared current fixes onto their pre-review bytes solely
for checking a historical source archive. It never relabels measured workers or
substitutes the reviewed executable for a measured execution identity.
"""
import argparse
import functools
import hashlib
import json
from pathlib import Path
import subprocess

ROOT=Path(__file__).resolve().parents[1]
BASE='bf03f327ce8ddfa73749b6c88f78a2e5694485b1'
RECEIPT=ROOT/'docs/benchmarks/data/refine/review-source.json'
ALLOWED={
    'crates/optimizer-lp/src/refine.rs',
    'crates/optimizer-lp/tests/refine.rs',
    'crates/optimizer-experiment/src/lp_refine.rs',
    'tools/lp_refine_admission.py', 'tools/report_lp_refine.py',
    'tools/lp_refine_review.py', 'tests/integration/test_lp_refine_review.py',
}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_receipt(value):
    if set(value)!={'identity','base_revision','files'} or value['identity']!='gpup-refine-review-source-v1' or value['base_revision']!=BASE:
        raise ValueError('refinement review source header differs')
    files=value['files']
    if not isinstance(files,list) or not files or any(set(f)!={'path','before_sha256','reviewed_sha256'} for f in files):
        raise ValueError('refinement review source fields differ')
    paths=[f['path'] for f in files]
    if len(set(paths))!=len(paths) or not set(paths)<=ALLOWED:
        raise ValueError('refinement review source scope differs')
    for f in files:
        before=subprocess.run(['git','show',BASE+':'+f['path']],cwd=ROOT,capture_output=True)
        if before.returncode:
            # Only these newly added review helpers may be absent at the base.
            if f['path'] not in {'tools/lp_refine_review.py','tests/integration/test_lp_refine_review.py'} or f['before_sha256'] is not None:
                raise ValueError('refinement review base source missing')
        elif hashlib.sha256(before.stdout).hexdigest()!=f['before_sha256']:
            raise ValueError('refinement review base hash differs')
        if sha(ROOT/f['path'])!=f['reviewed_sha256']:
            raise ValueError('refinement review current source differs: '+f['path'])
    return {f['path']:f for f in files}


@functools.lru_cache(maxsize=1)
def changes():
    if not RECEIPT.exists():return {}
    return validate_receipt(json.loads(RECEIPT.read_text()))


def pre_review_sha(path):
    actual=sha(ROOT/path)
    fix=changes().get(path)
    if fix is None:return actual
    # Check on each use too: a cached receipt cannot mask a subsequent mutation.
    if fix['reviewed_sha256']!=actual:raise ValueError('reviewed source changed during verification')
    return fix['before_sha256']


def verify_endpoints(binary,output):
    changes()
    report=json.loads((ROOT/'docs/benchmarks/data/refine/summary.json').read_text())
    directory=ROOT/'artifacts/gpup-refine-v2'
    paths=[]
    for row in report['rows']:
        if not row['verified'] or row['configuration']=='tuned-fp64':continue
        key=row['id'];trial=json.loads((directory/'study'/(key+'.trial.json')).read_text())
        endpoint=directory/'study'/(key+'.endpoint.json')
        ref=trial['artifacts']['endpoint'];model=trial['job']['instance']['model']
        if ref['path']!=endpoint.name or sha(endpoint)!=ref['sha256'] or sha(ROOT/model['path'])!=model['sha256']:
            raise ValueError('retained primary endpoint/model differs')
        paths.append((ROOT/model['path'],directory/'study'/(key+'.refine-request.json'),endpoint))
    protocol=json.loads((directory/'study/campaign.json').read_text())
    models={i['id']:i['model'] for manifest in protocol['manifests'] for i in json.loads((ROOT/manifest['path']).read_text())['instances']}
    pairs=json.loads((directory/'acceptance/project.json').read_text())['artifacts']
    for pair in pairs:
        key='accept-'+pair['model']+'-'+pair['configuration'];model=ROOT/models[pair['model']]['path'];request=directory/'acceptance'/(key+'.request.json')
        for suffix,field in [('.endpoint.json','endpoint_sha256'),('.endpoint.json.replay.json','replay_sha256')]:
            endpoint=directory/'acceptance'/(key+suffix)
            if sha(endpoint)!=pair[field] or sha(request)!=pair['request_sha256'] or sha(model)!=models[pair['model']]['sha256']:
                raise ValueError('retained acceptance artifact differs')
            paths.append((model,request,endpoint))
    rows=[]
    for model,request,endpoint in paths:
        result=subprocess.run([str(binary),'verify',str(model),str(request),str(endpoint)],capture_output=True,text=True,timeout=120)
        if result.returncode or result.stdout.strip()!='verified':raise ValueError('reviewed original-model verification failed: '+str(endpoint)+' '+result.stderr[:1000])
        rows.append(dict(path=str(endpoint.relative_to(ROOT)),sha256=sha(endpoint)))
    value=dict(identity='gpup-refine-reviewed-endpoints-v1',gpu_executed=False,endpoints=len(rows),
               verifier_sha256=sha(binary),review_source_sha256=sha(RECEIPT),files=rows)
    output.write_text(json.dumps(value,sort_keys=True,indent=2)+'\n')
    print('reviewed verifier accepts',len(rows),'unchanged endpoints; no GPU execution')


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--binary',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();verify_endpoints(args.binary.resolve(),args.output)
