"""New Rust window/preparation acceptance; never invokes retained test suites."""
import json
import os
import subprocess
import sys

import lp_cpu_admission as supervisor
import lp_tensor_expanded_authority as a
import lp_tensor_expanded_recovery as recovery
import lp_tensor_expanded_cpu_build as scalar

BASE=a.BASE/'rust-window-v1'
JOURNAL=BASE/'cpu-journal-v8.json'
NEW_SOURCES=[scalar.CRATE/'src'/name for name in ['bin/expanded_solver.rs','solver.rs','prepared.rs','outward.rs']]


def initialize():
    recovery.preservation()
    receipt=a.read(a.DATA/'rust-scalar-acceptance-v1.json')
    for source in receipt['sources']:a.checked(source)
    j=a.read(scalar.JOURNAL)
    a.require(not j['failed'] and j['active'] is None,'prior stage incomplete')
    a.require(j['stages']['implementation']['cap_cpu_ns']-j['stages']['implementation']['charged_cpu_ns']>=416*a.NS,'unused budget exhausted')
    j['stages']['implementation']['cap_cpu_ns']-=400*a.NS
    j['stages']['implementation']['charged_cpu_ns']+=16*a.NS
    j['stages']['cpu_window']=dict(cap_cpu_ns=400*a.NS,charged_cpu_ns=0)
    auth=a.DATA/'rust-window-authorization-v1.json'
    a.put(auth,dict(status='accepted',authorization='User-authorized conditional continuation using unused allocations.',
        transfer=dict(source='implementation',target='cpu_window',cpu_seconds=400),
        prior_journal=a.ref(scalar.JOURNAL),prior_scalar=a.ref(a.DATA/'rust-scalar-acceptance-v1.json'),
        new_sources=[a.ref(p) for p in NEW_SOURCES],implementation_bookkeeping_cpu_seconds=16,
        historical_sources_unchanged=True,passed_checks_rerun=False,gpu_seconds=0))
    j['runs'].append(dict(stage='implementation',charged_cpu_ns=16*a.NS,
        status='conservative_window_source_bookkeeping',output=str(auth)))
    j.update(identity='gpup-tensor-expanded-rust-window-journal-v8',continuation_authorization=a.ref(auth),
             prior_stage_journal=a.ref(scalar.JOURNAL))
    a.put(JOURNAL,j)
    path=a.ROOT/'state/active-task.md';first,rest=path.read_text().split('\n',1)
    path.write_text(first+'\n\n'+'''## GPUP-8 new Rust window acceptance (2026-10-24)

The new Rust scalar path passes 11482 comparisons. Preserve its source-bound
evidence and the passed CUDA primitive image. New isolated CPU solver work adds
expanded windows, local update/conversion enclosures, separate wider counters,
generation-bound rollback, bounded preparation lookup tables, contiguous groups,
predecoded Gram coefficient parts and reusable assessment assignments.
Transfer 400 unused implementation CPU seconds to new Rust window/preparation
acceptance; charge 16 implementation seconds for construction bookkeeping.
Run only the new bin's three focused tests, including five window lengths and
canonical penultimate inputs. Full model admission and GPU implementation remain
pending; no complete solver/device/inventory claim follows these checks.
Active journal: artifacts/gpup-tensor-expanded-v1/rust-window-v1/cpu-journal-v8.json.
All completion criteria, historical evidence and GPU allocations remain exact.

'''+rest.lstrip('\n'))


def child():
    env=os.environ.copy();env.update(RUSTUP_HOME='/tmp/ai-optimizer-rustup',
        CARGO_HOME='/tmp/ai-optimizer-cargo',CARGO_TARGET_DIR=str(BASE/'target'),CUDA_VISIBLE_DEVICES='')
    env['PATH']='/tmp/ai-optimizer-cargo/bin:'+env.get('PATH','')
    command=['/tmp/ai-optimizer-cargo/bin/cargo','test','--offline','--release',
        '--manifest-path',str(scalar.CRATE/'Cargo.toml'),'--bin','expanded_solver','-j','4',
        '--','--test-threads=1']
    p=subprocess.run(command,capture_output=True,text=True,env=env,timeout=90)
    (BASE/'accept.stdout').write_text(p.stdout);(BASE/'accept.stderr').write_text(p.stderr)
    a.put(a.DATA/'rust-window-acceptance-v1.json',dict(status='passed' if p.returncode==0 else 'refused',
        command=command,returncode=p.returncode,stdout=a.ref(BASE/'accept.stdout'),stderr=a.ref(BASE/'accept.stderr'),
        sources=[a.ref(p) for p in NEW_SOURCES],scalar_source=a.ref(scalar.CRATE/'src/value.rs'),
        passed_tests_rerun=False,gpu_seconds=0))
    print(p.stdout,flush=True)
    if p.returncode:print(p.stderr,flush=True)
    a.require(p.returncode==0,'new Rust window acceptance failed')


def run():
    recovery.preservation()
    for source in a.read(a.DATA/'rust-scalar-acceptance-v1.json')['sources']:a.checked(source)
    j=a.read(JOURNAL);stage='cpu_window';amount=400*a.NS
    a.stage_admission(j,stage,amount)
    out=BASE/'resource-v1.json'
    j['stage_attempts'][stage]=dict(output=str(out.relative_to(a.ROOT)),reserved_cpu_ns=amount)
    supervisor.atomic_json(JOURNAL,j)
    r=supervisor.run(dict(stage=stage,reserve_cpu_seconds=400,output=str(out),log=str(out)+'.log',
        journal=str(JOURNAL),lock=str(a.ROOT/'artifacts/lp-cpu-admission.lock'),slots=4,
        declared_memory_bytes=4<<30,rss_stop_bytes=6<<30,address_space_bytes=0,
        sources=[str(p) for p in [*NEW_SOURCES,scalar.CRATE/'src/value.rs',a.ROOT/'tools/lp_tensor_expanded_window_accept.py']],
        bootstrap=False,show_log=True,max_gap_ns=100_000_000,
        command=[sys.executable,str(a.ROOT/'tools/lp_tensor_expanded_window_accept.py'),'child']))
    if r['status']!='passed':
        j=a.read(JOURNAL);j['scientific_closed']=True;supervisor.atomic_json(JOURNAL,j)
    print(json.dumps(dict(status=r['status'],charged_cpu_ns=r['charged_cpu_ns'])))
    return 0 if r['status']=='passed' else 1


if __name__=='__main__':
    if sys.argv[1]=='initialize':initialize()
    elif sys.argv[1]=='child':child()
    elif sys.argv[1]=='run':raise SystemExit(run())
    else:raise SystemExit('unknown action')
