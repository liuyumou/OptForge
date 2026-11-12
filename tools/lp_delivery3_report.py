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
from lp_delivery3_common import ROOT, BASE, BINARY, CPU_CAPS, GPU_CAPS, NS, LANES, TIERS, load, put, ref, require
from lp_delivery3_budget import accounting, admission_open
from lp_delivery3_stats import summarize as decisions_for
from lp_delivery3_study import validate_manifest
from lp_delivery2_study import matches
DATA=ROOT/'docs/benchmarks/data'


def history():
    allowed={'AGENTS.md','state/active-task.md','state/backlog.yaml','docs/plans/gpu-lp-precision-roadmap.md'}
    rows=[]
    for record in subprocess.check_output(['git','ls-tree','-rz','--full-tree','96ab3b6'],cwd=ROOT).split(b'\0'):
        if not record:continue
        metadata,name=record.split(b'\t',1);mode,kind,blob=metadata.split();name=name.decode()
        if name in allowed:continue
        require(kind==b'blob','historical gitlink')
        raw=os.readlink(ROOT/name).encode() if mode==b'120000' else (ROOT/name).read_bytes()
        digest=hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()
        require(digest==blob.decode(),'historical source changed: '+name);rows.append(dict(path=name,git_blob=digest))
    for name in ('AGENTS.md','state/active-task.md'):
        old=subprocess.check_output(['git','show','96ab3b6:'+name],cwd=ROOT).decode().split('\n\n',1)[1]
        require((ROOT/name).read_text().endswith(old),'older handoff modified')
    return dict(baseline='96ab3b6',preserved=rows,allowed=sorted(allowed),older_handoffs_exact=True)


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


def package():
    archives=[];cohorts={};profiles=[];environments={}
    for kind in ('profile','diagnostic','confirmation'):
        directory=BASE/(kind+'-v1');manifest=load(directory/'manifest.json');validate_manifest(manifest)
        result=load(directory/'result.json');require(result['status']=='complete','cohort incomplete')
        expected={'profile':256,'diagnostic':512,'confirmation':6144}[kind]
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
            name=f'delivery3-{kind}-block-{block:02d}-evidence-v1.json.gz'
            archives.append(compressed(DATA/name,dict(kind=kind,block=block,started=load(block_dir/'STARTED.json'),result=block_result,outputs=values,stderr=logs)))
        environments[kind]=[dict(start=load(directory/f'block-{b:02d}'/'STARTED.json')['environment'],end=load(directory/f'block-{b:02d}'/'result.json')['environment']) for b in range(manifest['blocks'])]
        cohorts[kind]=dict(manifest=manifest,result=result,manifest_binding=ref(directory/'manifest.json'),result_binding=ref(directory/'result.json'))
    confirmation=cohorts['confirmation'];rows=confirmation['result']['rows'];families=list(confirmation['manifest']['models'])
    decisions=decisions_for(rows,families)
    medians=median_rows(rows);diagnostic_medians=median_rows(cohorts['diagnostic']['result']['rows'])
    lags=[]
    for lifecycle in ('cold','prepared'):
        for lane in LANES:
            for tier in TIERS:
                values=[]
                for block in range(32):
                    pair={r['role']:r for r in rows if r['block']==block and r['family']=='dense-generic-512' and r['lifecycle']==lifecycle and r['lane']==lane and r['tier']==tier}
                    values.append(pair['control']['complete_ns']/pair['candidate']['complete_ns'])
                lags.append(dict(lifecycle=lifecycle,lane=lane,tier=tier,lag_one_ratio_correlation=correlation(values),ratios=values))
    portable=compressed(DATA/'delivery3-cohorts-v1.json.gz',dict(cohorts=cohorts,
        model_bytes={f:(ROOT/b['path']).read_text() for f,b in confirmation['manifest']['models'].items()},
        selection=load(BASE/'selection-v1.json'),runner_source=(BASE/'run-cohort.py').read_text()))
    archive=BASE/'binaries'/ref(BINARY)['sha256'];archive.parent.mkdir(exist_ok=True)
    with archive.open('xb') as stream:stream.write(BINARY.read_bytes())
    value=dict(status='complete',confirmation_cells=len(rows),confirmation_solves=sum(len(r['records']) for r in rows),
        confirmation_certificates=sum(record['certified'] for row in rows for record in row['records']),
        diagnostic_cells=768,diagnostic_solves=sum(len(row['records']) for kind in ('profile','diagnostic') for row in cohorts[kind]['result']['rows']),
        candidates=load(BASE/'selection-v1.json')['candidates'],selection=load(BASE/'selection-v1.json'),decisions=decisions,medians=medians,diagnostic_medians=diagnostic_medians,
        lag_one_descriptive=lags,environment=environments,profile_parent_requests=profiles,
        archives=archives,cohorts_archive=portable,cpu=load(BASE/'cpu-v1/result.json'),device=ref(BASE/'device-v1/result.json'),binary_archive=ref(archive),
        exact_all_original_audits_certificates_checkpoints_and_work=True,
        inference_limit='Constructed development families on one shared device. Intervals assume independent comparable block effects; fresh processes and randomization do not prove independence. Lag correlations are descriptive, not an adjusted confidence analysis.')
    put(DATA/'delivery3-result-v1.json',value)
    for d in decisions:print(dict(lifecycle=d['lifecycle'],lane=d['lane'],tier=d['tier'],decision=d['decision'],benefit=d['benefit'],guards=[g for g in d['guards'] if g['decision']!='supported']),flush=True)
    for row in medians:
        if row['family']=='dense-generic-512' and row['tier']=='certified-1e-9':print(row,flush=True)


def verify():
    result=load(DATA/'delivery3-result-v1.json');h=history()
    require(result['confirmation_cells']==6144 and result['confirmation_solves']==12288 and result['confirmation_certificates']==11264,'confirmation coverage')
    require(result['diagnostic_solves']==1536,'diagnostic count')
    for binding in [*result['archives'],result['cohorts_archive'],result['binary_archive'],result['device']]:
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
    old=tasks(subprocess.check_output(['git','show','96ab3b6:state/backlog.yaml'],cwd=ROOT).decode())
    current_text=(ROOT/'state/backlog.yaml').read_text();current=tasks(current_text)
    require(set(old)==set(current),'backlog task roster changed')
    for name in old:
        if name!='GPUP-DELIVERY3':require(old[name]==current[name],'other backlog task changed: '+name)
    require('    status: complete\n' in current['GPUP-DELIVERY3'],'current task not complete')
    require('next_ready_task: GPUP-MIXED2\n' in current_text,'next ready task differs')
    require('    status: ready\n' in current['GPUP-MIXED2'],'next task not ready')
    h['all_other_backlog_tasks_exact']=True
    for command in (['python3','tools/validate_artifacts.py'],['python3','tools/build_docs.py'],['git','diff','--check']):
        subprocess.run(command,check=True,cwd=ROOT)
    put(DATA/'delivery3-history-v1.json',h)
    put(DATA/'delivery3-acceptance-v1.json',dict(status='passed',result=ref(DATA/'delivery3-result-v1.json'),history=ref(DATA/'delivery3-history-v1.json'),
        exact_historical_files=len(h['preserved']),native=ref(BASE/'resources/native-gate-v1.settlement.json'),cpu=ref(BASE/'cpu-v1/result.json'),
        device=ref(BASE/'device-v1/result.json'),settlements=settlements,cleanup_empty=True))
    print(dict(status='passed',historical_files=len(h['preserved'])),flush=True)


def close():
    admission_open();require(load(DATA/'delivery3-acceptance-v1.json')['status']=='passed','acceptance required')
    require(load(BASE/'resources/final-acceptance-v1.settlement.json')['status']=='passed','final supervisor incomplete')
    cpu,gpu=accounting();cpu['cleanup']+=128*NS
    require(all(cpu[k]<=v*NS for k,v in CPU_CAPS.items()) and all(gpu[k]<=v*NS for k,v in GPU_CAPS.items()),'allocation ceiling')
    settlements=[]
    for path in sorted((BASE/'resources').glob('*.settlement.json')):
        s=load(path);require(not s['overrun'],'resource overrun')
        if s['resource']:
            r=load(ROOT/s['resource']['path']);require(r['guardian_cleanup']['empty'] and r['result']['cleanup']['empty'],'cleanup incomplete')
        settlements.append(dict(binding=ref(path),settlement=s))
    value=dict(status='closed',cpu_caps_seconds=CPU_CAPS,gpu_caps_seconds=GPU_CAPS,cpu_ns=cpu,gpu_ns=gpu,cpu_seconds=sum(cpu.values())/NS,gpu_seconds=sum(gpu.values())/NS,
        closing_administration_cpu_seconds=128,settlements=settlements,historical_transfers=0,cleanup_empty=True)
    put(DATA/'delivery3-accounting-v1.json',value);put(BASE/'CLOSED.json',dict(accounting=ref(DATA/'delivery3-accounting-v1.json')))
    print(dict(status='closed',cpu_seconds=value['cpu_seconds'],gpu_seconds=value['gpu_seconds']),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['package','verify','close']);a=p.parse_args();globals()[a.action]()
