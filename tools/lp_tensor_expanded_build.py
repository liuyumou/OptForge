"""One compile-only primitive admission, prerequisite to the full candidate build.

The primitive module is reusable as-is by the eventual executor. This inventory
is explicitly partial: no Tensor, window, model, or device acceptance claim.
"""
import json
import re
import subprocess
import sys
import time

import lp_cpu_admission as supervisor
import lp_tensor_expanded_authority as a
import lp_tensor_expanded_recovery as recovery

BASE = a.BASE/'primitive-build-v1'
AUTH = a.DATA/'primitive-build-authorization-v1.json'
JOURNAL = BASE/'cpu-journal-v6.json'
SOURCE = a.ROOT/'cuda/lp_pdhg_tensor_expanded'
ENTRY_POINTS = ['xe_scalar', 'xe_integer_fma', 'xe_project', 'xe_encode64', 'xe_decode64']


def helpers():
    integer = (a.ROOT/'tools/diagnostics/lp_state_integer_probe.cu').read_text()
    compact = (a.ROOT/'tools/diagnostics/lp_state_compact_probe.cu').read_text()
    pieces = [integer.split('__device__ __forceinline__ Wide divide(', 1)[0],
        'using W=unsigned long long;'+integer.split('using W=unsigned long long;',1)[1].split('template<int P> __device__ __forceinline__ Value mul_value',1)[0],
        compact.split('// Right shift',1)[1].split('template<int P> __device__ __forceinline__ void compact_probe',1)[0]]
    # Restore the comment opener consumed by the exact marker extraction.
    pieces[2] = '// Right shift'+pieces[2]
    return '// Generated exact helper sections; see helper-source-v1.json.\n'+''.join(pieces)


def initialize():
    recovery.preservation()
    proof = a.read(a.DATA/'independent-proof-v2.json')
    a.require(proof['status']=='passed', 'proof prerequisite missing')
    old = a.read(recovery.JOURNAL)
    a.require(not old['failed'] and old['active'] is None, 'recovery not successful')
    a.require(old['stages']['native']['charged_cpu_ns']==0, 'native budget already used')
    auth = dict(identity='gpup-tensor-expanded-primitive-build-v1', status='accepted',
        authorization='User authorizes conditional continuation and unused-budget reallocations, 2026-10-24.',
        prior_journal=a.ref(recovery.JOURNAL), proof=a.ref(a.DATA/'independent-proof-v2.json'),
        transfer=dict(source='native', target='primitive_compile', cpu_seconds=800),
        work_wall_seconds=198, compile_timeout_seconds=180, inventory='primitive-module-only',
        numerical_criteria_unchanged=True, gpu_seconds=0,
        resource_limits=dict(max_registers=128, spill_store_bytes=0, spill_load_bytes=0),
        remaining_native_cpu_seconds=4000, retries=0,
        implementation_bookkeeping_cpu_seconds=32)
    a.put(AUTH, auth)
    old['stages']['native']['cap_cpu_ns']-=800*a.NS
    old['stages']['primitive_compile']=dict(cap_cpu_ns=800*a.NS, charged_cpu_ns=0)
    old['stages']['implementation']['charged_cpu_ns']+=32*a.NS
    old['runs'].append(dict(stage='implementation', charged_cpu_ns=32*a.NS,
        status='conservative_source_construction_bookkeeping', output=str(AUTH)))
    old.update(identity='gpup-tensor-expanded-primitive-build-journal-v6',
               continuation_authorization=a.ref(AUTH), prior_stage_journal=a.ref(recovery.JOURNAL))
    a.put(JOURNAL, old)
    path=SOURCE/'expanded_compact_helpers.h'
    a.require(not path.exists(), 'helper source already exists')
    path.write_text(helpers())
    a.put(BASE/'helper-source-v1.json', dict(generated=a.ref(path),
        sources=[a.ref(a.ROOT/'tools/diagnostics/lp_state_integer_probe.cu'),
                 a.ref(a.ROOT/'tools/diagnostics/lp_state_compact_probe.cu')],
        extraction=a.ref(a.ROOT/'tools/lp_tensor_expanded_build.py'),
        arithmetic_body_changes=False, historical_probe_entry_points_excluded=True))
    p=a.ROOT/'state/active-task.md'
    first,rest=p.read_text().split('\n',1)
    p.write_text(first+'\n\n'+'''## GPUP-8 corrected proof passes; primitive CUDA admission (2026-10-24)

The one corrected proof passes 7376 scalar, 1400 conversion, 1400 exact split,
720 component product and 2400 projection cases. The new fixture/harness
preflight passes; the old 28 checks and every historical profile are reused.
Before full solver integration, compile the actual expanded scalar, projection
and boundary-conversion module once. This partial inventory makes no complete
candidate, Tensor, device or model-admission claim. Preserve the exact retained
arithmetic helpers and reuse this module if admitted. Transfer 800 unused native
CPU seconds to its compile reservation (198 work-wall seconds); retain 4000 for
the remaining native inventory. Charge 32 implementation CPU seconds for source
construction/bookkeeping. A failed 128-register/zero-spill gate stops science.

Active journal: artifacts/gpup-tensor-expanded-v1/primitive-build-v1/cpu-journal-v6.json.
No extra CPU/GPU funds, changed criteria, GPU execution or historical rerun.

'''+rest.lstrip('\n'))
    print('Primitive build funded from native allocation; exact helpers preserved.')


def child():
    a.require((SOURCE/'expanded_compact_helpers.h').read_text()==helpers(), 'helper extraction differs')
    image=BASE/'expanded_primitives.cubin'
    a.require(not image.exists(), 'duplicate compile identity')
    keep=BASE/'nvcc-kept';keep.mkdir()
    command=['/usr/local/cuda/bin/nvcc','--cubin','-arch=sm_120','-O3','-lineinfo',
        '-fmad=false','-ftz=false','-Xptxas=-v','--keep','--keep-dir',str(keep),
        '-o',str(image),str(SOURCE/'expanded_primitives.cu')]
    start=time.monotonic_ns()
    result=subprocess.run(command,capture_output=True,text=True,timeout=180)
    for label,text in [('stdout',result.stdout),('stderr',result.stderr)]:
        (BASE/('compile.'+label)).write_text(text)
    receipt=dict(identity='gpup-tensor-expanded-primitive-inventory-v1',
        status='refused', complete_candidate_inventory=False, gpu_seconds=0,
        command=command, returncode=result.returncode, elapsed_ns=time.monotonic_ns()-start,
        stdout=a.ref(BASE/'compile.stdout'), stderr=a.ref(BASE/'compile.stderr'),
        sources=[a.ref(SOURCE/name) for name in ['expanded_compact_helpers.h',
            'expanded_fast.h','expanded_storage.h','expanded_primitives.cu']],
        acceptance_limits=dict(max_registers=128, max_spill_bytes=0))
    if result.returncode!=0:
        receipt['reason']='compiler failure'
        a.put(a.DATA/'primitive-inventory-v1.json',receipt)
        raise RuntimeError('primitive compiler failure; exact status retained')
    records=[]
    for section in result.stderr.split("ptxas info    : Compiling entry function '")[1:]:
        name=section.split("'",1)[0]
        registers=re.search(r'Used (\d+) registers',section)
        memory=re.search(r'(\d+) bytes stack frame, (\d+) bytes spill stores, (\d+) bytes spill loads',section)
        a.require(registers and memory, 'missing compiler resource record: '+name)
        records.append(dict(entry=name,registers=int(registers.group(1)),
            stack_bytes=int(memory.group(1)),spill_store_bytes=int(memory.group(2)),
            spill_load_bytes=int(memory.group(3))))
    a.require(sorted(r['entry'] for r in records)==sorted(ENTRY_POINTS), 'entry-point inventory differs')
    for flag,name in [('--dump-sass','primitive.sass'),('--dump-resource-usage','primitive.resources')]:
        output=subprocess.check_output(['/usr/local/cuda/bin/cuobjdump',flag,str(image)],text=True,timeout=10)
        (BASE/name).write_text(output)
    ptx_paths=list(keep.glob('*.ptx'))
    a.require(len(ptx_paths)==1,'ambiguous PTX inventory')
    ptx=ptx_paths[0].read_text()
    forbidden=bool(re.search(r'\b(?:add|sub|mul|fma|div)\.[^;\n]*f64|\b\w+\.ftz\.',ptx))
    eligible=not forbidden and all(r['registers']<=128 and r['spill_store_bytes']==0 and
                                  r['spill_load_bytes']==0 for r in records)
    receipt.update(status='passed' if eligible else 'refused', resources=records,
        image=a.ref(image),ptx=a.ref(ptx_paths[0]),sass=a.ref(BASE/'primitive.sass'),
        resource_dump=a.ref(BASE/'primitive.resources'),forbidden_fp64_or_ftz=forbidden,
        reason=None if eligible else 'primitive resource/rounding admission failed')
    a.put(a.DATA/'primitive-inventory-v1.json',receipt)
    print(json.dumps(receipt),flush=True)
    a.require(eligible,'primitive exceeds unchanged resource/rounding gate')


def run():
    recovery.preservation()
    a.checked(a.read(AUTH)['proof'])
    j=a.read(JOURNAL);stage='primitive_compile';amount=800*a.NS
    a.stage_admission(j,stage,amount)
    out=BASE/'compile-resource-v1.json'
    j['stage_attempts'][stage]=dict(output=str(out.relative_to(a.ROOT)),reserved_cpu_ns=amount)
    supervisor.atomic_json(JOURNAL,j)
    sources=[a.ROOT/'tools/lp_tensor_expanded_build.py',a.ROOT/'tools/lp_cpu_admission.py']
    sources.extend(SOURCE/name for name in ['expanded_primitives.cu','expanded_storage.h',
                   'expanded_compact_helpers.h','expanded_fast.h'])
    r=supervisor.run(dict(stage=stage,reserve_cpu_seconds=800,output=str(out),log=str(out)+'.log',
        journal=str(JOURNAL),lock=str(a.ROOT/'artifacts/lp-cpu-admission.lock'),slots=4,
        declared_memory_bytes=4<<30,rss_stop_bytes=6<<30,address_space_bytes=0,
        sources=list(map(str,sources)),bootstrap=False,show_log=True,max_gap_ns=100_000_000,
        command=[sys.executable,str(a.ROOT/'tools/lp_tensor_expanded_build.py'),'child']))
    if r['status']!='passed':
        j=a.read(JOURNAL);j['scientific_closed']=True;supervisor.atomic_json(JOURNAL,j)
    print(json.dumps(dict(status=r['status'],charged_cpu_ns=r['charged_cpu_ns'])))
    return 0 if r['status']=='passed' else 1


if __name__=='__main__':
    if sys.argv[1]=='initialize':initialize()
    elif sys.argv[1]=='child':child()
    elif sys.argv[1]=='run':raise SystemExit(run())
    else:raise SystemExit('unknown action')
