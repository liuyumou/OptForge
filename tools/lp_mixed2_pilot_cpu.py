"""Exact original serial checker differential and two-way process admission."""
import argparse
import copy
import gzip
import json
import os
from pathlib import Path
import statistics
import subprocess
from lp_mixed2_pilot_common import ROOT, BASE, BINARY, VARIANTS, load, put, ref, require
from lp_delivery2_study import bits
ARCHIVE = ROOT/'docs/benchmarks/data/fp4-accel-result-v1-endpoints.json.gz'


def environment(variant, profile=False):
    require(variant in VARIANTS, 'unknown pilot configuration')
    env = {k:v for k,v in os.environ.items() if not k.startswith(('GPUP_DELIVERY','GPUP_CHECKER_','GPUP_MIXED2_'))}
    env['GPUP_MIXED2_PILOT_VARIANT'] = variant
    return env


def numerical_source():
    old = ROOT/'research/lp-delivery4/src/main.rs'
    new = ROOT/'research/lp-mixed2-pilot/src/main.rs'
    def body(path):
        text = path.read_text()
        return text[text.index('    fn lane('):text.index('fn main()')]
    require(body(old) == body(new), 'numerical state machine differs')
    original_model=(ROOT/'research/lp-fp4-accel/src/model.rs').read_text()
    require((ROOT/'research/lp-mixed2-pilot/src/model.rs').read_text().replace('use crate::identity::hex;\n','')==original_model.replace('use optimizer_experiment::sha256::hex;\n',''),'model arithmetic changed')
    return dict(parent=ref(old), candidate=ref(new), unchanged='lane, preparation, solve, command state machine')


def process_cases(model, endpoint):
    rows=[]
    for variant in VARIANTS:
        env=environment(variant)
        request=dict(endpoint=endpoint,tier='certified-1e-9')
        for status in ('completed','cancelled','limit','error','refused'):
            value=copy.deepcopy(request);value['endpoint']['transport']=status
            r=subprocess.run([str(BINARY),'check-service',str(model)],input=json.dumps(value).encode()+b'\n',capture_output=True,timeout=15,env=env)
            values=[json.loads(v) for v in r.stdout.splitlines()]
            require(r.returncode==0 and len(values)==2 and values[1]['accepted']==(status=='completed'),'terminal authority')
            rows.append(dict(variant=variant,case=status,passed=True))
        for key,value in [('model_sha256','wrong'),('primal',[]),('dual',[]),('transport','optimal')]:
            bad=copy.deepcopy(request);bad['endpoint'][key]=value
            r=subprocess.run([str(BINARY),'check-service',str(model)],input=json.dumps(bad).encode()+b'\n',capture_output=True,timeout=15,env=env)
            require(r.returncode!=0 and len(r.stdout.splitlines())==1,'malformed accepted')
            rows.append(dict(variant=variant,case=key,passed=True))
    for changes in ({'GPUP_MIXED2_PILOT_VARIANT':'auto'},{'GPUP_DELIVERY4_VARIANT':'candidate'},{'GPUP_CHECKER_ORIGINAL':'1'}):
        r=subprocess.run([str(BINARY),'check-service',str(model)],capture_output=True,timeout=15,env={**environment('control'),**changes})
        require(r.returncode!=0 and not r.stdout,'configuration fail-open')
        rows.append(dict(case='configuration',changes=changes,passed=True))
    return rows


def run(directory, count=3):
    out = Path(directory); out.mkdir(exist_ok=False, parents=True)
    archive = json.loads(gzip.decompress(ARCHIVE.read_bytes()))
    put(out/'manifest.json', dict(binary=ref(BINARY), archive=ref(ARCHIVE), count=count, variants=VARIANTS, source=numerical_source()))
    models=[]
    prior=ROOT/'research/lp-delivery4/target/release/lp-delivery4'
    for family,binding in archive['manifest']['models'].items():
        model=ROOT/binding['path'];require(ref(model)==binding,'original model changed')
        old_env={k:v for k,v in os.environ.items() if not k.startswith(('GPUP_DELIVERY','GPUP_CHECKER_','GPUP_MIXED2_'))}
        old_env.update(GPUP_DELIVERY4_VARIANT='candidate',GPUP_DELIVERY4_PROFILE='0',CUDA_VISIBLE_DEVICES='')
        for unscaled in (False,True):
            args=['inspect',str(model)]+(['unscaled'] if unscaled else [])
            expected=json.loads(subprocess.check_output([str(prior),*args],env=old_env,timeout=30))
            for variant in VARIANTS:
                observed=json.loads(subprocess.check_output([str(BINARY),*args],env={**environment(variant),'CUDA_VISIBLE_DEVICES':''},timeout=30))
                require(bits(expected)==bits(observed),'original model representation changed')
                models.append(dict(family=family,unscaled=unscaled,variant=variant,exact=True))
    put(out/'representations.json',dict(prior=ref(prior),rows=models))
    rows = []
    for index,(key,value) in enumerate(archive['endpoints'].items()):
        endpoint = out/(key+'.endpoint.json'); put(endpoint,value['endpoint'])
        model = ROOT/archive['manifest']['models'][value['family']]['path']
        require(ref(model) == archive['manifest']['models'][value['family']], 'changed original model')
        expected = {k:v for k,v in value['certificate'].items() if k != 'checker_binary_sha256'}
        for variant in (VARIANTS if index%2 == 0 else VARIANTS[::-1]):
            dest = out/(key+'-'+variant+'.json')
            subprocess.run([str(BINARY),'transport-profile',str(model),str(endpoint),value['tier'],str(count),str(dest)],check=True,capture_output=True,timeout=30,env={**environment(variant),'CUDA_VISIBLE_DEVICES':''})
            result = load(dest)
            for row in result['rows']:
                require(bits({k:v for k,v in row['certificate'].items() if k != 'checker_binary_sha256'}) == bits(expected), 'serial receipt mismatch')
                require(row['certificate']['checker_binary_sha256'] == ref(BINARY)['sha256'], 'checker executable binding')
            rows.append(dict(key=key,family=value['family'],tier=value['tier'],variant=variant,accepted=expected['accepted'],median_ns=statistics.median(r['ns'] for r in result['rows']),setup_ns=result['setup_ns'],profile=ref(dest)))
        if (index+1)%20 == 0: print(dict(endpoints=index+1),flush=True)
    value = next(v for v in archive['endpoints'].values() if v['family']=='coupled-equality' and v['certificate']['accepted'])
    cases = process_cases(ROOT/archive['manifest']['models'][value['family']]['path'],value['endpoint'])
    put(out/'result.json', dict(status='passed',endpoints=len(archive['endpoints']),fresh_assessments=len(rows)*count,representations=ref(out/'representations.json'),rows=rows,process_cases=cases))
    print(dict(endpoints=len(archive['endpoints']),fresh_assessments=len(rows)*count,process_cases=len(cases)),flush=True)

if __name__ == '__main__':
    p=argparse.ArgumentParser(); p.add_argument('directory'); p.add_argument('--count',type=int,default=3); a=p.parse_args(); run(a.directory,a.count)
