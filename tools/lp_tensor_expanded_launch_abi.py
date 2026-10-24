"""Versioned same-owner CUDA argument adapter; only new ABI tests run."""
import json
import os
import subprocess
import sys
import lp_cpu_admission as supervisor
import lp_tensor_expanded_authority as a
import lp_tensor_expanded_recovery as recovery
import lp_tensor_expanded_guard_build as prior

BASE=a.BASE/'launch-abi-v1'
JOURNAL=BASE/'cpu-journal-v14.json'
CRATE=a.ROOT/'research/lp-tensor-expanded-device'
SOURCES=sorted((CRATE/'cuda-sys/src').glob('*.rs'))+[CRATE/'Cargo.toml',CRATE/'cuda-sys/Cargo.toml',CRATE/'src/lib.rs']

def initialize():
    recovery.preservation()
    j=a.read(prior.JOURNAL)
    a.require(not j['failed'] and j['active'] is None,'prior stage incomplete')
    a.require(j['stages']['proof_retry']['cap_cpu_ns']-j['stages']['proof_retry']['charged_cpu_ns']>=600*a.NS,'unused funds exhausted')
    j['stages']['proof_retry']['cap_cpu_ns']-=600*a.NS
    j['stages']['launch_abi']=dict(cap_cpu_ns=600*a.NS,charged_cpu_ns=0)
    auth=a.DATA/'launch-abi-authorization-v1.json'
    old=a.ROOT/'crates/optimizer-cuda-sys/src'
    bridge=[]
    for p in old.glob('*.rs'):
        new=CRATE/'cuda-sys/src'/p.name
        bridge.append(dict(original=a.ref(p),research=a.ref(new),body_unchanged=p.read_bytes()==new.read_bytes()))
        if p.name!='lib.rs':a.require(p.read_bytes()==new.read_bytes(),'unrelated boundary change')
    original=(old/'lib.rs').read_text();new=(CRATE/'cuda-sys/src/lib.rs').read_text()
    a.require(original.split('pub enum Argument')[0]==new.split('pub enum Argument')[0],'pre-launch driver body changed')
    a.require(original[original.index('\n#[cfg(test)]\nmod tests'):]==new[new.index('\n#[cfg(test)]\nmod tests'):].split('\n#[cfg(test)]\nmod expanded_argument_tests')[0].rstrip()+'\n','retained tests changed')
    a.put(auth,dict(status='accepted',authorization='User authorizes necessary harness adjustments and unused-budget transfers.',
        transfer=dict(source='proof_retry',target='launch_abi',cpu_seconds=600),prior_journal=a.ref(prior.JOURNAL),
        source_bridge=bridge,new_unsafe_owner=False,new_foreign_api=False,old_source_preserved=True,
        affected_behavior='Owned aligned 32-byte SoA launch parameters; all device/stream/module ownership bodies unchanged.',
        ordinary_tests_rerun=False,gpu_seconds=0))
    j.update(identity='gpup-tensor-expanded-launch-abi-journal-v14',continuation_authorization=a.ref(auth),prior_stage_journal=a.ref(prior.JOURNAL))
    a.put(JOURNAL,j)
    for p in SOURCES:
        dst=BASE/'source'/p.relative_to(a.ROOT);dst.parent.mkdir(parents=True,exist_ok=True);dst.write_bytes(p.read_bytes())

def child():
    env=os.environ.copy();env.update(RUSTUP_HOME='/tmp/ai-optimizer-rustup',CARGO_HOME='/tmp/ai-optimizer-cargo',
        CARGO_TARGET_DIR=str(BASE/'target'),CUDA_VISIBLE_DEVICES='')
    env['PATH']='/tmp/ai-optimizer-cargo/bin:'+env.get('PATH','')
    command=['/tmp/ai-optimizer-cargo/bin/cargo','test','--offline','--release','--manifest-path',str(CRATE/'Cargo.toml'),
        '-p','optimizer-cuda-sys','--lib','expanded_argument_tests::','-j','4']
    p=subprocess.run(command,capture_output=True,text=True,env=env,timeout=130)
    (BASE/'stdout').write_text(p.stdout);(BASE/'stderr').write_text(p.stderr)
    a.put(a.DATA/'launch-abi-acceptance-v1.json',dict(status='passed' if p.returncode==0 else 'refused',command=command,
        returncode=p.returncode,sources=[a.ref(p) for p in SOURCES],stdout=a.ref(BASE/'stdout'),stderr=a.ref(BASE/'stderr'),
        new_test_count=1,retained_tests_filtered=True,gpu_seconds=0))
    a.require(p.returncode==0,'new launch ABI acceptance failed')
    print(p.stdout,flush=True)

def run():
    recovery.preservation();j=a.read(JOURNAL);stage='launch_abi';amount=600*a.NS
    a.stage_admission(j,stage,amount);out=BASE/'resource-v1.json'
    j['stage_attempts'][stage]=dict(output=str(out.relative_to(a.ROOT)),reserved_cpu_ns=amount)
    supervisor.atomic_json(JOURNAL,j)
    r=supervisor.run(dict(stage=stage,reserve_cpu_seconds=600,output=str(out),log=str(out)+'.log',journal=str(JOURNAL),
        lock=str(a.ROOT/'artifacts/lp-cpu-admission.lock'),slots=4,declared_memory_bytes=4<<30,rss_stop_bytes=6<<30,address_space_bytes=0,
        sources=list(map(str,[*SOURCES,a.ROOT/'tools/lp_tensor_expanded_launch_abi.py'])),bootstrap=False,show_log=True,max_gap_ns=100_000_000,
        command=[sys.executable,str(a.ROOT/'tools/lp_tensor_expanded_launch_abi.py'),'child']))
    if r['status']!='passed':
        j=a.read(JOURNAL);j['scientific_closed']=True;supervisor.atomic_json(JOURNAL,j)
    print(json.dumps(dict(status=r['status'],charged_cpu_ns=r['charged_cpu_ns'])))
    return 0 if r['status']=='passed' else 1

if __name__=='__main__':
    if sys.argv[1]=='initialize':initialize()
    elif sys.argv[1]=='child':child()
    elif sys.argv[1]=='run':raise SystemExit(run())
    else:raise SystemExit('unknown action')
