"""Portable all-cell evidence, scoped decisions, exact history and independent closure."""
import argparse
import gzip
import hashlib
import json
import math
import os
import re
from pathlib import Path
import statistics
import subprocess
from lp_delivery4_common import ROOT, BASE, BINARY, CPU_CAPS, GPU_CAPS, NS, LANES, TIERS, load, put, ref, require
from lp_delivery4_budget import accounting, admission_open
from lp_delivery4_stats import summarize as decisions_for
from lp_delivery4_study import validate_manifest
from lp_delivery2_study import matches
DATA=ROOT/'docs/benchmarks/data'


def history():
    allowed={'AGENTS.md','state/active-task.md','state/backlog.yaml','docs/plans/gpu-lp-precision-roadmap.md'}
    rows=[]
    for record in subprocess.check_output(['git','ls-tree','-rz','--full-tree','eac5d00'],cwd=ROOT).split(b'\0'):
        if not record:continue
        metadata,name=record.split(b'\t',1);mode,kind,blob=metadata.split();name=name.decode()
        if name in allowed:continue
        require(kind==b'blob','historical gitlink')
        raw=os.readlink(ROOT/name).encode() if mode==b'120000' else (ROOT/name).read_bytes()
        digest=hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()
        require(digest==blob.decode(),'historical source changed: '+name);rows.append(dict(path=name,git_blob=digest))
    for name in ('AGENTS.md','state/active-task.md'):
        old=subprocess.check_output(['git','show','eac5d00:'+name],cwd=ROOT).decode().split('\n\n',1)[1]
        require((ROOT/name).read_text().endswith(old),'older handoff modified')
    return dict(baseline='eac5d00',preserved=rows,allowed=sorted(allowed),older_handoffs_exact=True)


def compressed(path,value):
    with Path(path).open('xb') as stream:
        stream.write(gzip.compress(json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode(),compresslevel=6,mtime=0));stream.flush();os.fsync(stream.fileno())
    return ref(path)


def median_rows(rows):
    groups={}
    for row in rows:
        key=tuple(row[k] for k in ('lifecycle','family','lane','tier','role','variant'))
        groups.setdefault(key,[]).append(row)
    result=[]
    for key,group in groups.items():
        records=[r for row in group for r in row['records']]
        phases=sorted(set().union(*(r['costs_ns'] for r in records)))
        result.append(dict(zip(('lifecycle','family','lane','tier','role','variant'),key),
            samples=len(group),complete_ms=statistics.median(r['complete_ns'] for r in group)/1e6,
            first_solve_ms=statistics.median(r['records'][0]['complete_ns'] for r in group)/1e6,
            solve_ms=statistics.median(r['solve_ns'] for r in records)/1e6,
            setup_ms=statistics.median(r['setup_ns'] for r in records)/1e6,
            gpu_ms=statistics.median(r['gpu_us'] for r in records)/1000,
            physical=statistics.median(r['physical'] for r in records),
            costs_ms={phase:statistics.median(r['costs_ns'].get(phase,0) for r in records)/1e6 for phase in phases}))
    return result


def correlation(values):
    a,b=values[:-1],values[1:]
    ma,mb=statistics.mean(a),statistics.mean(b)
    covariance=sum((x-ma)*(y-mb) for x,y in zip(a,b))
    scale=math.sqrt(sum((x-ma)**2 for x in a)*sum((y-mb)**2 for y in b))
    return covariance/scale if scale else None


def lifecycle_profiles(rows, logs=None):
    observations=[]
    for row in rows:
        record=row['records'][0]
        log=ROOT/record['result']['path'];log=log.with_name(row['id']+'.stderr')
        events=[json.loads(line) for line in (log.read_text() if logs is None else logs[row['id']]).splitlines()]
        processes=[e['delivery4_process'] for e in events if 'delivery4_process' in e]
        parent=next(p for p in processes if p['role']=='once')
        child=next(p for p in processes if p['role']=='check-service')
        scopes=parent['costs']['scopes']
        def exact(path):return sum(s['inclusive_ns'] for s in scopes if s['path']==path)
        setup=exact(['session_setup']);response=exact(['response_construction']);emit=exact(['response_emit']);destruction=exact(['session_destruction'])
        # These root scopes do not overlap. Nested scopes explain their parents.
        require(setup+response+emit+destruction<=parent['main_ns'],'overlapping root accounting')
        outside_main=record['delivery']['process_exit_ns']-parent['main_ns']
        require(outside_main>=0,'process timer boundary')
        parts=dict(setup=setup,solve=record['solve_ns'],response_after_solve=response-record['solve_ns'],response_emit=emit,destruction=destruction,
            unscoped_main=parent['main_ns']-setup-response-emit-destruction,process_entry_exit=outside_main,
            durable_output=record['delivery']['durable_end_ns']-record['delivery']['process_exit_ns'])
        require(all(v>=0 for v in parts.values()) and sum(parts.values())==record['complete_ns'],'complete profile partition')
        observations.append(dict(family=row['family'],lane=row['lane'],tier=row['tier'],variant=row['variant'],block=row['block'],parts_ns=parts,
            destruction_scopes=[s for s in scopes if s['path'][0]=='session_destruction'],parent=parent,child=child))
    groups={}
    for row in observations:groups.setdefault(tuple(row[k] for k in ('family','lane','tier','variant')),[]).append(row)
    return dict(observations=observations,means=[dict(zip(('family','lane','tier','variant'),key),samples=len(group),parts_ms={k:statistics.mean(v['parts_ns'][k] for v in group)/1e6 for k in group[0]['parts_ns']},
        destruction_scopes_ms={str(scope['path']):statistics.mean(sum(s['inclusive_ns'] for s in row['destruction_scopes'] if s['path']==scope['path']) for row in group)/1e6 for scope in group[0]['destruction_scopes']},
        setup_scopes_ms={str(list(path)):statistics.mean(sum(s['inclusive_ns'] for s in row['parent']['costs']['scopes'] if tuple(s['path'])==path) for row in group)/1e6 for path in sorted({tuple(s['path']) for row in group for s in row['parent']['costs']['scopes'] if s['path'][0]=='session_setup'})}) for key,group in groups.items()])


def package():
    archives=[];cohorts={};profiles=[];environments={}
    for kind in ('profile','diagnostic','confirmation'):
        directory=BASE/(kind+'-v1');manifest=load(directory/'manifest.json');validate_manifest(manifest)
        result=load(directory/'result.json');require(result['status']=='complete','cohort incomplete')
        expected={'profile':64,'diagnostic':128,'confirmation':3072}[kind]
        require(len(result['rows'])==expected and len({r['id'] for r in result['rows']})==expected,'cohort coverage')
        for block in range(manifest['blocks']):
            block_dir=directory/f'block-{block:02d}';block_result=load(block_dir/'result.json');values={};logs={}
            for row in block_result['rows']:
                require(ref(ROOT/row['original_result']['path'])==row['original_result'],'changed original result')
                original=load(ROOT/row['original_result']['path'])
                for record in row['records']:
                    binding=record['result'];require(ref(ROOT/binding['path'])==binding,'new result changed')
                    value=load(ROOT/binding['path']);matches(value,original,manifest['binary']);values[binding['path']]=value
                    require(record['certified']==(row['family']!='infinite-bound-refusal'),'certificate coverage')
                    if kind=='profile':
                        for assessment in value['delivery_profile']['assessments']:
                            profiles.append(dict(family=row['family'],lane=row['lane'],tier=row['tier'],variant=row['variant'],lifecycle=row['lifecycle'],**assessment))
                log=block_dir/(row['id']+'.stderr');logs[row['id']]=log.read_text()
            name=f'delivery4-{kind}-block-{block:02d}-evidence-v1.json.gz'
            archives.append(compressed(DATA/name,dict(kind=kind,block=block,started=load(block_dir/'STARTED.json'),result=block_result,outputs=values,stderr=logs)))
        environments[kind]=[dict(start=load(directory/f'block-{b:02d}'/'STARTED.json')['environment'],end=load(directory/f'block-{b:02d}'/'result.json')['environment']) for b in range(manifest['blocks'])]
        cohorts[kind]=dict(manifest=manifest,result=result,manifest_binding=ref(directory/'manifest.json'),result_binding=ref(directory/'result.json'))
    prior_sanitizers=load(DATA/'fp4-accel-acceptance-v2.json')
    require(prior_sanitizers['admission']['image']==cohorts['confirmation']['manifest']['image'],'sanitizer image differs')
    require(set(prior_sanitizers['sanitizers'])=={'memcheck','racecheck','initcheck','synccheck'} and all(v['zero_errors'] and v['processes']==28 for v in prior_sanitizers['sanitizers'].values()),'sanitizer coverage')
    confirmation=cohorts['confirmation'];rows=confirmation['result']['rows'];families=list(confirmation['manifest']['models'])
    decisions=decisions_for(rows,families)
    medians=median_rows(rows);diagnostic_medians=median_rows(cohorts['diagnostic']['result']['rows'])
    lags=[]
    for lifecycle in ('cold',):
        for lane in LANES:
            for tier in TIERS:
                values=[]
                for block in range(32):
                    pair={r['role']:r for r in rows if r['block']==block and r['family']=='dense-generic-512' and r['lifecycle']==lifecycle and r['lane']==lane and r['tier']==tier}
                    values.append(pair['control']['complete_ns']/pair['candidate']['complete_ns'])
                lags.append(dict(lifecycle=lifecycle,lane=lane,tier=tier,lag_one_ratio_correlation=correlation(values),ratios=values))
    portable=compressed(DATA/'delivery4-cohorts-v1.json.gz',dict(cohorts=cohorts,
        model_bytes={f:(ROOT/b['path']).read_text() for f,b in confirmation['manifest']['models'].items()},
        selection=load(BASE/'selection-v1.json'),originals={path:load(ROOT/path) for path in sorted({c['original_result']['path'] for group in cohorts.values() for c in group['manifest']['cells']})},runner_source=(ROOT/'tools/lp_delivery4_cohort.py').read_text()))
    archive=BASE/'binaries'/ref(BINARY)['sha256'];archive.parent.mkdir(exist_ok=True)
    if archive.exists():require(archive.read_bytes()==BINARY.read_bytes(),'binary archive differs')
    else:
        with archive.open('xb') as stream:stream.write(BINARY.read_bytes())
    ideal=[]
    for lane in LANES:
        for tier in TIERS:
            values=[r['records'][0] for r in rows if r['role']=='candidate' and r['lane']==lane and r['tier']==tier and r['family'] in ('dense-generic-128','dense-generic-256','dense-generic-512')]
            ratios=[v['complete_ns']/(v['complete_ns']-v['gpu_us']*1000) for v in values]
            ideal.append(dict(lane=lane,tier=tier,geometric_mean=math.exp(statistics.mean(math.log(v) for v in ratios)),n=len(values),assumption='Eliminate every GPU event interval with unchanged other work and no added cost; descriptive bound, not a forecast.'))
    value=dict(status='complete',report_source=ref(Path(__file__)),replay_source=ref(ROOT/'tools/lp_delivery4_replay.py'),candidate_ideal_gpu_removal=ideal,confirmation_cells=len(rows),confirmation_solves=sum(len(r['records']) for r in rows),
        confirmation_certificates=sum(record['certified'] for row in rows for record in row['records']),
        diagnostic_cells=192,diagnostic_solves=sum(len(row['records']) for kind in ('profile','diagnostic') for row in cohorts[kind]['result']['rows']),
        reused_sanitizers=dict(receipt=ref(DATA/'fp4-accel-acceptance-v2.json'),image=prior_sanitizers['admission']['image'],coverage=prior_sanitizers['sanitizers'],new_runs=0),candidate='candidate',selection=load(BASE/'selection-v1.json'),decisions=decisions,medians=medians,diagnostic_medians=diagnostic_medians,
        lag_one_descriptive=lags,environment=environments,profile_parent_requests=profiles,profile_lifecycle=lifecycle_profiles(cohorts['profile']['result']['rows']),
        startup={v:load(BASE/('startup-'+v+'-v2')/'result.json') for v in ('control','candidate')},
        startup_raw={name:dict(manifest=load(BASE/name/'manifest.json'),measurements={p.name:load(p) for p in sorted((BASE/name).glob('*.json')) if p.name not in ('manifest.json','result.json')}) for name in ('startup-v1','startup-control-v2','startup-candidate-v2')},dependencies=load(BASE/'dependencies-v2.json'),environment_binding=load(BASE/'environment-v1.json'),development_binaries=load(BASE/'development-binaries-v1.json'),
        archives=archives,cohorts_archive=portable,cpu=load(BASE/'cpu-v1/result.json'),device=ref(BASE/'device-v1/result.json'),binary_archive=ref(archive),
        exact_all_original_audits_certificates_checkpoints_and_work=True,
        inference_limit='Constructed development families on one shared device. Intervals assume independent comparable block effects; fresh processes and randomization do not prove independence. Lag correlations are descriptive, not an adjusted confidence analysis.')
    put(DATA/'delivery4-result-v1.json',value)
    for d in decisions:print(dict(lifecycle=d['lifecycle'],lane=d['lane'],tier=d['tier'],decision=d['decision'],benefit=d['benefit'],guards=[g for g in d['guards'] if g['decision']!='supported']),flush=True)
    for row in medians:
        if row['family']=='dense-generic-512' and row['tier']=='certified-1e-9':print(row,flush=True)


def verify():
    result=load(DATA/'delivery4-result-v1.json');h=history()
    require(result['confirmation_cells']==3072 and result['confirmation_solves']==3072 and result['confirmation_certificates']==2816,'confirmation coverage')
    require(result['diagnostic_solves']==192,'diagnostic count')
    for binding in [*result['archives'],result['cohorts_archive'],result['binary_archive'],result['device'],result['report_source'],result['replay_source']]:
        require(ref(ROOT/binding['path'])==binding,'archive changed')
    for kind in ('profile','diagnostic','confirmation'):validate_manifest(load(BASE/(kind+'-v1')/'manifest.json'))
    settlements=[]
    for path in sorted((BASE/'resources').glob('*.settlement.json')):
        s=load(path);require(not s['overrun'],'resource overrun')
        if s['resource']:
            r=load(ROOT/s['resource']['path']);require(r['guardian_cleanup']['empty'] and r['result']['cleanup']['empty'],'cleanup incomplete')
        settlements.append(ref(path))
    def tasks(text):
        points=list(re.finditer(r'^  - id: (\S+)\s*$',text,re.M));result={}
        for i,point in enumerate(points):
            require(point.group(1) not in result,'duplicate backlog identity')
            result[point.group(1)]=text[point.start():points[i+1].start() if i+1<len(points) else len(text)]
        return result
    old=tasks(subprocess.check_output(['git','show','eac5d00:state/backlog.yaml'],cwd=ROOT).decode())
    current_text=(ROOT/'state/backlog.yaml').read_text();current=tasks(current_text)
    require(set(old)==set(current),'backlog task roster changed')
    for name in old:
        if name!='GPUP-DELIVERY4':require(old[name]==current[name],'other backlog task changed: '+name)
    require('    status: complete\n' in current['GPUP-DELIVERY4'],'current task not complete')
    require('next_ready_task: GPUP-MIXED2\n' in current_text,'next ready task differs')
    require('    status: ready\n' in current['GPUP-MIXED2'],'next task not ready')
    h['all_other_backlog_tasks_exact']=True
    from lp_delivery4_replay import replay
    portable=replay()
    native=load(BASE/'resources/native-gate-v1.settlement.json');require(native['status']=='passed','native gate incomplete')
    log=(BASE/'resources/native-gate-v1.resource.json.log').read_text()
    require('Ran 678 tests' in log and 'committed run records re-executed and verified: passed' in log,'software coverage')
    require(sum(int(n) for n in re.findall(r'test result: ok\. (\d+) passed;',log))==638,'Rust count')
    for command in (['python3','tools/validate_artifacts.py'],['python3','tools/build_docs.py'],['git','diff','--check']):
        subprocess.run(command,check=True,cwd=ROOT)
    put(DATA/'delivery4-history-v1.json',h)
    put(DATA/'delivery4-acceptance-v1.json',dict(status='passed',result=ref(DATA/'delivery4-result-v1.json'),history=ref(DATA/'delivery4-history-v1.json'),
        exact_historical_files=len(h['preserved']),workspace_rust_tests=637,total_rust_tests=638,isolated_rust_tests=27,python_tests=678,native=ref(BASE/'resources/native-gate-v1.settlement.json'),cpu=ref(BASE/'cpu-v1/result.json'),
        device=ref(BASE/'device-v1/result.json'),settlements=settlements,cleanup_empty=True,portable_replay=portable))
    print(dict(status='passed',historical_files=len(h['preserved'])),flush=True)


def close():
    admission_open();require(load(DATA/'delivery4-acceptance-v1.json')['status']=='passed','acceptance required')
    require(load(BASE/'resources/final-acceptance-v1.settlement.json')['status']=='passed','final supervisor incomplete')
    cpu,gpu=accounting();cpu['cleanup']+=128*NS
    require(all(cpu[k]<=v*NS for k,v in CPU_CAPS.items()) and all(gpu[k]<=v*NS for k,v in GPU_CAPS.items()),'allocation ceiling')
    settlements=[]
    for path in sorted((BASE/'resources').glob('*.settlement.json')):
        s=load(path);require(not s['overrun'],'resource overrun')
        if s['resource']:
            r=load(ROOT/s['resource']['path']);require(r['guardian_cleanup']['empty'] and r['result']['cleanup']['empty'],'cleanup incomplete')
        settlements.append(dict(binding=ref(path),settlement=s))
    receipts=[]
    for item in settlements:
        path=ROOT/item['binding']['path'];prefix=str(path).replace('.settlement.json','')
        receipts.append(dict(**item,reservation=load(prefix+'.reservation.json'),resource=load(prefix+'.resource.json'),log=Path(prefix+'.resource.json.log').read_text()))
    development={str(p.relative_to(BASE)):p.read_text() for p in sorted((BASE/'sources').rglob('*')) if p.is_file()}
    development.update({p.name:p.read_text() for p in sorted(BASE.iterdir()) if p.suffix in ('.py','.sh')})
    value=dict(status='closed',receipts=receipts,development_sources=development,failed_jobs=sum(s['settlement']['status']!='passed' for s in settlements),cpu_caps_seconds=CPU_CAPS,gpu_caps_seconds=GPU_CAPS,cpu_ns=cpu,gpu_ns=gpu,cpu_seconds=sum(cpu.values())/NS,gpu_seconds=sum(gpu.values())/NS,
        closing_administration_cpu_seconds=128,settlements=settlements,historical_transfers=0,cleanup_empty=True)
    put(DATA/'delivery4-accounting-v1.json',value);put(BASE/'CLOSED.json',dict(accounting=ref(DATA/'delivery4-accounting-v1.json')))
    print(dict(status='closed',cpu_seconds=value['cpu_seconds'],gpu_seconds=value['gpu_seconds']),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['package','verify','close']);a=p.parse_args();globals()[a.action]()
