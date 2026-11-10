"""One inherited eight-model CPU matrix for the new candidate, no CUDA execution."""
import concurrent.futures
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

import lp_cpu_admission as supervisor
import lp_tensor_expanded_authority as a
import lp_tensor_expanded_recovery as recovery
import lp_tensor_expanded_cpu_build as scalar
import lp_tensor_expanded_window_accept as window
from lp_tensor_cost_common import instances

BASE=a.BASE/'cpu-model-admission-v1'
JOURNAL=BASE/'cpu-journal-v9.json'


def initialize():
    recovery.preservation()
    j=a.read(window.JOURNAL)
    a.require(not j['failed'] and j['active'] is None,'window gate not passed')
    a.require(a.read(a.DATA/'rust-window-acceptance-v1.json')['status']=='passed','window receipt not passed')
    for name in ['rust-window-acceptance-v1.json','rust-scalar-acceptance-v1.json']:
        for source in a.read(a.DATA/name)['sources']:a.checked(source)
    a.require(j['stages']['native']==dict(cap_cpu_ns=4000*a.NS,charged_cpu_ns=0),'native funds differ')
    j['stages']['native']['cap_cpu_ns']=0
    j['stages']['cpu_models']=dict(cap_cpu_ns=4000*a.NS,charged_cpu_ns=0)
    sources=sorted([*scalar.CRATE.glob('src/**/*.rs'),*scalar.CRATE.glob('tests/**/*.rs'),
                    scalar.CRATE/'Cargo.toml',scalar.CRATE/'Cargo.lock'])
    manifest=[a.ref(p) for p in sources]
    source_hash=hashlib.sha256(json.dumps(manifest,sort_keys=True).encode()).hexdigest()
    a.put(BASE/'source-manifest.json',dict(sources=manifest,source_tree_sha256=source_hash))
    for p in sources:
        target=BASE/'source'/p.relative_to(scalar.CRATE);target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(p.read_bytes())
    auth=a.DATA/'cpu-model-authorization-v1.json'
    a.put(auth,dict(status='accepted',authorization='User-authorized conditional continuation with unused-budget reallocation.',
        transfer=dict(source='native',target='cpu_models',cpu_seconds=4000),work_wall_seconds=998,
        prior_journal=a.ref(window.JOURNAL),source_manifest=a.ref(BASE/'source-manifest.json'),
        prior_checks_reused=['authority','prototype','corrected_proof','CUDA_primitives','Rust_scalar','Rust_window'],
        new_tests='window_recovery only',matrix_cells=48,
        reuse_unchanged_tuned_control=True,gpu_seconds=0,full_candidate_inventory=False))
    j.update(identity='gpup-tensor-expanded-cpu-model-journal-v9',continuation_authorization=a.ref(auth),
        prior_stage_journal=a.ref(window.JOURNAL))
    a.put(JOURNAL,j)
    path=a.ROOT/'state/active-task.md';first,rest=path.read_text().split('\n',1)
    path.write_text(first+'\n\n'+'''## GPUP-8 new CPU recovery checks and model admission (2026-10-24)

Three focused Rust window/preparation checks pass. Reuse their exact sources and
receipts. Run only five additional recovery/controller tests, then the inherited
48-cell CPU model matrix: new candidate and affected matched controls, with the
unchanged tuned control reused through its original bindings. Verify each new
endpoint once. Transfer the remaining 4000 native CPU seconds to this bounded
CPU-model stage (998 work-wall seconds). Keep all original-unit budgets, useful
400-update requirements, coverage and later GPU gates unchanged. This remains a
partial CPU admission; full Tensor/CUDA solver inventory is still pending.
Active journal: artifacts/gpup-tensor-expanded-v1/cpu-model-admission-v1/cpu-journal-v9.json.
No passed test/profile rerun and no GPU execution is authorized by this CPU stage.

'''+rest.lstrip('\n'))


def command(label,args,env,timeout):
    start=time.monotonic_ns()
    p=subprocess.run(args,capture_output=True,text=True,env=env,timeout=timeout)
    (BASE/(label+'.stdout')).write_text(p.stdout);(BASE/(label+'.stderr')).write_text(p.stderr)
    a.put(BASE/(label+'.json'),dict(command=args,returncode=p.returncode,elapsed_ns=time.monotonic_ns()-start,
        stdout=a.ref(BASE/(label+'.stdout')),stderr=a.ref(BASE/(label+'.stderr'))))
    print(p.stdout.strip(),flush=True)
    if p.returncode:print(p.stderr.strip(),flush=True)
    a.require(p.returncode==0,label+' failed')


def child():
    manifest=a.read(BASE/'source-manifest.json')
    for item in manifest['sources']:a.checked(item)
    env=os.environ.copy();env.update(RUSTUP_HOME='/tmp/ai-optimizer-rustup',CARGO_HOME='/tmp/ai-optimizer-cargo',
        CARGO_TARGET_DIR=str(window.BASE/'target'),CUDA_VISIBLE_DEVICES='')
    env['PATH']='/tmp/ai-optimizer-cargo/bin:'+env.get('PATH','')
    cargo=['/tmp/ai-optimizer-cargo/bin/cargo']
    common=['--offline','--release','--manifest-path',str(scalar.CRATE/'Cargo.toml'),'-j','4']
    command('new-recovery-checks',cargo+['test',*common,'--test','window_recovery','--','--test-threads=1'],env,90)
    command('solver-build',cargo+['build',*common,'--bin','expanded_solver'],env,90)
    binary=window.BASE/'target/release/expanded_solver'
    binary_ref=a.ref(binary)
    v=a.read(a.ROOT/'benchmarks/configs/lp-tensor-warp32-v1.json')
    models=instances(v)
    names=a.read(a.ROOT/'benchmarks/configs/lp-exec-v1.json')['timing_instances']
    old_path=a.ROOT/'docs/benchmarks/data/tensor-warp32/cpu-admission-v1.json'
    old=a.read(old_path)
    old_rows={(r['model'],r['configuration']):r for r in old['rows']}
    tasks=[];rows=[]
    for name in names:
        for configuration in v['configurations']:
            historical=old_rows[(name,configuration['id'])]
            row=dict(model=name,configuration=configuration['id'],layout=historical['layout'])
            model=a.checked(models[name]['model'])
            if configuration['layout']=='original_tuned':
                if historical.get('endpoint'):a.checked(historical['endpoint'])
                rows.append(dict(row,status='retained_control',eligible=historical['eligible'],
                    original=historical,prior_admission=a.ref(old_path),passed_check_rerun=False))
            elif configuration['layout'] in ['int8','fp16','bf16','simt'] and not historical['layout']['selected_tiles']:
                rows.append(dict(row,status='layout_refusal',eligible=False,model_binding=models[name]['model']))
            else:tasks.append((name,configuration,model,row))
    a.put(BASE/'frozen-roster.json',dict(cells=48,retained=rows,
        execute=[dict(model=n,configuration=c['id'],model_binding=a.ref(m)) for n,c,m,_ in tasks],
        binary=binary_ref,source_manifest=a.ref(BASE/'source-manifest.json')))
    worker=[sys.executable,str(a.ROOT/'tools/lp_tensor_cost_exec.py'),'--memory-bytes',str(1<<30),'--',str(binary)]
    def one(task):
        name,configuration,model,row=task
        out=BASE/(name+'-'+configuration['id']);out.mkdir()
        request=dict(identity='lp-tensor-expanded-v1',model_sha256=a.ref(model)['sha256'],
            source_tree_sha256=manifest['source_tree_sha256'],executable_sha256=binary_ref['sha256'],
            layout=configuration['layout'],method=dict(v['lp_settings'],iteration_limit=480),
            settings=configuration['settings'],options=dict(v['solve'],iteration_limit=480,time_limit_ms=16000),horizon=400)
        a.put(out/'request.json',request)
        started=time.monotonic_ns()
        p=subprocess.run(worker+['trace-cpu',str(model),str(out/'request.json'),str(out/'endpoint.json')],capture_output=True,text=True,env=env,timeout=900)
        (out/'stdout').write_text(p.stdout);(out/'stderr').write_text(p.stderr)
        a.put(out/'execution.json',dict(returncode=p.returncode,elapsed_ns=time.monotonic_ns()-started,
            stdout=a.ref(out/'stdout'),stderr=a.ref(out/'stderr'),request=a.ref(out/'request.json'),binary=binary_ref))
        if p.returncode:
            a.require('panicked' not in p.stderr,'new CPU solver panic: '+p.stderr)
            result=dict(row,status='preparation_refusal',eligible=False,error=p.stderr)
        else:
            endpoint=a.read(out/'endpoint.json');o=endpoint['outcome'];core=o['core']
            verify=subprocess.run(worker+['verify',str(model),str(out/'request.json'),str(out/'endpoint.json')],capture_output=True,text=True,env=env,timeout=120)
            (out/'verify.stdout').write_text(verify.stdout);(out/'verify.stderr').write_text(verify.stderr)
            receipt=dict(status='passed' if verify.returncode==0 else 'refused',returncode=verify.returncode,
                endpoint=a.ref(out/'endpoint.json'),request=a.ref(out/'request.json'),binary=binary_ref,
                stdout=a.ref(out/'verify.stdout'),stderr=a.ref(out/'verify.stderr'))
            a.put(out/'verification.json',receipt)
            a.require(verify.returncode==0,'new endpoint verification failed: '+verify.stderr)
            # Preparation reductions/bounds must stay bit-equivalent to retained inputs.
            old_endpoint=a.read(a.checked(old_rows[(name,configuration['id'])]['endpoint']))
            a.require(endpoint['norm_proof']==old_endpoint['norm_proof'],'preparation norm proof differs')
            useful=o['counts']['useful_windows']>0
            eligible=core['stop']=='work_horizon' and core['iterations']==400 and (configuration['layout']=='segmented' or useful)
            result=dict(row,status=core['stop'],eligible=eligible,iterations=core['iterations'],physical=core['physical'],
                failure=core['failure'],counts=o['counts'],endpoint=a.ref(out/'endpoint.json'),verification=a.ref(out/'verification.json'))
        a.put(out/'trial.json',result)
        print(name,configuration['id'],result['status'],'eligible',result['eligible'],flush=True)
        return result
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        rows.extend(pool.map(one,tasks))
    for item in manifest['sources']:a.checked(item)
    a.checked(binary_ref)
    required={(name,c['id']) for name in v['timing_instances'] for c in v['configurations']}
    admitted={(r['model'],r['configuration']) for r in rows if r['eligible']}
    result=dict(status='passed' if required<=admitted else 'refused',rows=rows,complete_candidate_inventory=False,
        required_dense_cells=12,missing_required=sorted(required-admitted),gpu_seconds=0,
        source_manifest=a.ref(BASE/'source-manifest.json'),binary=binary_ref,
        ordinary_checks_rerun=False,historical_profiles_rerun=False)
    a.put(a.DATA/'cpu-model-admission-v1.json',result)
    a.require(required<=admitted,'new expanded CPU model admission lacks required useful 400-update trajectories')
    print('All 48 CPU cells accounted; all twelve required dense cells admitted.',flush=True)


def run():
    recovery.preservation()
    j=a.read(JOURNAL);stage='cpu_models';amount=4000*a.NS
    a.stage_admission(j,stage,amount)
    out=BASE/'resource-v1.json'
    j['stage_attempts'][stage]=dict(output=str(out.relative_to(a.ROOT)),reserved_cpu_ns=amount)
    supervisor.atomic_json(JOURNAL,j)
    sources=[a.checked(p) for p in a.read(BASE/'source-manifest.json')['sources']]
    r=supervisor.run(dict(stage=stage,reserve_cpu_seconds=4000,output=str(out),log=str(out)+'.log',
        journal=str(JOURNAL),lock=str(a.ROOT/'artifacts/lp-cpu-admission.lock'),slots=4,
        declared_memory_bytes=4<<30,rss_stop_bytes=6<<30,address_space_bytes=0,
        sources=list(map(str,[*sources,a.ROOT/'tools/lp_tensor_expanded_model_admission.py',a.ROOT/'tools/lp_tensor_cost_exec.py'])),
        bootstrap=False,show_log=True,max_gap_ns=100_000_000,
        command=[sys.executable,str(a.ROOT/'tools/lp_tensor_expanded_model_admission.py'),'child']))
    if r['status']!='passed':
        j=a.read(JOURNAL);j['scientific_closed']=True;supervisor.atomic_json(JOURNAL,j)
    print(json.dumps(dict(status=r['status'],charged_cpu_ns=r['charged_cpu_ns'])))
    return 0 if r['status']=='passed' else 1


if __name__=='__main__':
    if sys.argv[1]=='initialize':initialize()
    elif sys.argv[1]=='child':child()
    elif sys.argv[1]=='run':raise SystemExit(run())
    else:raise SystemExit('unknown action')
