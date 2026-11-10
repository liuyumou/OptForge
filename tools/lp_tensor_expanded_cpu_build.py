"""Bounded validation of the NEW Rust scalar implementation; reuse proof receipts."""
import json
import os
import random
import subprocess
import sys

import lp_cpu_admission as supervisor
import lp_tensor_expanded_authority as a
import lp_tensor_expanded_build as build
import lp_tensor_expanded_recovery as recovery
import lp_expansion_oracle as oracle

BASE = a.BASE/'rust-scalar-v1'
JOURNAL = BASE/'cpu-journal-v7.json'
CRATE = a.ROOT/'research/lp-tensor-expanded'
SOURCES = [CRATE/'Cargo.toml', CRATE/'src/lib.rs', CRATE/'src/main.rs', CRATE/'src/value.rs']


def initialize():
    recovery.preservation()
    j=a.read(build.JOURNAL)
    a.require(not j['failed'] and j['active'] is None,'prior stage failed')
    a.require(a.read(a.DATA/'primitive-inventory-v1.json')['status']=='passed','primitive admission missing')
    amount=600*a.NS
    a.require(j['stages']['implementation']['cap_cpu_ns']-j['stages']['implementation']['charged_cpu_ns']>=amount,'CPU transfer exhausted')
    j['stages']['implementation']['cap_cpu_ns']-=amount
    j['stages']['rust_scalar']=dict(cap_cpu_ns=amount,charged_cpu_ns=0)
    auth=a.DATA/'rust-scalar-authorization-v1.json'
    a.put(auth,dict(status='accepted',authorization='User-authorized conditional continuation with unused-budget transfers.',
        transfer_cpu_seconds=600,source='implementation',target='rust_scalar',
        prior_journal=a.ref(build.JOURNAL),new_implementation=True,passed_checks_rerun=False,
        prior_independent_proof=a.ref(a.DATA/'independent-proof-v2.json'),gpu_seconds=0))
    j.update(identity='gpup-tensor-expanded-rust-scalar-journal-v7',continuation_authorization=a.ref(auth),
             prior_stage_journal=a.ref(build.JOURNAL))
    a.put(JOURNAL,j)
    path=a.ROOT/'state/active-task.md'
    first,rest=path.read_text().split('\n',1)
    path.write_text(first+'\n\n'+'''## GPUP-8 new Rust arithmetic validation (2026-10-24)

The CUDA primitive module passes at 79 registers maximum and zero stack/spills.
Its image is retained for reuse. Add the isolated research Rust scalar path;
public solver registrations and dependencies remain unchanged. Transfer 600
unused implementation CPU seconds to the new Rust scalar acceptance reservation.
Compile only this new executable and compare it with the already verified scalar
outputs plus independent new codec/packing cases; do not rerun the C++ proof or
historical tests. This is new implementation validation, not another proof retry.
Active journal: artifacts/gpup-tensor-expanded-v1/rust-scalar-v1/cpu-journal-v7.json.
Full solver/window/model admission, Tensor inventory and GPU gates remain pending.

'''+rest.lstrip('\n'))
    print('New Rust scalar admission funded; existing independent scalar outputs will be reused.')


def doc(d):
    return dict(magnitude=abs(d['coefficient']),exponent=d['exponent'],
                negative=d['coefficient']<0 if d['coefficient'] else bool(d['zero_sign']))


def child():
    env=os.environ.copy()
    env.update(RUSTUP_HOME='/tmp/ai-optimizer-rustup',CARGO_HOME='/tmp/ai-optimizer-cargo',
        CARGO_TARGET_DIR=str(BASE/'target'),CUDA_VISIBLE_DEVICES='')
    env['PATH']='/tmp/ai-optimizer-cargo/bin:'+env.get('PATH','')
    command=['/tmp/ai-optimizer-cargo/bin/cargo','build','--offline','--release',
             '--manifest-path',str(CRATE/'Cargo.toml'),'-j','4']
    result=subprocess.run(command,capture_output=True,text=True,env=env,timeout=120)
    (BASE/'build.stdout').write_text(result.stdout);(BASE/'build.stderr').write_text(result.stderr)
    a.put(BASE/'build-status.json',dict(returncode=result.returncode,command=command,
        stdout=a.ref(BASE/'build.stdout'),stderr=a.ref(BASE/'build.stderr')))
    a.require(result.returncode==0,'Rust scalar build failed; exact logs retained')
    binary=BASE/'target/release/lp-tensor-expanded-research'
    requests=[];expected=[];categories=[]
    passed=a.read(a.DATA/'independent-proof-v2.json')
    raw=a.checked(passed['scalar']['input']).read_text().splitlines()
    outputs=a.checked(passed['scalar']['output']).read_text().splitlines()
    a.require(len(raw)==len(outputs)==7376,'retained scalar corpus differs')
    for line,output in zip(raw,outputs):
        values=list(map(int,line.split()));got=list(map(int,output.split()))
        requests.append(dict(operation='fma',values=[dict(magnitude=values[k],exponent=values[k+1],negative=bool(values[k+2])) for k in range(0,9,3)]))
        expected.append(dict(error='expanded_overflow') if got[3]==2 else dict(value=dict(magnitude=got[0],exponent=got[1],negative=bool(got[2]))))
        categories.append('new_rust_fma')
    rng=random.Random(17025)
    bitcases=[0,1,(1<<52)-1,1<<52,0x7fefffffffffffff,1<<63,(1<<63)|1,0x7ff0000000000000,0xfff0000000000000,0x7ff8000000000000]
    bitcases += [rng.getrandbits(64) for _ in range(2048)]
    for bits in bitcases:
        requests.append(dict(operation='encode',bits=bits))
        if (bits>>52)&2047==2047: expected.append(dict(error='expanded_nonfinite'))
        else:
            d=oracle.round_fraction(oracle.binary64_fraction(bits),(64,-1022,1023),zero_sign=bits>>63)
            expected.append(dict(value=doc(d)))
        categories.append('new_rust_encode')
    for i in range(1024):
        exponent=rng.randrange(-1085,961)
        magnitude=rng.getrandbits(64) if exponent==-1085 else rng.getrandbits(63)|(1<<63)
        d=dict(coefficient=magnitude*(-1 if i%2 else 1),exponent=exponent,zero_sign=0)
        v=doc(d)
        requests.append(dict(operation='decode',value=v))
        r=oracle.round_fraction(oracle.exact_value(d),(53,-1022,1023))
        if r['infinity_sign']:expected.append(dict(error='expanded_overflow'))
        elif magnitude and not r['coefficient']:expected.append(dict(error='boundary_nonzero_to_zero'))
        else:
            # Binary64 construction from the independently rounded dyadic.
            import struct
            bits=int.from_bytes(struct.pack('>d',float(oracle.exact_value(r))),'big')
            if not r['coefficient']:bits=r['zero_sign']<<63
            expected.append(dict(bits=bits))
        categories.append('new_rust_decode')
        block=exponent+64+rng.choice([0,1,31,63,127])
        requests.append(dict(operation='pack',value=v,exponent=block))
        shift=block-64-exponent
        q=magnitude>>shift
        tail=(magnitude-(q<<shift))*(-1 if i%2 else 1)
        residual=oracle.round_fraction(tail*oracle.power2(exponent),(64,-1022,1023),zero_sign=i%2)
        expected.append(dict(magnitude=q,residual=doc(residual)))
        categories.append('new_rust_pack')
    payload=''.join(json.dumps(row)+'\n' for row in requests)
    (BASE/'input.jsonl').write_text(payload)
    a.put(BASE/'expected.json',dict(expected=expected,categories=categories))
    p=subprocess.run([str(binary)],input=payload,capture_output=True,text=True,env=env,timeout=20)
    (BASE/'output.jsonl').write_text(p.stdout);(BASE/'stderr').write_text(p.stderr)
    a.put(BASE/'execution.json',dict(returncode=p.returncode,binary=a.ref(binary),input=a.ref(BASE/'input.jsonl'),
        output=a.ref(BASE/'output.jsonl'),stderr=a.ref(BASE/'stderr')))
    a.require(p.returncode==0,'Rust arithmetic adapter failed: '+p.stderr)
    rows=[json.loads(line) for line in p.stdout.splitlines()]
    a.require(len(rows)==len(expected),'result count differs')
    for i,(actual,want) in enumerate(zip(rows,expected)):
        if actual!=want:
            a.put(BASE/'counterexample.json',dict(index=i,category=categories[i],request=requests[i],expected=want,actual=actual))
            raise ValueError('new Rust scalar mismatch at '+str(i))
    a.put(a.DATA/'rust-scalar-acceptance-v1.json',dict(status='passed',cases=len(rows),
        source_bound_expected_fma_reused=7376,source_bound_cpp_not_rerun=True,
        sources=[a.ref(p) for p in SOURCES],binary=a.ref(binary),expected=a.ref(BASE/'expected.json'),
        execution=a.ref(BASE/'execution.json'),gpu_seconds=0))
    print('New Rust scalar implementation passes '+str(len(rows))+' source-bound comparisons.',flush=True)


def run():
    recovery.preservation()
    j=a.read(JOURNAL);stage='rust_scalar';reserve=600*a.NS
    a.stage_admission(j,stage,reserve)
    out=BASE/'resource-v1.json'
    j['stage_attempts'][stage]=dict(output=str(out.relative_to(a.ROOT)),reserved_cpu_ns=reserve)
    supervisor.atomic_json(JOURNAL,j)
    r=supervisor.run(dict(stage=stage,reserve_cpu_seconds=600,output=str(out),log=str(out)+'.log',
        journal=str(JOURNAL),lock=str(a.ROOT/'artifacts/lp-cpu-admission.lock'),slots=4,
        declared_memory_bytes=4<<30,rss_stop_bytes=6<<30,address_space_bytes=0,
        sources=[str(p) for p in [*SOURCES,a.ROOT/'tools/lp_tensor_expanded_cpu_build.py']],
        bootstrap=False,show_log=True,max_gap_ns=100_000_000,
        command=[sys.executable,str(a.ROOT/'tools/lp_tensor_expanded_cpu_build.py'),'child']))
    if r['status']!='passed':
        j=a.read(JOURNAL);j['scientific_closed']=True;supervisor.atomic_json(JOURNAL,j)
    print(json.dumps(dict(status=r['status'],charged_cpu_ns=r['charged_cpu_ns'])))
    return 0 if r['status']=='passed' else 1


if __name__=='__main__':
    if sys.argv[1]=='initialize':initialize()
    elif sys.argv[1]=='child':child()
    elif sys.argv[1]=='run':raise SystemExit(run())
    else:raise SystemExit('unknown action')
