"""Single compile-only inventory for wider Tensor products and fused updates."""
import json
import re
import subprocess
import sys
import time

import lp_cpu_admission as supervisor
import lp_tensor_expanded_authority as a
import lp_tensor_expanded_recovery as recovery
import lp_tensor_expanded_model_admission as models
import lp_tensor_expanded_build as primitive

BASE=a.BASE/'product-build-v1'
JOURNAL=BASE/'cpu-journal-v10.json'
SOURCE=primitive.SOURCE
NAMES=['xe_int8_main','xe_fp16_main','xe_bf16_main','xe_simt_main','xe_pack64','xe_primal_update','xe_dual_update']
SOURCES=[SOURCE/p for p in ['expanded_products.cu','expanded_updates.cuh','expanded_compact_helpers.h','expanded_fast.h','expanded_storage.h']]
SOURCES.append(a.ROOT/'cuda/lp_pdhg_tensor_warp32/fragment_layout.h')


def initialize():
    recovery.preservation()
    proof=a.read(a.DATA/'cpu-model-admission-v1.json')
    a.require(proof['status']=='passed' and not proof['missing_required'],'CPU model admission failed')
    j=a.read(models.JOURNAL)
    a.require(not j['failed'] and j['active'] is None,'model stage incomplete')
    a.require(j['stages']['cpu_models']['cap_cpu_ns']-j['stages']['cpu_models']['charged_cpu_ns']>=800*a.NS,'unused native funds exhausted')
    j['stages']['cpu_models']['cap_cpu_ns']-=800*a.NS
    j['stages']['products_compile']=dict(cap_cpu_ns=800*a.NS,charged_cpu_ns=0)
    j['stages']['implementation']['charged_cpu_ns']+=16*a.NS
    auth=a.DATA/'product-build-authorization-v1.json'
    a.put(auth,dict(status='accepted',authorization='User-authorized continuation and unused-budget reallocation.',
        transfer=dict(source='cpu_models',target='products_compile',cpu_seconds=800),
        prior_journal=a.ref(models.JOURNAL),model_admission=a.ref(a.DATA/'cpu-model-admission-v1.json'),
        sources=[a.ref(p) for p in SOURCES],implementation_bookkeeping_cpu_seconds=16,
        work_wall_seconds=198,compile_timeout_seconds=180,register_limit=128,spill_bytes_limit=0,
        full_candidate_inventory=False,passed_checks_rerun=False,gpu_seconds=0))
    j['runs'].append(dict(stage='implementation',charged_cpu_ns=16*a.NS,status='conservative_cuda_source_bookkeeping',output=str(auth)))
    j.update(identity='gpup-tensor-expanded-product-build-journal-v10',continuation_authorization=a.ref(auth),
        prior_stage_journal=a.ref(models.JOURNAL))
    a.put(JOURNAL,j)
    for p in SOURCES:
        dst=BASE/'source'/p.relative_to(a.ROOT);dst.parent.mkdir(parents=True,exist_ok=True);dst.write_bytes(p.read_bytes())
    path=a.ROOT/'state/active-task.md';first,rest=path.read_text().split('\n',1)
    path.write_text(first+'\n\n'+'''## GPUP-8 CPU matrix passes; wider CUDA component inventory (2026-10-24)

All five new recovery/controller tests pass. All 48 CPU cells are accounted for,
including eight retained tuned controls, 24 layout refusals and 16 new endpoint
verifications. All twelve required dense cells admit useful/eligible 400-update
trajectories; scaling-256's expected matched-control refusal remains. The CPU
stage charges 924.347221328 seconds. Preserve all source/binary/endpoint receipts.

Continue to one compile-only module for 8x10/14x16 Tensor main products, separate
u64 magnitudes/signs, Expansion64 reconstruction, warp-local packing and fused
primal/dual updates. Transfer 800 unused CPU-model seconds to compilation; charge
16 implementation seconds for source construction. Require intended Tensor
instructions, <=128 registers and zero spills. This is still a partial inventory:
residual/enclosure integration, complete CUDA executor and device acceptance
remain gated. Reuse every passed check/profile and existing primitive image.
Active journal: artifacts/gpup-tensor-expanded-v1/product-build-v1/cpu-journal-v10.json.
No GPU work, additional resources or changed completion criterion.

'''+rest.lstrip('\n'))


def child():
    image=BASE/'expanded_products.cubin';a.require(not image.exists(),'duplicate image attempt')
    keep=BASE/'nvcc-kept';keep.mkdir()
    command=['/usr/local/cuda/bin/nvcc','--cubin','-arch=sm_120','-O3','-lineinfo',
        '-fmad=false','-ftz=false','-Xptxas=-v','--keep','--keep-dir',str(keep),
        '-o',str(image),str(SOURCE/'expanded_products.cu')]
    started=time.monotonic_ns()
    p=subprocess.run(command,capture_output=True,text=True,timeout=180)
    (BASE/'compile.stdout').write_text(p.stdout);(BASE/'compile.stderr').write_text(p.stderr)
    record=dict(identity='gpup-tensor-expanded-product-inventory-v1',status='refused',command=command,
        returncode=p.returncode,elapsed_ns=time.monotonic_ns()-started,sources=[a.ref(p) for p in SOURCES],
        stdout=a.ref(BASE/'compile.stdout'),stderr=a.ref(BASE/'compile.stderr'),
        complete_candidate_inventory=False,gpu_seconds=0,limits=dict(registers=128,spill_bytes=0))
    if p.returncode:
        record['reason']='compiler failure';a.put(a.DATA/'product-inventory-v1.json',record)
        raise ValueError('product module compilation failed')
    resources=[]
    for section in p.stderr.split("ptxas info    : Compiling entry function '")[1:]:
        name=section.split("'",1)[0]
        registers=re.search(r'Used (\d+) registers',section)
        memory=re.search(r'(\d+) bytes stack frame, (\d+) bytes spill stores, (\d+) bytes spill loads',section)
        a.require(registers and memory,'missing resources: '+name)
        resources.append(dict(entry=name,registers=int(registers.group(1)),stack_bytes=int(memory.group(1)),
            spill_store_bytes=int(memory.group(2)),spill_load_bytes=int(memory.group(3))))
    a.require(sorted(r['entry'] for r in resources)==sorted(NAMES),'entry-point inventory differs')
    for flag,name in [('--dump-sass','product.sass'),('--dump-resource-usage','product.resources')]:
        result=subprocess.check_output(['/usr/local/cuda/bin/cuobjdump',flag,str(image)],text=True,timeout=10)
        (BASE/name).write_text(result)
    ptxs=list(keep.glob('*.ptx'));a.require(len(ptxs)==1,'ambiguous PTX')
    ptx=ptxs[0].read_text();sass=(BASE/'product.sass').read_text()
    tensor={}
    for name in NAMES[:3]:
        body=sass.split('Function : '+name,1)[1].split('Function :',1)[0]
        tensor[name]=bool(re.search(r'\b[HI]MMA',body))
    forbidden=bool(re.search(r'\b(?:add|sub|mul|fma|div)\.[^;\n]*f64|\b\w+\.ftz\.',ptx))
    eligible=all(tensor.values()) and not forbidden and all(r['registers']<=128 and
        r['spill_store_bytes']==0 and r['spill_load_bytes']==0 for r in resources)
    record.update(status='passed' if eligible else 'refused',resources=resources,tensor_instructions=tensor,
        forbidden_fp64_or_ftz=forbidden,image=a.ref(image),ptx=a.ref(ptxs[0]),sass=a.ref(BASE/'product.sass'),
        resource_dump=a.ref(BASE/'product.resources'),
        planned_mma_per_tile_product=dict(int8=32,fp16=64,bf16=112),execution_counter_validation_pending=True,
        reason=None if eligible else 'unchanged register/spill/instruction gate refused')
    a.put(a.DATA/'product-inventory-v1.json',record)
    print(json.dumps(record),flush=True)
    a.require(eligible,'wider CUDA module failed unchanged resource/instruction admission')


def run():
    recovery.preservation()
    for item in a.read(models.BASE/'source-manifest.json')['sources']:a.checked(item)
    a.checked(a.read(a.DATA/'cpu-model-admission-v1.json')['binary'])
    j=a.read(JOURNAL);stage='products_compile';amount=800*a.NS
    a.stage_admission(j,stage,amount)
    out=BASE/'resource-v1.json'
    j['stage_attempts'][stage]=dict(output=str(out.relative_to(a.ROOT)),reserved_cpu_ns=amount)
    supervisor.atomic_json(JOURNAL,j)
    r=supervisor.run(dict(stage=stage,reserve_cpu_seconds=800,output=str(out),log=str(out)+'.log',
        journal=str(JOURNAL),lock=str(a.ROOT/'artifacts/lp-cpu-admission.lock'),slots=4,
        declared_memory_bytes=4<<30,rss_stop_bytes=6<<30,address_space_bytes=0,
        sources=list(map(str,[*SOURCES,a.ROOT/'tools/lp_tensor_expanded_products_build.py'])),
        bootstrap=False,show_log=True,max_gap_ns=100_000_000,
        command=[sys.executable,str(a.ROOT/'tools/lp_tensor_expanded_products_build.py'),'child']))
    if r['status']!='passed':
        j=a.read(JOURNAL);j['scientific_closed']=True;supervisor.atomic_json(JOURNAL,j)
    print(json.dumps(dict(status=r['status'],charged_cpu_ns=r['charged_cpu_ns'])))
    return 0 if r['status']=='passed' else 1


if __name__=='__main__':
    if sys.argv[1]=='initialize':initialize()
    elif sys.argv[1]=='child':child()
    elif sys.argv[1]=='run':raise SystemExit(run())
    else:raise SystemExit('unknown action')
