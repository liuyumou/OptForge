"""Artifact-only PTX opcode review; no compiler, numerical test or GPU rerun."""
import bisect
import json
import re
import sys

import lp_cpu_admission as supervisor
import lp_tensor_expanded_authority as a
import lp_tensor_expanded_products_build as products
import lp_tensor_expanded_recovery as recovery

BASE=a.BASE/'instruction-review-v1'
JOURNAL=BASE/'cpu-journal-v11.json'


def instructions(ptx):
    # Only instruction tokens carry type/FTZ modifiers. Operand register names
    # such as %f64 are ordinary FP32 registers and must never be parsed as types.
    text=re.sub(r'/\*.*?\*/|//[^\n]*',lambda m:'\n'*m.group().count('\n'),ptx,flags=re.S)
    entries=[(m.start(),m.group(1)) for m in re.finditer(r'\.visible\s+\.entry\s+(\w+)',text)]
    positions=[p for p,_ in entries]
    pattern=r'(?m)(?:^|;)[ \t{}]*(?:[A-Za-z_$][\w.$]*:[ \t]*)?(?:@!?%[\w$]+[ \t]+)?([a-z][a-z0-9_]*(?:\.[a-zA-Z0-9_]+)+)\b'
    for match in re.finditer(pattern,text):
        opcode=match.group(1);parts=opcode.split('.')
        index=bisect.bisect_right(positions,match.start())-1
        yield dict(opcode=opcode,entry=entries[index][1] if index>=0 else None,
            forbidden=('ftz' in parts or parts[0] in ['add','sub','mul','fma','div'] and 'f64' in parts[1:]))


def initialize():
    recovery.preservation()
    old=a.read(products.JOURNAL);record=a.read(a.DATA/'product-inventory-v1.json')
    a.require(old['failed'] and old['scientific_closed'] and old['active'] is None,'unexpected inventory state')
    a.require(record['returncode']==0,'compilation did not succeed')
    for item in record['sources']:a.checked(item)
    for key in ['image','ptx','sass','resource_dump','stderr']:a.checked(record[key])
    ptx=a.checked(record['ptx']).read_text()
    old_pattern=r'\b(?:add|sub|mul|fma|div)\.[^;\n]*f64|\b\w+\.ftz\.'
    matches=[m.group() for m in re.finditer(old_pattern,ptx)]
    a.require(len(matches)==1 and matches[0].startswith('fma.rn.f32') and matches[0].endswith('%f64'),
              'failure is not the diagnosed register-name false positive')
    auth=a.DATA/'instruction-review-authorization-v1.json'
    a.put(auth,dict(status='accepted',authorization='User explicitly permits harness correction and unused-budget reallocation; no passed check/profile rerun.',
        prior_journal=a.ref(products.JOURNAL),original_inventory=a.ref(a.DATA/'product-inventory-v1.json'),
        diagnosed_match=matches[0],correction='Read opcode modifiers, never operand register names.',
        transfer=dict(source='cpu_models',target='instruction_review',cpu_seconds=160),
        retained_failed_charge_ns=800*a.NS,compiler_rerun=False,numerical_checks_rerun=False,
        scientific_criteria_changed=False,gpu_seconds=0))
    a.require(old['stages']['cpu_models']['cap_cpu_ns']-old['stages']['cpu_models']['charged_cpu_ns']>=160*a.NS,'unused funds exhausted')
    old['stages']['cpu_models']['cap_cpu_ns']-=160*a.NS
    old['stages']['instruction_review']=dict(cap_cpu_ns=160*a.NS,charged_cpu_ns=16*a.NS)
    old['runs'].append(dict(stage='instruction_review',charged_cpu_ns=16*a.NS,
        status='conservative_harness_diagnosis_bookkeeping',output=str(auth)))
    old.update(identity='gpup-tensor-expanded-instruction-review-journal-v11',
        failed=False,scientific_closed=False,continuation_authorization=a.ref(auth),
        prior_stage_journal=a.ref(products.JOURNAL))
    a.put(JOURNAL,old)
    p=a.ROOT/'state/active-task.md';first,rest=p.read_text().split('\n',1)
    p.write_text(first+'\n\n'+'''## GPUP-8 emitted-instruction scanner correction (2026-10-24)

The wider CUDA module compiles successfully: all seven entries use <=72 registers,
zero stack/spills, and all three Tensor entry points contain intended MMA.
The scanner falsely rejects `fma.rn.f32 ... %f64`: it mistakes a register name
for an FP64 type modifier. Preserve the exact successful image, assembly, original
refusal, sources and full 800-CPU-second failure charge. The user's explicit
harness-correction authorization permits an artifact-only corrected review.
Transfer 160 unused CPU-model seconds, with 16 for diagnosis/bookkeeping. Test
opcode parsing, re-read the existing assembly, and continue only if unchanged
requirements pass. Rerun no compiler, numerical check or profile.
Active journal: artifacts/gpup-tensor-expanded-v1/instruction-review-v1/cpu-journal-v11.json.
No GPU work or scientific criterion changes.

'''+rest.lstrip('\n'))


def child():
    tests=[
        ('fma.rn.f32 %f284, %f58, %f61, %f64;',False),
        ('fma.rn.f64 %fd0, %fd1, %fd2, %fd3;',True),
        ('@!%p2 add.rn.f64 %fd0, %fd1, %fd2;',True),
        ('$L_label: mul.rn.f64 %fd0, %fd1, %fd2;',True),
        ('add.s64 %rd0, %rd1, %rd2;',False),
        ('setp.eq.f64 %p0, %fd0, 0d0000000000000000;',False),
        ('add.rn.ftz.f32 %f0, %f1, %f2;',True),
        ('mul.rn.f32 %f0, %f1, %f2; div.rn.f64 %fd0, %fd1, %fd2;',True),
        ('// add.rn.f64\nfma.rn.f32 %f0, %f64, %f1, %f2; /* div.rn.f64 */',False),
        ('.reg .f64 %fd<12>;\n.reg .f32 %f<500>;\nfma.rn.f32 %f0, %f64, %f1, %f2;',False),
    ]
    for text,want in tests:
        a.require(any(r['forbidden'] for r in instructions(text))==want,'opcode parser counterexample: '+text)
    old=a.read(a.DATA/'product-inventory-v1.json')
    for item in old['sources']:a.checked(item)
    for key in ['image','ptx','sass','resource_dump','stderr']:a.checked(old[key])
    rows=list(instructions(a.checked(old['ptx']).read_text()))
    forbidden=[r for r in rows if r['forbidden']]
    a.require(rows and {r['entry'] for r in rows}>=set(products.NAMES),'opcode inventory incomplete')
    a.require(not forbidden,'actual forbidden instruction: '+str(forbidden[:3]))
    a.require(all(r['registers']<=128 and r['spill_store_bytes']==r['spill_load_bytes']==0 for r in old['resources']),
              'resource requirement failed')
    a.require(all(old['tensor_instructions'].values()),'required Tensor instructions absent')
    recovery.preservation()
    a.put(a.DATA/'product-inventory-reviewed-v2.json',dict(identity='gpup-tensor-expanded-product-inventory-reviewed-v2',
        status='passed',original_inventory=a.ref(a.DATA/'product-inventory-v1.json'),
        original_charge_retained_ns=800*a.NS,image=old['image'],ptx=old['ptx'],sass=old['sass'],
        sources=old['sources'],resources=old['resources'],tensor_instructions=old['tensor_instructions'],
        opcode_parser_cases=len(tests),parsed_instructions=len(rows),forbidden_opcodes=forbidden,
        reviewer=a.ref(a.ROOT/'tools/lp_tensor_expanded_instruction_review.py'),
        compiler_rerun=False,numerical_checks_rerun=False,gpu_seconds=0,complete_candidate_inventory=False,
        execution_counter_validation_pending=True,planned_mma_per_tile_product=old['planned_mma_per_tile_product']))
    print('Ten new opcode-reader cases pass; retained image passes all unchanged compile-only requirements.',flush=True)


def run():
    recovery.preservation()
    j=a.read(JOURNAL);stage='instruction_review';amount=144*a.NS
    a.stage_admission(j,stage,amount)
    out=BASE/'resource-v1.json';j['stage_attempts'][stage]=dict(output=str(out.relative_to(a.ROOT)),reserved_cpu_ns=amount)
    supervisor.atomic_json(JOURNAL,j)
    r=supervisor.run(dict(stage=stage,reserve_cpu_seconds=144,output=str(out),log=str(out)+'.log',journal=str(JOURNAL),
        lock=str(a.ROOT/'artifacts/lp-cpu-admission.lock'),slots=4,declared_memory_bytes=4<<30,
        rss_stop_bytes=6<<30,address_space_bytes=0,sources=[str(a.ROOT/'tools/lp_tensor_expanded_instruction_review.py')],
        bootstrap=False,show_log=True,max_gap_ns=100_000_000,
        command=[sys.executable,str(a.ROOT/'tools/lp_tensor_expanded_instruction_review.py'),'child']))
    if r['status']!='passed':
        j=a.read(JOURNAL);j['scientific_closed']=True;supervisor.atomic_json(JOURNAL,j)
    print(json.dumps(dict(status=r['status'],charged_cpu_ns=r['charged_cpu_ns'])))
    return 0 if r['status']=='passed' else 1


if __name__=='__main__':
    if sys.argv[1]=='initialize':initialize()
    elif sys.argv[1]=='child':child()
    elif sys.argv[1]=='run':raise SystemExit(run())
    else:raise SystemExit('unknown action')
