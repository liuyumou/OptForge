"""Authorized wrapper correction; resumes unpassed integration checks only."""
import hashlib
import json
import os
import shutil
import subprocess
import sys
import lp_cpu_admission as supervisor
import lp_tensor_expanded_authority as a
import lp_tensor_expanded_recovery as recovery
import lp_tensor_expanded_executor_build as old

BASE=a.BASE/'executor-recovery-v1'
JOURNAL=BASE/'cpu-journal-v16.json'

def initialize():
    recovery.preservation();j=a.read(old.JOURNAL)
    a.require(j['failed'] and j['active'] is None,'prior construction gate not closed')
    log=(old.BASE/'clippy.stderr').read_text()
    a.require('function `sum` is never used' in log and 'function `sum_using` is never used' in log,'unexpected refusal')
    for source,amount in [('primitive_compile',700),('authority',100)]:
        a.require(j['stages'][source]['cap_cpu_ns']-j['stages'][source]['charged_cpu_ns']>=amount*a.NS,'unused funds exhausted')
        j['stages'][source]['cap_cpu_ns']-=amount*a.NS
    j['stages']['executor_recovery']=dict(cap_cpu_ns=800*a.NS,charged_cpu_ns=0)
    j['stages']['implementation']['charged_cpu_ns']+=16*a.NS
    auth=a.DATA/'executor-recovery-authorization-v1.json'
    a.put(auth,dict(status='accepted',authorization='Explicit user authorization to adjust the harness as needed and reallocate unused funds.',
        correction='Scope an unused-code annotation to the exact retained outward helper module in the new wrapper; no arithmetic change.',
        previous_journal=a.ref(old.JOURNAL),failure=a.ref(old.BASE/'clippy.json'),retained_full_failure_cpu_seconds=1600,
        transfers_cpu_seconds=[dict(source='primitive_compile',amount=700),dict(source='authority',amount=100)],
        target='executor_recovery',new_cpu_seconds=0,gpu_seconds=0,passed_checks_rerun=False,
        construction_source_manifest=a.ref(old.BASE/'source-manifest.json'),
        source_snapshot_note='The initial construction reservation captured pre-format source hashes; its compiler inputs are preserved separately in source-manifest.json and source/.'))
    j['runs'].append(dict(stage='implementation',charged_cpu_ns=16*a.NS,status='conservative_wrapper_correction_bookkeeping',output=str(auth)))
    j.update(identity='gpup-tensor-expanded-executor-recovery-journal-v16',failed=False,scientific_closed=False,
        continuation_authorization=a.ref(auth),prior_stage_journal=a.ref(old.JOURNAL))
    a.put(JOURNAL,j)
    path=a.ROOT/'state/active-task.md';first,rest=path.read_text().split('\n',1)
    path.write_text(first+'\n\n## GPUP-8 wrapper lint correction (2026-10-24)\n\nThe integration construction gate stops at two unused retained enclosure helpers\nimported into the new library wrapper. No arithmetic/device test fails or runs.\nPreserve the exact failed compiler inputs and full 1600-CPU-second charge. Under\nthe user\'s explicit harness-correction authority, add a scoped unused annotation\nto that module; its numerical body remains exact. Transfer 700 unused primitive\ncompile seconds and 100 unused authority seconds to the new 800-second gate.\nThe formatter already passed and is not rerun. Continue only unpassed Clippy,\nproducer build and new interface tests. No GPU work or changed criteria.\nActive journal: artifacts/gpup-tensor-expanded-v1/executor-recovery-v1/cpu-journal-v16.json.\n\n'+rest.lstrip('\n'))

def child():
    recovery.preservation()
    previous=a.read(old.BASE/'source-manifest.json')
    changed=old.CRATE/'src/lib.rs'
    for item in previous['sources']:
        path=a.ROOT/item['path']
        if path==changed:
            saved=old.BASE/'source'/item['path'];a.require(a.ref(saved)['sha256']==item['sha256'],'saved wrapper mismatch')
            a.require(changed.read_text().replace('#[allow(dead_code)] // Retain the exact shared enclosure body, including unused sums.\n','')==saved.read_text(),'unexpected wrapper change')
        else:a.checked(item)
    shutil.copytree(old.BASE/'target',BASE/'target')
    manifest=[a.ref(p) for p in old.sources()]
    source_hash=hashlib.sha256(json.dumps(manifest,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    a.put(BASE/'source-manifest.json',dict(source_tree_sha256=source_hash,sources=manifest,
        original_manifest=a.ref(old.BASE/'source-manifest.json'),arithmetic_body_changed=False,formatter_reused=a.ref(old.BASE/'format.json')))
    for path in old.sources():
        dest=BASE/'source'/path.relative_to(a.ROOT);dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(path.read_bytes())
    env=os.environ.copy();env.update(RUSTUP_HOME='/tmp/ai-optimizer-rustup',CARGO_HOME='/tmp/ai-optimizer-cargo',
        CARGO_TARGET_DIR=str(BASE/'target'),CUDA_VISIBLE_DEVICES='',EXPANDED_SOURCE_SHA256=source_hash)
    env['PATH']='/tmp/ai-optimizer-cargo/bin:'+env.get('PATH','')
    cargo='/tmp/ai-optimizer-cargo/bin/cargo';common=['--offline','--release','--manifest-path',str(old.CRATE/'Cargo.toml'),'-p','lp-tensor-expanded-device','--bin','lp-tensor-expanded-device','-j','4']
    for action,label,extra,timeout in [('clippy','clippy',['--','-D','warnings'],55),('build','build',[],85),('test','new-tests',['integration_contract_tests::','--','--test-threads=1'],40)]:
        argv=[cargo,action,*common,*extra];p=subprocess.run(argv,capture_output=True,text=True,env=env,timeout=timeout)
        (BASE/(label+'.stdout')).write_text(p.stdout);(BASE/(label+'.stderr')).write_text(p.stderr)
        a.put(BASE/(label+'.json'),dict(command=argv,returncode=p.returncode,stdout=a.ref(BASE/(label+'.stdout')),stderr=a.ref(BASE/(label+'.stderr'))))
        print(p.stdout,flush=True)
        if p.returncode:print(p.stderr,flush=True)
        a.require(p.returncode==0,label+' failed')
    a.put(a.DATA/'executor-native-acceptance-v2.json',dict(status='passed',source_manifest=a.ref(BASE/'source-manifest.json'),
        binary=a.ref(BASE/'target/release/lp-tensor-expanded-device'),checks=[a.ref(BASE/(n+'.json')) for n in ['clippy','build','new-tests']],
        retained_format=a.ref(old.BASE/'format.json'),historical_checks_rerun=False,gpu_seconds=0))

def run():
    recovery.preservation();j=a.read(JOURNAL);stage='executor_recovery';amount=800*a.NS
    a.stage_admission(j,stage,amount);out=BASE/'resource-v1.json';j['stage_attempts'][stage]=dict(output=str(out.relative_to(a.ROOT)),reserved_cpu_ns=amount)
    supervisor.atomic_json(JOURNAL,j)
    r=supervisor.run(dict(stage=stage,reserve_cpu_seconds=800,output=str(out),log=str(out)+'.log',journal=str(JOURNAL),lock=str(a.ROOT/'artifacts/lp-cpu-admission.lock'),slots=4,
        declared_memory_bytes=4<<30,rss_stop_bytes=6<<30,address_space_bytes=0,sources=list(map(str,[*old.sources(),a.ROOT/'tools/lp_tensor_expanded_executor_recovery.py'])),
        bootstrap=False,show_log=True,max_gap_ns=100_000_000,command=[sys.executable,str(a.ROOT/'tools/lp_tensor_expanded_executor_recovery.py'),'child']))
    if r['status']!='passed':
        j=a.read(JOURNAL);j['scientific_closed']=True;supervisor.atomic_json(JOURNAL,j)
    print(json.dumps(dict(status=r['status'],charged_cpu_ns=r['charged_cpu_ns'])))
    return 0 if r['status']=='passed' else 1

if __name__=='__main__':
    if sys.argv[1]=='initialize':initialize()
    elif sys.argv[1]=='child':child()
    elif sys.argv[1]=='run':raise SystemExit(run())
    else:raise SystemExit('unknown action')
