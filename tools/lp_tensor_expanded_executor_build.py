"""Bounded new executor acceptance with retained numerical evidence bindings."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import lp_cpu_admission as supervisor
import lp_tensor_expanded_authority as a
import lp_tensor_expanded_recovery as recovery
import lp_tensor_expanded_launch_abi as abi
import lp_tensor_expanded_model_admission as models

BASE=a.BASE/'executor-build-v1'
JOURNAL=BASE/'cpu-journal-v15.json'
CRATE=abi.CRATE

def sources():
    return sorted([*CRATE.rglob('*.rs'),CRATE/'Cargo.toml',CRATE/'cuda-sys/Cargo.toml',
        a.ROOT/'research/lp-tensor-expanded/src/value.rs',a.ROOT/'research/lp-tensor-expanded/src/prepared.rs',
        a.ROOT/'research/lp-tensor-expanded/src/outward.rs'])

def command(argv,name,env,timeout):
    p=subprocess.run(argv,capture_output=True,text=True,env=env,timeout=timeout)
    (BASE/(name+'.stdout')).write_text(p.stdout);(BASE/(name+'.stderr')).write_text(p.stderr)
    a.put(BASE/(name+'.json'),dict(command=argv,returncode=p.returncode,stdout=a.ref(BASE/(name+'.stdout')),stderr=a.ref(BASE/(name+'.stderr'))))
    print(p.stdout,flush=True)
    if p.returncode:print(p.stderr,flush=True)
    a.require(p.returncode==0,name+' failed; exact outputs preserved')

def child():
    recovery.preservation()
    for item in a.read(models.BASE/'source-manifest.json')['sources']:a.checked(item)
    original=(a.ROOT/'research/lp-tensor-expanded/src/solver.rs').read_bytes()
    a.require((CRATE/'src/solver_adapter.rs').read_bytes().startswith(original),'CPU arithmetic body changed')
    saved=abi.BASE/'source/research/lp-tensor-expanded-device/cuda-sys/src/lib.rs'
    a.require((CRATE/'cuda-sys/src/lib.rs').read_text().replace('pub mod events;\n','')==saved.read_text(),
        'accepted argument or retained driver body changed')
    for item in a.read(a.DATA/'launch-abi-acceptance-v1.json')['sources']:
        path=a.ROOT/item['path']
        if path in [CRATE/'src/lib.rs',CRATE/'cuda-sys/src/lib.rs']:
            archive=abi.BASE/'source'/item['path']
            a.require(hashlib.sha256(archive.read_bytes()).hexdigest()==item['sha256'],'ABI source archive mismatch')
        else:a.checked(item)
    env=os.environ.copy();env.update(RUSTUP_HOME='/tmp/ai-optimizer-rustup',CARGO_HOME='/tmp/ai-optimizer-cargo',
        CARGO_TARGET_DIR=str(BASE/'target'),CUDA_VISIBLE_DEVICES='')
    env['PATH']='/tmp/ai-optimizer-cargo/bin:'+env.get('PATH','')
    # Copy caches, never hard-link or rebuild inside a passed evidence directory.
    shutil.copytree(models.a.BASE/'rust-window-v1/target',BASE/'target')
    for path in (abi.BASE/'target').rglob('*'):
        dst=BASE/'target'/path.relative_to(abi.BASE/'target')
        if path.is_dir():dst.mkdir(exist_ok=True)
        elif path.is_file() and not dst.exists():shutil.copy2(path,dst)
    new=[CRATE/'src'/name for name in ['main.rs','native.rs','device.rs','device_checks.rs']]+[CRATE/'cuda-sys/src/events.rs']
    command(['/tmp/ai-optimizer-cargo/bin/rustfmt','--edition','2024','--config','skip_children=true',*map(str,new)],'format',env,15)
    manifest=[a.ref(p) for p in sources()]
    source_hash=hashlib.sha256(json.dumps(manifest,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    env['EXPANDED_SOURCE_SHA256']=source_hash
    a.put(BASE/'source-manifest.json',dict(source_tree_sha256=source_hash,sources=manifest,CPU_solver_prefix_sha256=hashlib.sha256(original).hexdigest(),
        retained_ABI_source=a.ref(saved),retained_CPU_admission=a.ref(a.DATA/'cpu-model-admission-v1.json'),
        unchanged_CPU_cases_not_rerun=True,CUDA_images_not_recompiled=True))
    for p in sources():
        dst=BASE/'source'/p.relative_to(a.ROOT);dst.parent.mkdir(parents=True,exist_ok=True);dst.write_bytes(p.read_bytes())
    cargo='/tmp/ai-optimizer-cargo/bin/cargo'
    common=['--offline','--release','--manifest-path',str(CRATE/'Cargo.toml'),'-p','lp-tensor-expanded-device','--bin','lp-tensor-expanded-device','-j','4']
    command([cargo,'clippy',*common,'--','-D','warnings'],'clippy',env,130)
    command([cargo,'build',*common],'build',env,130)
    command([cargo,'test',*common,'integration_contract_tests::','--','--test-threads=1'],'new-tests',env,60)
    binary=BASE/'target/release/lp-tensor-expanded-device'
    a.put(a.DATA/'executor-native-acceptance-v1.json',dict(status='passed',source_manifest=a.ref(BASE/'source-manifest.json'),binary=a.ref(binary),
        checks=[a.ref(BASE/(name+'.json')) for name in ['format','clippy','build','new-tests']],
        historical_tests_rerun=False,passed_numerical_cases_rerun=False,gpu_seconds=0,
        full_device_acceptance=False))

def run():
    recovery.preservation();j=a.read(JOURNAL);stage='executor_build';amount=1600*a.NS
    a.stage_admission(j,stage,amount);out=BASE/'resource-v1.json'
    j['stage_attempts'][stage]=dict(output=str(out.relative_to(a.ROOT)),reserved_cpu_ns=amount)
    supervisor.atomic_json(JOURNAL,j)
    r=supervisor.run(dict(stage=stage,reserve_cpu_seconds=1600,output=str(out),log=str(out)+'.log',journal=str(JOURNAL),
        lock=str(a.ROOT/'artifacts/lp-cpu-admission.lock'),slots=4,declared_memory_bytes=4<<30,rss_stop_bytes=6<<30,address_space_bytes=0,
        sources=list(map(str,[*sources(),a.ROOT/'tools/lp_tensor_expanded_executor_build.py'])),bootstrap=False,show_log=True,max_gap_ns=100_000_000,
        command=[sys.executable,str(a.ROOT/'tools/lp_tensor_expanded_executor_build.py'),'child']))
    if r['status']!='passed':
        j=a.read(JOURNAL);j['scientific_closed']=True;supervisor.atomic_json(JOURNAL,j)
    print(json.dumps(dict(status=r['status'],charged_cpu_ns=r['charged_cpu_ns'])))
    return 0 if r['status']=='passed' else 1

if __name__=='__main__':
    if sys.argv[1]=='child':child()
    elif sys.argv[1]=='run':raise SystemExit(run())
    else:raise SystemExit('unknown action')
