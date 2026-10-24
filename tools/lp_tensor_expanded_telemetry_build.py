"""Finish forecast instrumentation before device freeze; reuse numerical checks."""
import hashlib
import json
import os
import shutil
import subprocess
import sys
import lp_cpu_admission as supervisor
import lp_tensor_expanded_authority as a
import lp_tensor_expanded_recovery as recovery
import lp_tensor_expanded_executor_build as build
import lp_tensor_expanded_executor_recovery as previous

BASE=a.BASE/'telemetry-build-v1'
JOURNAL=BASE/'cpu-journal-v17.json'

def initialize():
    recovery.preservation();j=a.read(previous.JOURNAL)
    a.require(not j['failed'] and j['active'] is None,'prior integration not passed')
    a.require(j['stages']['executor_recovery']['cap_cpu_ns']-j['stages']['executor_recovery']['charged_cpu_ns']>=320*a.NS,'unused funds exhausted')
    j['stages']['executor_recovery']['cap_cpu_ns']-=320*a.NS
    j['stages']['telemetry_build']=dict(cap_cpu_ns=320*a.NS,charged_cpu_ns=0)
    j['stages']['implementation']['charged_cpu_ns']+=16*a.NS
    auth=a.DATA/'telemetry-build-authorization-v1.json'
    a.put(auth,dict(status='accepted',authorization='Required pre-freeze instrumentation under the approved plan; unused-budget transfers authorized.',
        prior_journal=a.ref(previous.JOURNAL),prior_native_acceptance=a.ref(a.DATA/'executor-native-acceptance-v2.json'),
        transfer=dict(source='executor_recovery',target='telemetry_build',cpu_seconds=320),
        change='Record the retained cumulative certificate-boundary/final-assessment/execute envelopes; bind actual executor; preserve deadline status after final assessment.',
        numerical_sources_changed=False,old_interface_tests_rerun=False,old_arithmetic_tests_rerun=False,gpu_seconds=0))
    j['runs'].append(dict(stage='implementation',charged_cpu_ns=16*a.NS,status='conservative_instrumentation_bookkeeping',output=str(auth)))
    j.update(identity='gpup-tensor-expanded-telemetry-journal-v17',continuation_authorization=a.ref(auth),prior_stage_journal=a.ref(previous.JOURNAL));a.put(JOURNAL,j)
    path=a.ROOT/'state/active-task.md';first,rest=path.read_text().split('\n',1)
    path.write_text(first+'\n\n## GPUP-8 native integration passes; final profile instrumentation (2026-10-24)\n\nClippy, producer compilation and two new interface tests pass. Preserve their\nsource/binary receipts. Complete the required cumulative first-certificate,\nfinal-assessment and execution timing fields before device freeze, using the\nretained observation schedule and formula. Bind the actual executor and preserve\ndeadline status after final assessment. Arithmetic, window logic and images stay\nexact; reuse all numerical/interface checks. Transfer 320 unused executor-recovery\nCPU seconds to new telemetry acceptance, running only its one new contract test\nand affected producer compilation/lint. Active journal: artifacts/\ngpup-tensor-expanded-v1/telemetry-build-v1/cpu-journal-v17.json. No GPU work yet.\n\n'+rest.lstrip('\n'))

def child():
    recovery.preservation();main=build.CRATE/'src/main.rs'
    for item in a.read(previous.BASE/'source-manifest.json')['sources']:
        if a.ROOT/item['path']!=main:a.checked(item)
    saved=BASE/'before-format/main.rs';saved.parent.mkdir();saved.write_bytes(main.read_bytes())
    shutil.copytree(previous.BASE/'target',BASE/'target')
    env=os.environ.copy();env.update(RUSTUP_HOME='/tmp/ai-optimizer-rustup',CARGO_HOME='/tmp/ai-optimizer-cargo',CARGO_TARGET_DIR=str(BASE/'target'),CUDA_VISIBLE_DEVICES='')
    env['PATH']='/tmp/ai-optimizer-cargo/bin:'+env.get('PATH','')
    subprocess.run(['/tmp/ai-optimizer-cargo/bin/rustfmt','--edition','2024','--config','skip_children=true',str(main)],check=True,timeout=10)
    manifest=[a.ref(p) for p in build.sources()];digest=hashlib.sha256(json.dumps(manifest,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    env['EXPANDED_SOURCE_SHA256']=digest
    a.put(BASE/'source-manifest.json',dict(source_tree_sha256=digest,sources=manifest,
        prior_acceptance=a.ref(a.DATA/'executor-native-acceptance-v2.json'),new_source_only=a.ref(main),before_format=a.ref(saved)))
    for p in build.sources():
        dest=BASE/'source'/p.relative_to(a.ROOT);dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(p.read_bytes())
    common=['--offline','--release','--manifest-path',str(build.CRATE/'Cargo.toml'),'-p','lp-tensor-expanded-device','--bin','lp-tensor-expanded-device','-j','4']
    for action,name,extra,timeout in [('clippy','clippy',['--','-D','warnings'],20),('build','build',[],25),('test','telemetry-test',['telemetry_contract_tests::','--','--test-threads=1'],20)]:
        argv=['/tmp/ai-optimizer-cargo/bin/cargo',action,*common,*extra]
        p=subprocess.run(argv,capture_output=True,text=True,env=env,timeout=timeout)
        (BASE/(name+'.stdout')).write_text(p.stdout);(BASE/(name+'.stderr')).write_text(p.stderr)
        a.put(BASE/(name+'.json'),dict(command=argv,returncode=p.returncode,stdout=a.ref(BASE/(name+'.stdout')),stderr=a.ref(BASE/(name+'.stderr'))))
        print(p.stdout,flush=True)
        if p.returncode:print(p.stderr,flush=True)
        a.require(p.returncode==0,name+' failed')
    a.put(a.DATA/'executor-native-acceptance-v3.json',dict(status='passed',source_manifest=a.ref(BASE/'source-manifest.json'),
        binary=a.ref(BASE/'target/release/lp-tensor-expanded-device'),checks=[a.ref(BASE/(n+'.json')) for n in ['clippy','build','telemetry-test']],
        reused_native=a.ref(a.DATA/'executor-native-acceptance-v2.json'),old_tests_filtered=True,gpu_seconds=0))

def run():
    recovery.preservation();j=a.read(JOURNAL);stage='telemetry_build';amount=320*a.NS
    a.stage_admission(j,stage,amount);out=BASE/'resource-v1.json';j['stage_attempts'][stage]=dict(output=str(out.relative_to(a.ROOT)),reserved_cpu_ns=amount);supervisor.atomic_json(JOURNAL,j)
    r=supervisor.run(dict(stage=stage,reserve_cpu_seconds=320,output=str(out),log=str(out)+'.log',journal=str(JOURNAL),lock=str(a.ROOT/'artifacts/lp-cpu-admission.lock'),slots=4,
        declared_memory_bytes=4<<30,rss_stop_bytes=6<<30,address_space_bytes=0,sources=list(map(str,[*build.sources(),a.ROOT/'tools/lp_tensor_expanded_telemetry_build.py'])),
        bootstrap=False,show_log=True,max_gap_ns=100_000_000,command=[sys.executable,str(a.ROOT/'tools/lp_tensor_expanded_telemetry_build.py'),'child']))
    if r['status']!='passed':
        j=a.read(JOURNAL);j['scientific_closed']=True;supervisor.atomic_json(JOURNAL,j)
    print(json.dumps(dict(status=r['status'],charged_cpu_ns=r['charged_cpu_ns'])))
    return 0 if r['status']=='passed' else 1

if __name__=='__main__':
    if sys.argv[1]=='initialize':initialize()
    elif sys.argv[1]=='child':child()
    elif sys.argv[1]=='run':raise SystemExit(run())
    else:raise SystemExit('unknown action')
