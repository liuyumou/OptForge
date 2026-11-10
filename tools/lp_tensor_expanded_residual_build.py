"""One compile-only residual reconstruction inventory; no device execution."""
import json
import re
import subprocess
import sys
import time

import lp_cpu_admission as supervisor
import lp_tensor_expanded_authority as a
import lp_tensor_expanded_recovery as recovery
import lp_tensor_expanded_instruction_review as review
import lp_tensor_expanded_model_admission as models
import lp_tensor_expanded_build as primitive

BASE=a.BASE/'residual-build-v1'
JOURNAL=BASE/'cpu-journal-v12.json'
SOURCE=primitive.SOURCE
NAMES=['xe_abs_blocks','xe_abs_finish','xe_reconstruct']
SOURCES=[SOURCE/p for p in ['expanded_reconstruct.cu','expanded_compact_helpers.h','expanded_fast.h','expanded_storage.h']]


def initialize():
    recovery.preservation()
    a.require(a.read(a.DATA/'product-inventory-reviewed-v2.json')['status']=='passed','product inventory missing')
    j=a.read(review.JOURNAL)
    a.require(not j['failed'] and j['active'] is None,'prior stage incomplete')
    a.require(j['stages']['implementation']['cap_cpu_ns']-j['stages']['implementation']['charged_cpu_ns']>=1216*a.NS,'unused funds exhausted')
    j['stages']['implementation']['cap_cpu_ns']-=1200*a.NS
    j['stages']['residual_compile']=dict(cap_cpu_ns=1200*a.NS,charged_cpu_ns=0)
    j['stages']['implementation']['charged_cpu_ns']+=16*a.NS
    auth=a.DATA/'residual-build-authorization-v1.json'
    a.put(auth,dict(status='accepted',authorization='User-authorized continuation and unused-budget reallocation.',
        transfer=dict(source='implementation',target='residual_compile',cpu_seconds=1200),
        prior_journal=a.ref(review.JOURNAL),sources=[a.ref(p) for p in SOURCES],
        implementation_bookkeeping_cpu_seconds=16,work_wall_seconds=298,compile_timeout_seconds=280,
        register_limit=128,spill_bytes_limit=0,full_candidate_inventory=False,passed_checks_rerun=False,gpu_seconds=0,
        fp64_operations='Outward error/magnitude metadata only; product iterates remain Expansion64.'))
    j['runs'].append(dict(stage='implementation',charged_cpu_ns=16*a.NS,status='conservative_cuda_source_bookkeeping',output=str(auth)))
    j.update(identity='gpup-tensor-expanded-residual-build-journal-v12',continuation_authorization=a.ref(auth),
        prior_stage_journal=a.ref(review.JOURNAL))
    a.put(JOURNAL,j)
    for p in SOURCES:
        dst=BASE/'source'/p.relative_to(a.ROOT);dst.parent.mkdir(parents=True,exist_ok=True);dst.write_bytes(p.read_bytes())


def child():
    image=BASE/'expanded_reconstruct.cubin';a.require(not image.exists(),'duplicate image attempt')
    keep=BASE/'nvcc-kept';keep.mkdir()
    command=['/usr/local/cuda/bin/nvcc','--cubin','-arch=sm_120','-O3','-lineinfo',
        '-fmad=false','-ftz=false','-Xptxas=-v','--keep','--keep-dir',str(keep),
        '-o',str(image),str(SOURCE/'expanded_reconstruct.cu')]
    started=time.monotonic_ns()
    p=subprocess.run(command,capture_output=True,text=True,timeout=280)
    (BASE/'compile.stdout').write_text(p.stdout);(BASE/'compile.stderr').write_text(p.stderr)
    record=dict(identity='gpup-tensor-expanded-residual-inventory-v1',status='refused',command=command,
        returncode=p.returncode,elapsed_ns=time.monotonic_ns()-started,sources=[a.ref(p) for p in SOURCES],
        stdout=a.ref(BASE/'compile.stdout'),stderr=a.ref(BASE/'compile.stderr'),
        complete_candidate_inventory=False,gpu_seconds=0,limits=dict(registers=128,spill_bytes=0))
    if p.returncode:
        record['reason']='compiler failure';a.put(a.DATA/'residual-inventory-v1.json',record)
        raise ValueError('residual module compilation failed')
    resources=[]
    for section in p.stderr.split("ptxas info    : Compiling entry function '")[1:]:
        name=section.split("'",1)[0]
        registers=re.search(r'Used (\d+) registers',section)
        memory=re.search(r'(\d+) bytes stack frame, (\d+) bytes spill stores, (\d+) bytes spill loads',section)
        a.require(registers and memory,'missing resources: '+name)
        resources.append(dict(entry=name,registers=int(registers.group(1)),stack_bytes=int(memory.group(1)),
            spill_store_bytes=int(memory.group(2)),spill_load_bytes=int(memory.group(3))))
    a.require(sorted(r['entry'] for r in resources)==sorted(NAMES),'entry-point inventory differs')
    for flag,name in [('--dump-sass','residual.sass'),('--dump-resource-usage','residual.resources')]:
        result=subprocess.check_output(['/usr/local/cuda/bin/cuobjdump',flag,str(image)],text=True,timeout=15)
        (BASE/name).write_text(result)
    ptxs=list(keep.glob('*.ptx'));a.require(len(ptxs)==1,'ambiguous PTX')
    instructions=list(review.instructions(ptxs[0].read_text()))
    ftz=[r for r in instructions if 'ftz' in r['opcode'].split('.')]
    eligible=not ftz and all(r['registers']<=128 and r['spill_store_bytes']==0 and r['spill_load_bytes']==0 for r in resources)
    record.update(status='passed' if eligible else 'refused',resources=resources,
        ftz_instructions=ftz,image=a.ref(image),ptx=a.ref(ptxs[0]),sass=a.ref(BASE/'residual.sass'),
        resource_dump=a.ref(BASE/'residual.resources'),
        fp64_metadata_arithmetic=True,device_differential_validation_pending=True,
        reason=None if eligible else 'unchanged register/spill/rounding gate refused')
    a.put(a.DATA/'residual-inventory-v1.json',record)
    print(json.dumps(record),flush=True)
    a.require(eligible,'residual CUDA module failed unchanged resource/rounding admission')


def run():
    recovery.preservation()
    for item in a.read(models.BASE/'source-manifest.json')['sources']:a.checked(item)
    j=a.read(JOURNAL);stage='residual_compile';amount=1200*a.NS
    a.stage_admission(j,stage,amount)
    out=BASE/'resource-v1.json'
    j['stage_attempts'][stage]=dict(output=str(out.relative_to(a.ROOT)),reserved_cpu_ns=amount)
    supervisor.atomic_json(JOURNAL,j)
    r=supervisor.run(dict(stage=stage,reserve_cpu_seconds=1200,output=str(out),log=str(out)+'.log',
        journal=str(JOURNAL),lock=str(a.ROOT/'artifacts/lp-cpu-admission.lock'),slots=4,
        declared_memory_bytes=4<<30,rss_stop_bytes=6<<30,address_space_bytes=0,
        sources=list(map(str,[*SOURCES,a.ROOT/'tools/lp_tensor_expanded_residual_build.py'])),
        bootstrap=False,show_log=True,max_gap_ns=100_000_000,
        command=[sys.executable,str(a.ROOT/'tools/lp_tensor_expanded_residual_build.py'),'child']))
    if r['status']!='passed':
        j=a.read(JOURNAL);j['scientific_closed']=True;supervisor.atomic_json(JOURNAL,j)
    print(json.dumps(dict(status=r['status'],charged_cpu_ns=r['charged_cpu_ns'])))
    return 0 if r['status']=='passed' else 1


if __name__=='__main__':
    if sys.argv[1]=='initialize':initialize()
    elif sys.argv[1]=='child':child()
    elif sys.argv[1]=='run':raise SystemExit(run())
    else:raise SystemExit('unknown action')
