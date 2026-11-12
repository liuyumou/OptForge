"""Exact original serial checker differential and four-way process admission."""
import argparse
import copy
import gzip
import json
import os
from pathlib import Path
import statistics
import subprocess
from lp_delivery3_common import ROOT, BASE, BINARY, VARIANTS, load, put, ref, require
from lp_delivery2_study import bits
ARCHIVE = ROOT/'docs/benchmarks/data/fp4-accel-result-v1-endpoints.json.gz'


def environment(variant, profile=False):
    require(variant in VARIANTS, 'unknown delivery configuration')
    env = dict(os.environ)
    for name in ('GPUP_DELIVERY2_CONTROL', 'GPUP_CHECKER_ORIGINAL'):
        env.pop(name, None)
    env['GPUP_DELIVERY3_VARIANT'] = variant
    env['GPUP_DELIVERY3_PROFILE'] = '1' if profile else '0'
    return env


def numerical_source():
    old = ROOT/'research/lp-delivery2/src/main.rs'
    new = ROOT/'research/lp-delivery3/src/main.rs'
    def body(path):
        text = path.read_text()
        return text[text.index('    fn lane('):text.index('fn main()')]
    require(body(old) == body(new), 'numerical state machine differs')
    return dict(parent=ref(old), candidate=ref(new), unchanged='lane, preparation, solve, command state machine')


def process_cases(model, endpoint):
    rows = []
    request = dict(endpoint=endpoint, tier='certified-1e-9')
    for variant in VARIANTS:
        for profile in (False, True):
            env = {**environment(variant, profile), 'CUDA_VISIBLE_DEVICES':''}
            requests = []
            for status in ('completed', 'cancelled', 'limit', 'error', 'refused'):
                value = copy.deepcopy(request); value['endpoint']['transport'] = status; requests.append(value)
            result = subprocess.run([str(BINARY), 'check-service', str(model)], input=b''.join(json.dumps(v).encode()+b'\n' for v in requests), capture_output=True, timeout=15, env=env)
            values = [json.loads(line) for line in result.stdout.splitlines()]
            require(result.returncode == 0 and len(values) == 6, 'fresh checker lifecycle')
            require(values[1]['accepted'] and all(not r['accepted'] for r in values[2:]), 'terminal status authority')
            require(bool(result.stderr) == profile, 'diagnostic instrumentation mode')
            if profile:
                events = [json.loads(line) for line in result.stderr.splitlines()]
                require(len(events) == 6 and 'delivery3_checker_setup' in events[0], 'diagnostic schema')
                for event in events[1:]:
                    p = event['delivery3_checker_assessment']
                    require(0 <= p['decode_ns'] <= p['assessed_ns'] <= p['sent_ns'], 'child timing order')
            rows.append(dict(variant=variant, profile=profile, case='fresh-status-EOF', passed=True))
            malformed = {}
            for key, value in [('model_sha256','wrong'), ('primal',[]), ('dual',[]), ('transport','optimal')]:
                bad = copy.deepcopy(request); bad['endpoint'][key] = value; malformed[key] = json.dumps(bad).encode()+b'\n'
            bad = copy.deepcopy(request); bad['tier'] = 'certified-1e-6'; malformed['tier'] = json.dumps(bad).encode()+b'\n'
            malformed.update(duplicate=b'{"tier":"a","tier":"b","endpoint":null}\n', truncated=json.dumps(request).encode(), oversize=b' '*(8<<20)+b'\n')
            for case, payload in malformed.items():
                r = subprocess.run([str(BINARY),'check-service',str(model)],input=payload,capture_output=True,timeout=15,env=env)
                require(r.returncode != 0 and len(r.stdout.splitlines()) == 1, 'bad request accepted: '+case)
                rows.append(dict(variant=variant,profile=profile,case=case,passed=True))
    for changes in ({'GPUP_DELIVERY3_VARIANT':'auto'}, {'GPUP_DELIVERY3_PROFILE':'yes'}, {'GPUP_DELIVERY2_CONTROL':'1'}, {'GPUP_CHECKER_ORIGINAL':'1'}):
        env = {**environment('control'), **changes, 'CUDA_VISIBLE_DEVICES':''}
        r = subprocess.run([str(BINARY),'check-service',str(model)],capture_output=True,timeout=10,env=env)
        require(r.returncode != 0 and not r.stdout, 'configuration fail-open')
        rows.append(dict(case='configuration-refusal',changes=changes,passed=True))
    r = subprocess.run([str(BINARY),'check-service',str(model)+'.missing'],capture_output=True,timeout=10,env={**environment('combined'),'CUDA_VISIBLE_DEVICES':''})
    require(r.returncode != 0 and not r.stdout,'missing model became ready')
    rows.append(dict(case='missing-model',passed=True))
    return rows


def run(directory, count=3):
    out = Path(directory); out.mkdir(exist_ok=False, parents=True)
    archive = json.loads(gzip.decompress(ARCHIVE.read_bytes()))
    put(out/'manifest.json', dict(binary=ref(BINARY), archive=ref(ARCHIVE), count=count, variants=VARIANTS, source=numerical_source()))
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
    put(out/'result.json', dict(status='passed',endpoints=len(archive['endpoints']),fresh_assessments=len(rows)*count,rows=rows,process_cases=cases))
    print(dict(endpoints=len(archive['endpoints']),fresh_assessments=len(rows)*count,process_cases=len(cases)),flush=True)

if __name__ == '__main__':
    p=argparse.ArgumentParser(); p.add_argument('directory'); p.add_argument('--count',type=int,default=3); a=p.parse_args(); run(a.directory,a.count)
