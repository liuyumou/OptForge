"""Additive publication, history validation and final allocation closure."""
import argparse
import gzip
import hashlib
import json
import os
from pathlib import Path
import statistics
import subprocess
import numpy as np
from lp_fp4_accel_common import ROOT,BASE,CPU_CAPS,GPU_CAPS,NS,put,ref,load,require
from lp_fp4_accel_budget import accounting,admission_open

DATA=ROOT/'docs/benchmarks/data'


def summarize():
    first=load(DATA/'fp4-accel-result-v1.json');cold=load(BASE/'cold-eof-v1/result.json');manifest=load(BASE/'cold-eof-v1/manifest.json')
    require(cold['status']=='complete' and len(cold['rows'])==360,'cold coverage')
    medians=[];decisions=[];rng=np.random.default_rng(310064)
    families=list(manifest['models']);lanes=manifest['lanes']
    for tier in ('certified-1e-7','certified-1e-9'):
        grouped={}
        for family in families:
            for lane in lanes:
                rows=sorted([r for r in cold['rows'] if r['family']==family and r['lane']==lane and r['tier']==tier],key=lambda x:x['repetition'])
                require(len(rows)==5,'cold repetition coverage');grouped[family,lane]=rows
                medians.append(dict(family=family,lane=lane,tier=tier,complete_ms=statistics.median(r['complete_ns'] for r in rows)/1e6,certified=sum(r['certified'] for r in rows)))
        bounded=[f for f in families if all(r['certified'] for r in grouped[f,'nativefast'])]
        for lane in lanes:
            ratios=[];boot=[];regressions=[]
            for family in bounded:
                a=np.array([r['complete_ns'] for r in grouped[family,'nativefast']],float);b=np.array([r['complete_ns'] for r in grouped[family,lane]],float)
                ratio=float(np.median(a)/np.median(b));ratios.append(ratio)
                if ratio<1:regressions.append(family)
                idx=rng.integers(0,5,(2000,5));boot.append(np.median(a[idx],axis=1)/np.median(b[idx],axis=1))
            gm=float(np.exp(np.log(ratios).mean()));ci=list(map(float,np.quantile(np.exp(np.log(boot).mean(axis=0)),[.025,.975])))
            losses=[f for f in families if sum(r['certified'] for r in grouped[f,lane])<sum(r['certified'] for r in grouped[f,'nativefast'])]
            decisions.append(dict(tier=tier,lane=lane,reference='nativefast',geomean=gm,bootstrap95=ci,model_regressions=regressions,coverage_losses=losses,retention_pass=gm>=1.10 and not regressions and not losses))
    archive=json.loads(gzip.decompress((ROOT/first['endpoint_archive']['path']).read_bytes()));links=[]
    for cohort,rows in [('formal-v1',first['rows']),('cold-eof-v1',cold['rows'])]:
        for row in rows:
            require(ref(ROOT/row['result']['path'])==row['result'],'changed raw cell')
            result=load(ROOT/row['result']['path']);keys=[]
            for e,c in [(result['endpoint'],result['certificate'])]+[(a['endpoint'],a['certificate']) for a in result['audits']]:
                key=hashlib.sha256(json.dumps([e,row['tier']],sort_keys=True,separators=(',',':')).encode()).hexdigest()
                require(archive['endpoints'][key]['endpoint']==e and archive['endpoints'][key]['certificate']==c,'new/unverified endpoint')
                keys.append(key)
            links.append(dict(cohort=cohort,id=row['id'],final_endpoint=keys[0],audit_endpoints=keys[1:],raw=row['result']))
    put(DATA/'fp4-accel-evidence-v1.json',dict(endpoint_archive=first['endpoint_archive'],serial_replays=first['unique_serial_replays'],cells=links))
    put(DATA/'fp4-accel-cold-eof-v1.json',dict(status='complete',manifest=manifest,manifest_binding=ref(BASE/'cold-eof-v1/manifest.json'),
        cells=len(cold['rows']),certified=sum(r['certified'] for r in cold['rows']),rows=cold['rows'],medians=medians,decisions=decisions,all_endpoint_receipts_and_work_identical=True))
    print(dict(cold_cells=360,cold_certified=sum(r['certified'] for r in cold['rows']),decisions=decisions),flush=True)


def validate_history():
    baseline='ccfbb56';allowed={'AGENTS.md','state/active-task.md','state/backlog.yaml','docs/plans/gpu-lp-precision-roadmap.md'}
    preserved=[]
    records=subprocess.check_output(['git','ls-tree','-rz','--full-tree',baseline],cwd=ROOT).split(b'\0')
    for record in records:
        if not record:continue
        meta,name=record.split(b'\t',1);mode,kind,blob=meta.split();name=name.decode()
        if name in allowed:continue
        require(kind==b'blob','unexpected gitlink');path=ROOT/name
        data=os.readlink(path).encode() if mode==b'120000' else path.read_bytes()
        actual=hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()
        require(actual==blob.decode(),'changed historical bytes: '+name)
        preserved.append(dict(path=name,git_blob=actual))
    put(DATA/'fp4-accel-history-v1.json',dict(baseline=baseline,allowed_handoff_updates=sorted(allowed),preserved=preserved))
    for manifest in [load(BASE/'study-v1/manifest.json'),load(BASE/'cold-eof-v1/manifest.json')]:
        refs=[manifest['image'],manifest['binary']]+manifest.get('sources',[])
        if 'source' in manifest:refs.append(manifest['source'])
        for r in refs:require(ref(ROOT/r['path'])==r,'changed scientific source')
    return len(preserved)


def check():
    count=validate_history();summaries={}
    for tool in ('memcheck','racecheck','initcheck','synccheck'):
        logs=list((BASE/(tool+'-final-v1')).glob('*.sanitizer'));require(len(logs)==28,'sanitizer coverage')
        for p in logs:require(('RACECHECK SUMMARY: 0 hazards' if tool=='racecheck' else 'ERROR SUMMARY: 0 errors') in p.read_text(),'sanitizer failure')
        summaries[tool]=dict(processes=len(logs),zero_errors=True)
    for p in (BASE/'resources').glob('*.settlement.json'):
        s=load(p);require(not s['overrun'],'resource overrun')
        if s['resource']:
            r=load(ROOT/s['resource']['path'])
            require(r['guardian_cleanup']['empty'] and r['result']['cleanup']['empty'],'incomplete cleanup')
    subprocess.run(['python3','tools/validate_artifacts.py'],cwd=ROOT,check=True)
    subprocess.run(['python3','tools/build_docs.py'],cwd=ROOT,check=True)
    subprocess.run(['git','diff','--check'],cwd=ROOT,check=True)
    put(DATA/'fp4-accel-acceptance-v1.json',dict(status='passed',admission=load(BASE/'admission.json'),
        frozen_results=ref(DATA/'fp4-accel-result-v1.json'),cold_results=ref(DATA/'fp4-accel-cold-eof-v1.json'),
        serial_evidence=ref(DATA/'fp4-accel-evidence-v1.json'),history=ref(DATA/'fp4-accel-history-v1.json'),sanitizers=summaries,historical_files_exact=count))
    print(dict(status='passed',historical_files_exact=count,sanitizers=summaries),flush=True)


def close():
    admission_open();cpu,gpu=accounting();cpu['cleanup']+=64*NS
    require(all(cpu[k]<=v*NS for k,v in CPU_CAPS.items()) and all(gpu[k]<=v*NS for k,v in GPU_CAPS.items()),'allocation exceeded')
    attempts=[]
    for p in sorted((BASE/'resources').glob('*.settlement.json')):
        r=load(p);attempts.append(dict(id=p.name.removesuffix('.settlement.json'),settlement=ref(p),**r))
    receipt=dict(status='closed',cpu_ns=sum(cpu.values()),gpu_ns=sum(gpu.values()),cpu_by_phase_ns=cpu,gpu_by_phase_ns=gpu,
        cpu_caps_seconds=CPU_CAPS,gpu_caps_seconds=GPU_CAPS,preparation_cpu_seconds=512,
        closing_administration_cpu_seconds=64,administration_method='explicit conservative charge for final metadata/docs/local commit after supervisor settlement; not a fabricated execution receipt',
        attempts=attempts,acceptance=ref(DATA/'fp4-accel-acceptance-v1.json'),historical_transfer=False)
    put(DATA/'fp4-accel-accounting-v1.json',receipt);put(BASE/'CLOSED.json',dict(accounting=ref(DATA/'fp4-accel-accounting-v1.json')))
    print(dict(cpu_seconds=receipt['cpu_ns']/NS,gpu_seconds=receipt['gpu_ns']/NS,status='closed'),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['summarize','check','close']);a=p.parse_args()
    globals()[{'summarize':'summarize','check':'check','close':'close'}[a.action]]()
