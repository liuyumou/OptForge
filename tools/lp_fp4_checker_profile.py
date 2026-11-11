"""CPU-only retained-endpoint differential and interleaved component profiles."""
import argparse
import gzip
import json
import statistics
import subprocess
from pathlib import Path
from lp_fp4_checker_common import ROOT,BASE,put,ref,load,require

BINARY=ROOT/'research/lp-fp4-checker/target/release/lp-fp4-checker'
ARCHIVE=ROOT/'docs/benchmarks/data/fp4-accel-result-v1-endpoints.json.gz'


def run(version,count):
    out=BASE/version;out.mkdir(exist_ok=False)
    archive=json.loads(gzip.decompress(ARCHIVE.read_bytes()))
    put(out/'manifest.json',dict(binary=ref(BINARY),archive=ref(ARCHIVE),count=count,
        sources=[ref(p) for p in sorted((ROOT/'research/lp-fp4-checker/src').glob('*.rs'))]))
    rows=[]
    for index,(key,v) in enumerate(archive['endpoints'].items()):
        endpoint=out/(key+'.endpoint.json');put(endpoint,v['endpoint'])
        model=ROOT/archive['manifest']['models'][v['family']]['path']
        require(ref(model)==archive['manifest']['models'][v['family']],'changed original model')
        dest=out/(key+'.profile.json')
        subprocess.run([str(BINARY),'profile',str(model),str(endpoint),v['tier'],str(count),str(dest)],check=True,timeout=30,capture_output=True)
        result=load(dest);expected={k:x for k,x in v['certificate'].items() if k!='checker_binary_sha256'}
        require(result['certificate']==expected,'original serial receipt mismatch: '+key)
        for baseline in (True,False):
            samples=[r for r in result['rows'] if r['baseline']==baseline]
            rows.append(dict(key=key,family=v['family'],tier=v['tier'],baseline=baseline,accepted=expected['accepted'],
                median_ns=statistics.median(r['ns'] for r in samples),profile=ref(dest),
                phase_ns={phase:statistics.median(next(s['inclusive_ns'] for s in r['costs']['scopes'] if s['path']==[phase]) for r in samples)
                    for phase in ('candidate_feasibility_objective','dual_certification','gap_assessment') if all(any(s['path']==[phase] for s in r['costs']['scopes']) for r in samples)}))
        if (index+1)%20==0:print(dict(endpoints=index+1),flush=True)
    put(out/'result.json',dict(status='passed',endpoints=len(archive['endpoints']),rows=rows))
    for f in ('coupled-equality','dense-generic-128','dense-generic-256','dense-generic-512'):
        print([r for r in rows if r['family']==f and r['tier']=='certified-1e-9' and r['accepted']],flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('version');p.add_argument('--count',type=int,default=10);a=p.parse_args();run(a.version,a.count)
