"""All-cell exact delivery evidence, paired uncertainty, source preservation and closure."""
import argparse
import gzip
import hashlib
import json
import os
from pathlib import Path
import statistics
import subprocess
import numpy as np
from lp_delivery2_common import ROOT,BASE,CPU_CAPS,GPU_CAPS,NS,load,put,ref,require
from lp_delivery2_budget import accounting,admission_open
from lp_delivery2_study import matches,LANES,TIERS

DATA=ROOT/'docs/benchmarks/data'


def history():
    allowed={'AGENTS.md','state/active-task.md','state/backlog.yaml','docs/plans/gpu-lp-precision-roadmap.md'}
    records=subprocess.check_output(['git','ls-tree','-rz','--full-tree','8fe3a20'],cwd=ROOT).split(b'\0')
    exact=[]
    for record in records:
        if not record:continue
        meta,name=record.split(b'\t',1);mode,kind,blob=meta.split();name=name.decode()
        if name in allowed:continue
        require(kind==b'blob','historical gitlink');path=ROOT/name
        raw=os.readlink(path).encode() if mode==b'120000' else path.read_bytes()
        actual=hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()
        require(actual==blob.decode(),'historical file changed: '+name);exact.append(dict(path=name,git_blob=actual))
    for name in ('AGENTS.md','state/active-task.md'):
        before=subprocess.check_output(['git','show','8fe3a20:'+name],cwd=ROOT).decode().split('\n\n',1)[1]
        require((ROOT/name).read_text().endswith(before),'older handoff changed: '+name)
    return dict(baseline='8fe3a20',allowed=sorted(allowed),preserved=exact,older_handoffs_exact=True)


def summarize():
    directory=BASE/'study-v1';manifest=load(directory/'manifest.json');result=load(directory/'result.json')
    rows=result['rows'];require(result['status']=='complete' and len(rows)==len(manifest['cells'])==960,'incomplete cohort')
    require({r['id'] for r in rows}=={c['id'] for c in manifest['cells']},'duplicate or missing cells')
    evidence={}
    for row in rows:
        require(ref(ROOT/row['result']['path'])==row['result'],'changed new receipt')
        require(ref(ROOT/row['original_result']['path'])==row['original_result'],'changed original receipt')
        observed=load(ROOT/row['result']['path']);old=load(ROOT/row['original_result']['path'])
        matches(observed,old,manifest['binaries'][row['checker']]);evidence[row['id']]=observed
    families=list(manifest['models']);medians=[];decisions=[];rng=np.random.default_rng(33)
    for lifecycle in ('cold','prepared'):
        for tier in TIERS:
            for lane in LANES:
                ratios=[];bootstrap=[];regressions=[];losses=[];models=[]
                for family in families:
                    groups={mode:sorted([r for r in rows if all(r[k]==v for k,v in dict(lifecycle=lifecycle,tier=tier,lane=lane,family=family,checker=mode).items())],key=lambda r:r['repetition']) for mode in ('original','optimized')}
                    require(all(len(g)==5 for g in groups.values()),'missing paired repetition')
                    for mode,group in groups.items():
                        medians.append(dict(lifecycle=lifecycle,tier=tier,lane=lane,family=family,mode=mode,
                            certified=sum(r['certified'] for r in group),complete_ms=statistics.median(r['complete_ns'] for r in group)/1e6,
                            setup_ms=statistics.median(r['setup_ns'] for r in group)/1e6,solve_ms=statistics.median(r['solve_ns'] for r in group)/1e6,
                            checker_ms=statistics.median(r['costs_ns'].get('checker',0) for r in group)/1e6,
                            physical=statistics.median(r['physical'] for r in group)))
                    if sum(r['certified'] for r in groups['optimized'])<sum(r['certified'] for r in groups['original']):losses.append(family)
                    if not all(r['certified'] for r in groups['original']+groups['optimized']):continue
                    a=np.array([r['complete_ns'] for r in groups['original']],float);b=np.array([r['complete_ns'] for r in groups['optimized']],float)
                    ratio=float(np.median(a)/np.median(b));ratios.append(ratio)
                    if ratio<1:regressions.append(family)
                    indices=rng.integers(0,5,(2000,5));bootstrap.append(np.median(a[indices],axis=1)/np.median(b[indices],axis=1))
                    models.append(dict(family=family,ratio=ratio,paired_range=[float(np.min(a/b)),float(np.max(a/b))]))
                gm=float(np.exp(np.mean(np.log(ratios))));interval=list(map(float,np.quantile(np.exp(np.mean(np.log(bootstrap),axis=0)),[.025,.975])))
                decisions.append(dict(lifecycle=lifecycle,tier=tier,lane=lane,geomean=gm,bootstrap95=interval,models=models,
                    regressions=regressions,coverage_losses=losses,retention_pass=lifecycle=='cold' and gm>=1.1 and not regressions and not losses))
    archive=DATA/'delivery2-evidence-v1.json.gz'
    with archive.open('xb') as stream:
        stream.write(gzip.compress(json.dumps(dict(manifest=manifest,results=evidence),sort_keys=True,separators=(',',':'),allow_nan=False).encode(),mtime=0));stream.flush();os.fsync(stream.fileno())
    data=dict(status='complete',cells=len(rows),certified=sum(r['certified'] for r in rows),manifest=manifest,manifest_binding=ref(directory/'manifest.json'),
        rows=rows,medians=medians,decisions=decisions,setups=result['setups'],teardowns=result['teardowns'],exact_all_numerical_evidence=True,
        evidence_archive=ref(archive),cpu=load(BASE/'cpu-v1/result.json'),device=load(BASE/'lifecycle-v1/result.json'))
    put(DATA/'delivery2-result-v1.json',data)
    for d in decisions:print({k:v for k,v in d.items() if k!='models'},flush=True)
    for row in medians:
        if row['family']=='dense-generic-512' and row['tier']=='certified-1e-9':print(row,flush=True)


def verify():
    data=load(DATA/'delivery2-result-v1.json');manifest=data['manifest'];h=history()
    for binding in [manifest['parent'],manifest['cpu_admission'],manifest['image'],*manifest['models'].values(),*manifest['binaries'].values(),*manifest['sources']]:
        require(ref(ROOT/binding['path'])==binding,'changed frozen source/input')
    require(data['cells']==960 and data['certified']==880,'coverage differs')
    cleanup=[]
    for path in sorted((BASE/'resources').glob('*.settlement.json')):
        s=load(path);require(not s['overrun'],'resource overrun')
        if s['resource']:
            r=load(ROOT/s['resource']['path']);require(r['guardian_cleanup']['empty'] and r['result']['cleanup']['empty'],'cleanup not empty')
            cleanup.append(dict(settlement=ref(path),empty=True))
    binary=ROOT/manifest['binaries']['optimized']['path'];archive=BASE/'binaries'/manifest['binaries']['optimized']['sha256'];archive.parent.mkdir(exist_ok=True)
    if archive.exists():require(archive.read_bytes()==binary.read_bytes(),'archive changed')
    else:archive.write_bytes(binary.read_bytes())
    subprocess.run(['python3','tools/validate_artifacts.py'],check=True,cwd=ROOT)
    subprocess.run(['python3','tools/build_docs.py'],check=True,cwd=ROOT)
    subprocess.run(['git','diff','--check'],check=True,cwd=ROOT)
    put(DATA/'delivery2-history-v1.json',h)
    put(DATA/'delivery2-acceptance-v1.json',dict(status='passed',result=ref(DATA/'delivery2-result-v1.json'),history=ref(DATA/'delivery2-history-v1.json'),
        exact_historical_files=len(h['preserved']),binary_archive=ref(archive),native=ref(BASE/'resources/native-gate-v2.settlement.json'),
        cpu=ref(BASE/'cpu-v1/result.json'),device=ref(BASE/'lifecycle-v1/result.json'),smoke=ref(BASE/'smoke-v1/result.json'),cleanup=cleanup))
    print(dict(status='passed',historical_files=len(h['preserved'])),flush=True)


def close():
    admission_open();require(load(DATA/'delivery2-acceptance-v1.json')['status']=='passed','acceptance required')
    require(load(BASE/'resources/delivery-v1.settlement.json')['status']=='passed','delivery supervisor')
    cpu,gpu=accounting();cpu['cleanup']+=128*NS
    require(all(cpu[k]<=v*NS for k,v in CPU_CAPS.items()) and all(gpu[k]<=v*NS for k,v in GPU_CAPS.items()),'ceiling')
    settlements=[]
    for path in sorted((BASE/'resources').glob('*.settlement.json')):
        s=load(path);require(not s['overrun'],'overrun')
        if s['resource']:
            r=load(ROOT/s['resource']['path']);require(r['guardian_cleanup']['empty'] and r['result']['cleanup']['empty'],'cleanup')
        settlements.append(dict(binding=ref(path),settlement=s))
    value=dict(status='closed',cpu_caps_seconds=CPU_CAPS,gpu_caps_seconds=GPU_CAPS,cpu_ns=cpu,gpu_ns=gpu,cpu_seconds=sum(cpu.values())/NS,gpu_seconds=sum(gpu.values())/NS,
        closing_administration_cpu_seconds=128,all_settlements=settlements,historical_transfers=0,cleanup_empty=True)
    put(DATA/'delivery2-accounting-v1.json',value);put(BASE/'CLOSED.json',dict(accounting=ref(DATA/'delivery2-accounting-v1.json')))
    print(dict(status='closed',cpu_seconds=value['cpu_seconds'],gpu_seconds=value['gpu_seconds']),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['summarize','verify','close']);a=p.parse_args();globals()[a.action]()
