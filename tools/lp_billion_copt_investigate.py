"""Bounded COPT investigation; original outcomes and numerical images remain immutable."""
import argparse
import json
import math
import resource
import subprocess
import sys
import time
from pathlib import Path
from lp_billion_common import BASE,ROOT,put,load,ref,resolve,require,CPU_CAPS,GPU_CAPS,NS
from lp_billion_budget import accounting,run
from lp_billion_prepare_continue import completed,job
from lp_billion_owned_process import execute as child

PREFIX='copt-diagnostic'
PYTHON=ROOT/'artifacts/gpup-copt-adapter-env/venv/bin/python'
ADAPTER=ROOT/'tools/lp_billion_copt_diagnostic.py'
AUDIT=ROOT/'tools/lp_billion_full_audit_v2.py'
PROTOCOL=ROOT/'docs/specifications/SPEC-0046-amendment-78.md'
FAMILIES=['irregular','coupled_blocks','ill_scaled']


def retrospective():
    rows=[]
    for i,family in [(2,'tall'),(4,'ill_scaled'),(5,'degenerate')]:
        identity=f'copt-nopresolve-1b-v1-{i}'
        log=BASE/identity/'response.copt.log'
        telemetry=BASE/'resources'/(identity+'.resource.json.capacity.jsonl')
        samples=[json.loads(v)['gpu'] for v in telemetry.read_text().splitlines() if '"gpu"' in v]
        receipt=BASE/'resources'/(identity+'.resource.json')
        rows.append(dict(id=identity,family=family,log=ref(log),telemetry=ref(telemetry),resource=ref(receipt),
                         observed_active_ns=load(receipt)['active_elapsed_ns'],
                         owned_gpu_peak_bytes=max(sum(s['processes'].values()) for s in samples),
                         maximum_gpu_utilization=max(s['utilization'] for s in samples),
                         gpu_pdlp_start_reported='Starting PDLP solver using GPU' in log.read_text(),
                         original_problem_reported='The original problem has:' in log.read_text(),
                         has_response=(BASE/identity/'response.json').exists()))
    put(BASE/'copt-diagnostic-retrospective-v1.json',dict(status='retained_evidence_reviewed',rows=rows,
        historical_capacity=ref(BASE/'copt-nopresolve-capacity-v1.json'),source=ref(__file__),protocol=ref(PROTOCOL),
        conclusion='The imported billion models enter COPT_SolveLp but never report PDLP startup; context-sized GPU use is consistent with an earlier startup bottleneck. Internal attribution requires new controlled diagnostics.'))
    print(rows,flush=True)


def regenerate():
    from lp_billion_generate import generate
    rows=[]
    for family in FAMILIES:
        previous=load(BASE/f'models-64m-{family}-v1/result.json')
        resolve(previous['generator'])
        name=f'{PREFIX}-regenerated-64m-{family}-v1'
        generate(name,family,previous['target'],previous['seed'])
        fresh=load(BASE/name/'result.json')
        require(fresh['model']['sha256']==previous['model']['sha256'],'byte-identical original model regeneration')
        require(load(resolve(fresh['model']))==load(resolve(previous['model'])),'identical original array manifests')
        rows.append(dict(original=previous['model'],regeneration=ref(BASE/name/'result.json')))
    put(BASE/'copt-diagnostic-regeneration-v1.json',dict(status='exact_original_inputs_restored',rows=rows,source=ref(__file__)))


def idle():
    from lp_billion_idle import Nvml
    from lp_billion_availability import stable,idle as is_idle
    out=BASE/'copt-diagnostic-idle-v1';out.mkdir(exist_ok=False)
    sensor=Nvml();samples=[];start=time.monotonic()
    try:
        for i in range(7):
            if i:
                while time.monotonic()<start+i*60:time.sleep(min(1,start+i*60-time.monotonic()))
            samples.append(sensor.sample())
            with (out/'samples.jsonl').open('a') as stream:stream.write(json.dumps(samples[-1])+'\n')
            ready=stable(samples,time.monotonic_ns())
            print(dict(sample=i,idle=is_idle(samples[-1]),ready=ready),flush=True)
            if ready:break
        put(out/'result.json',dict(status='observed_idle' if ready else 'idle_not_established',samples=samples,source=ref(__file__)))
    finally:sensor.close()


def admit():
    from lp_billion_copt_nopresolve_admit import fixtures,validate_nonoptimal
    from lp_general_oracle import settings
    require(completed('copt-diagnostic-contracts-v1'),'diagnostic contracts passed')
    out=BASE/'copt-diagnostic-admission-v1';out.mkdir(exist_ok=False)
    cases=fixtures();rows=[];deadline=time.monotonic()+270
    for variant in ['instrumented','scale-off','dualize-off','scale-dual-off']:
        selected=cases if variant=='instrumented' else [c for c in cases if c[0] in ['minimize','maximize','empty-matrix','ill_scaled']]
        for name,doc,expect,wall in selected:
            tag=variant+'-'+name
            original=out/(tag+'.json');put(original,doc)
            p=subprocess.run([str(BASE/'image-v1/executor'),'convert',str(original),str(BASE)],text=True,capture_output=True,timeout=10)
            require(p.returncode==0,'small original conversion')
            model=out/(tag+'.arrays.json');put(model,json.loads(p.stdout));response=out/(tag+'.response.json')
            remaining=deadline-time.monotonic();require(remaining>10,'whole admission cleanup allowance')
            process=child([str(PYTHON),'-B',str(ADAPTER),str(model),str(response),'--variant',variant,'--wall',str(wall),'--roundtrip'],out/(tag+'.stdout'),out/(tag+'.stderr'),min(wall+20,remaining-5))
            require(not process['timed_out'] and process['returncode']==0,'diagnostic small child returned '+tag)
            r=load(response);require(r['roundtrip_checked'] and r['model_sha256']==ref(model)['sha256'],'exact import/model identity')
            require(r['parameters']['FeasTol']==r['parameters']['DualTol']==1e-9 and r['parameters']['PDLPTol']==1e-12 and r['parameters']['MatrixTol']==0,'strict unchanged tolerances')
            resolve(r['phase_journal'])
            proof=None
            if r['has_solution']:
                q=dict(settings=settings('native'),endpoint=r['endpoint'])
                p=subprocess.run([str(BASE/'image-v1/executor'),'assess',str(model),str(BASE)],input=json.dumps(q)+'\n',text=True,capture_output=True,timeout=max(1,deadline-time.monotonic()))
                require(p.returncode==0,'independent strict small assessment')
                proof=json.loads(p.stdout);put(out/(tag+'.proof.json'),proof)
                require(proof['model_sha256']==r['model_sha256'],'original checker identity')
            if expect=='certified':require(proof is not None and proof['accepted'] and r['optimal'],'strict small optimum '+tag)
            if expect=='not_started':require(not r['solve_called'] and not r['has_solution'],'preparation consumes allowance')
            if expect in ['infeasible','unbounded']:
                if r['status']==10 and r['interrupts']:
                    require(not r['optimal'] and not (proof and proof['accepted']) and all(e['returncode']==0 for e in r['interrupts']),
                            'owned deadline interruption is unresolved, not a proof')
                else:validate_nonoptimal(expect,r,proof)
            rows.append(dict(variant=variant,case=name,response=ref(response),proof=ref(out/(tag+'.proof.json')) if proof else None,strict_accepted=bool(proof and proof['accepted']),process=process))
            print(dict(case=tag,status=r['status'],strict_accepted=rows[-1]['strict_accepted']),flush=True)
    from lp_billion_copt_diagnostic import installation
    put(out/'result.json',dict(status='passed',rows=rows,adapter=ref(ADAPTER),input_adapter=ref(ROOT/'tools/lp_billion_copt_run.py'),
        checker=ref(BASE/'image-v1/executor'),installation=installation(),source=ref(__file__),protocol=ref(PROTOCOL)))


def freeze():
    require(completed('copt-diagnostic-admission-v1'),'complete new adapter admission')
    require(load(BASE/'copt-diagnostic-regeneration-v1.json')['status']=='exact_original_inputs_restored','original inputs restored')
    gate=load(BASE/'copt-diagnostic-admission-v1/result.json')
    require(gate['adapter']==ref(ADAPTER) and gate['input_adapter']==ref(ROOT/'tools/lp_billion_copt_run.py'),'exact admitted sources')
    variants=['instrumented','scale-off','dualize-off','scale-dual-off'];cells=[]
    for i,family in enumerate(FAMILIES):
        model=load(BASE/f'models-64m-{family}-v1/result.json')
        for variant in variants[i:]+variants[:i]:
            cells.append(dict(id=f'{PREFIX}-64m-v1-{family}-{variant}',family=family,lane='copt-gpu-pdlp-diagnostic',variant=variant,
                model=model['model'],model_result=ref(BASE/f'models-64m-{family}-v1/result.json'),status='pending',seconds=150,audit_seconds=90,
                wall_seconds=90.,memory_mb=48000.,memory=dict(host_gib=32,device_gib=16),disk_gib=1))
    cpu,gpu=accounting()
    require(cpu['development']+4*sum(c['seconds'] for c in cells)*NS<=CPU_CAPS['development']*NS and gpu['development']+sum(c['seconds'] for c in cells)*NS<=GPU_CAPS['development']*NS,'whole diagnostic solve reservation')
    require(cpu['reporting']+(4*sum(c['audit_seconds'] for c in cells)+960)*NS<=CPU_CAPS['reporting']*NS,'whole diagnostic independent audits/report')
    put(BASE/'copt-diagnostic-64m-v1/freeze.json',dict(status='frozen_startup_diagnostic',cells=cells,adapter=ref(ADAPTER),source=ref(__file__),
        admission=ref(BASE/'copt-diagnostic-admission-v1/result.json'),checker=ref(BASE/'image-v1/executor'),audit=ref(AUDIT),
        child=ref(ROOT/'tools/lp_billion_owned_process.py'),protocol=ref(PROTOCOL)))


def worker(index):
    manifest=BASE/'copt-diagnostic-64m-v1/freeze.json';f=load(manifest);c=f['cells'][index]
    for k in ['source','adapter','audit','child']:resolve(f[k])
    out=BASE/c['id'];out.mkdir(exist_ok=False)
    previous=resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss
    p=child([str(PYTHON),'-B',str(ADAPTER),str(resolve(c['model'])),str(out/'response.json'),'--variant',c['variant'],'--wall',str(c['wall_seconds']),'--memory-mb',str(c['memory_mb'])],out/'stdout',out/'stderr',c['seconds']-30)
    p.update(child_rusage_hwm_bytes=resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss*1024,child_rusage_scope_is_single_solver=previous==0)
    put(out/'process.json',p)
    require(not p['timed_out'] and p['returncode']==0,'diagnostic interrupted: retain partial journal and no retry')
    started=time.monotonic_ns();r=load(out/'response.json')
    require(r['model_sha256']==c['model']['sha256'] and r['variant']==c['variant'],'original input and configuration')
    require(sum(r['profile']['exclusive_ns'].values())==r['profile']['total_ns']<=p['elapsed_ns'],'exact measured coverage')
    transport=time.monotonic_ns()-started
    put(out/'result.json',dict(response=ref(out/'response.json'),freeze=ref(manifest),process_ns=p['elapsed_ns'],response_transport_ns=transport,fresh_process_ns=p['elapsed_ns']+transport))


def execute():
    manifest=BASE/'copt-diagnostic-64m-v1/freeze.json';f=load(manifest)
    for i,c in enumerate(f['cells']):
        require(not (BASE/'resources'/(c['id']+'.reservation.json')).exists(),'never attempted diagnostic')
        s=run(c['id'],'development',c['seconds'],True,[str(PYTHON),'-B',__file__,'worker','--index',str(i)],32,16,1)
        print(dict(cell=c['id'],settlement=s),flush=True)
        require(s['cleanup_empty'] and not s['overrun'],'cleanup/overrun stops diagnostics')
        audit=c['id']+'-full-audit'
        s=run(audit,'reporting',c['audit_seconds'],False,[str(PYTHON),'-B',str(AUDIT),str(manifest),str(i)],32,0,1)
        print(dict(audit=audit,settlement=s),flush=True);require(s['status']=='passed','complete independent audit')
    put(manifest.parent/'completed.json',dict(status='all_diagnostic_cells_attempted_and_audited',freeze=ref(manifest)))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['retrospective','regenerate','idle','admit','freeze','worker','execute']);p.add_argument('--index',type=int)
    a=p.parse_args();worker(a.index) if a.action=='worker' else globals()[a.action]()
