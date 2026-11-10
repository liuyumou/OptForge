"""One bounded artifact-adapter admission and immutable expanded-study freeze."""
import copy
import json
from pathlib import Path
import shutil
import subprocess
import sys

import lp_cpu_admission as supervisor
import lp_tensor_expanded_authority as a
import lp_tensor_expanded_study as s
import lp_tensor_expanded_telemetry_build as previous

def initialize():
    previous.recovery.preservation();j=a.read(previous.JOURNAL)
    a.require(not j['failed'] and j['active'] is None,'native gate not settled')
    a.require(j['stages']['implementation']['cap_cpu_ns']-j['stages']['implementation']['charged_cpu_ns']>=416*a.NS,'unused implementation funds exhausted')
    j['stages']['implementation']['cap_cpu_ns']-=400*a.NS
    j['stages']['implementation']['charged_cpu_ns']+=16*a.NS
    j['stages']['study_adapter']=dict(cap_cpu_ns=400*a.NS,charged_cpu_ns=0)
    auth=a.DATA/'study-continuation-authorization-v1.json'
    a.put(auth,dict(status='accepted',authorization='User authorizes unused-budget transfers and necessary harness corrections; approved ADR-0046 scientific attempt continues once.',
        prior_journal=a.ref(previous.JOURNAL),transfer=dict(source='implementation',target='study_adapter',cpu_seconds=400),
        added_cpu_seconds=0,acceptance_cpu_seconds=4000,profiles_cpu_seconds=3200,timings_cpu_seconds=6400,
        completion_criteria_changed=False,passed_checks_rerun=False,passed_profiles_rerun=False))
    j['runs'].append(dict(stage='implementation',charged_cpu_ns=16*a.NS,status='conservative_adapter_bookkeeping',output=str(auth)))
    j.update(identity='gpup-tensor-expanded-continuation-journal-v18',prior_stage_journal=a.ref(previous.JOURNAL),continuation_authorization=a.ref(auth))
    a.put(s.JOURNAL,j)
    path=a.ROOT/'state/active-task.md';first,rest=path.read_text().split('\n',1)
    path.write_text(first+'\n\n## GPUP-8 corrected proof passes; freeze and bounded device continuation (2026-10-24)\n\nThe corrected 7376-case proof, new arithmetic/window checks, all twelve useful\n400-update dense CPU configurations, four zero-spill CUDA modules and native\nexecutor acceptance pass. Reuse every passed receipt and compiled image.\nTransfer 400 unused implementation CPU seconds to artifact-adapter acceptance,\nwith 16 CPU seconds for bookkeeping. Active journal is artifacts/\ngpup-tensor-expanded-v1/continuation-v1/cpu-journal-v18.json. Freeze all 76 study\ncells, six device jobs and exact evidence bindings before device observations.\nThen run acceptance, profiles and conditional timings in isolated existing\n4000/3200/6400 CPU reservations. Preserve the 17412-event GPU prefix, 1760-second\ncohort cap, all deadlines and completion criteria. No old check/profile rerun.\n\n'+rest.lstrip('\n'))

def retained_pairs():
    rows=[]
    for row in a.read(s.OLD.parent/'deadline-recovery-v1/project-composite.json')['rows']:
        if row['configuration']!='tuned-fp64':continue
        for key in ['request','endpoint','replay']:a.checked(row[key])
        request=a.read(a.checked(row['request']))
        a.require(request['layout']=='original_tuned' and request['horizon']==64,'retained control input differs')
        a.require(request['executable_sha256']==a.ref(s.OLD/'lp_precision_tensor_cost')['sha256'],'retained control executable mismatch')
        a.require(request['code_object_sha256']==a.ref(s.OLD/'lp_pdhg_tensor_cost.cubin')['sha256'],'retained control image mismatch')
        for role,item in row['verification'].items():
            receipt=a.read(a.checked(item));a.require(receipt['status']=='passed','control receipt failed')
            for field in ['endpoint','executable','model','request']:a.checked(receipt['binding'][field])
            a.require(receipt['binding']['endpoint']==row['endpoint' if role=='endpoint' else 'replay'],'control endpoint receipt mismatch')
        rows.append(row)
    a.require(len(rows)==2,'two control pairs required');return rows

def freeze():
    previous.recovery.preservation();s.D.mkdir(exist_ok=False)
    acceptance=a.read(a.DATA/'executor-native-acceptance-v3.json');a.require(acceptance['status']=='passed','native not passed')
    manifest=a.read(a.checked(acceptance['source_manifest']))
    for item in manifest['sources']:a.checked(item)
    binary=a.checked(acceptance['binary']);shutil.copy2(binary,s.D/'lp_tensor_expanded')
    images=[s.OLD/'lp_pdhg_tensor_cost.cubin',a.BASE/'primitive-build-v1/expanded_primitives.cubin',
        a.BASE/'product-build-v1/expanded_products.cubin',a.BASE/'residual-build-v1/expanded_reconstruct.cubin',a.BASE/'guard-build-v1/expanded_guard.cubin']
    old_images=a.read(s.OLD/'code-objects.json')
    for name,digest in old_images.items():
        a.require(a.ref(s.OLD/name)['sha256']==digest,'retained image differs');shutil.copy2(s.OLD/name,s.D/name)
    shutil.copy2(s.OLD/'optimizer',s.D/'optimizer')
    a.put(s.D/'code-objects.json',old_images)
    a.put(s.D/'execution.json',dict(identity='gpup-tensor-expanded-v1',binary=a.ref(s.D/'lp_tensor_expanded'),
        source_tree_sha256=manifest['source_tree_sha256'],images=[a.ref(p) for p in images],
        control_identity=a.read(s.OLD/'execution.json'),native_acceptance=a.ref(a.DATA/'executor-native-acceptance-v3.json')))
    v=a.read(s.OLD/'campaign.json');old_roster=list(s.legacy.jobs(v));v=copy.deepcopy(v)
    v.update(id=s.PREFIX,output=str(s.D.relative_to(a.ROOT)),acceptance_output=str(s.D.relative_to(a.ROOT)),
        allocated_gpu_seconds=1760,combined_cap_seconds=1760,cpu_cap_seconds=31600,
        prior_events=a.PREFIX_EVENTS,prior_ledger_sha256=a.PREFIX_SHA256,prior_gpu_ns=a.authority()['prior_campaign_gpu_ns'],
        decision=a.ref(a.ROOT/'docs/decisions/ADR-0046-expanded-audit-window-state.md'))
    for c in v['configurations']:
        if c['backend']!='cuda-lp-tuned':c['backend']='lp-tensor-expanded-v1'
    for key,cap in [('accept',450),('profile',320),('timing',990)]:v['categories'][key]['seconds']=cap
    a.put(s.D/'campaign.json',v)
    roster=[]
    for old in old_roster:
        j=copy.deepcopy(old);j['id']=j['id'].replace('gpup-tensor-warp32-v1-profile-',s.PREFIX+'-profiles-').replace('gpup-tensor-warp32-v1-timing-',s.PREFIX+'-timings-')
        if j['configuration']['backend']!='cuda-lp-tuned':j['configuration']['backend']='lp-tensor-expanded-v1'
        roster.append(j)
    a.put(s.D/'roster.json',roster)
    a.require(len(roster)==76 and sum(s.legacy.effective(v,j)[2]+6 for j in roster if j['kind']=='profile')==320 and sum(s.legacy.effective(v,j)[2]+6 for j in roster if j['kind']=='timing')==990,'roster changed')
    a.put(s.D/'forecast-rule.json',s.screen.RULE);a.put(s.D/'resource-rule.json',s.screen.RESOURCE_RULE)
    a.put(s.D/'timing-budget-amendment.json',dict(status='accepted',previous_gpu_seconds=300,active_gpu_seconds=990,
        estimator=a.ref(a.ROOT/'tools/lp_tensor_warp32_screen.py'),multiplier=1.25,admission_tail_seconds=120,
        authorization=a.ref(a.DATA/'authorization-v1.json'),inputs_changed=False))
    for j in roster:
        request,docs=s.inputs(j);docs[j['id']+'.frozen.json']=request
        for name,doc in docs.items():a.put(s.D/name,doc)
    for name in v['timing_instances']:
        model=a.checked(s.legacy.instances(v)[name]['model'])
        for c in v['configurations']:
            if c['id']!='tuned-fp64':a.put(s.D/(name+'-'+c['id']+'.acceptance-request.json'),s.make_request(c,model,64,16))
    model=a.checked(s.legacy.instances(v)[v['timing_instances'][0]]['model'])
    a.put(s.D/'acceptance-scope.request.json',s.make_request(v['configurations'][0],model,64,16,False))
    scalar=a.read(a.DATA/'independent-proof-v2.json')['scalar'];a.put(s.D/'scalar-fixture.json',{k:scalar[k] for k in ['input','output']})
    for name,seconds in s.SCOPES:
        key=s.PREFIX+'-acceptance-'+name
        command=[s.D/'lp_tensor_expanded','device-checks',name if name in ['primitive','project'] else 'sanitizer',s.D/'scalar-fixture.json',s.D/'acceptance-scope.request.json',s.D/(key+'.numerical.json')]
        if name=='project':command=[sys.executable,a.ROOT/'tools/lp_tensor_expanded_study.py','project-child']
        elif name!='primitive':command=['/usr/local/cuda/bin/compute-sanitizer','--tool',name,'--error-exitcode','86','--target-processes','all',*command]
        a.put(s.D/(key+'.frozen.json'),s.worker(key,s.numeric(command),seconds))
    old_regular=s.OLD.parent/'acceptance-v1'/ 'gpup-tensor-warp32-v1-accept-regular.worker.json'
    a.require(a.read(old_regular)['reason']=='completed' and a.read(old_regular)['returncode']==0,'ordinary suite not passed')
    proof_names=['independent-proof-v2','rust-scalar-acceptance-v1','rust-window-acceptance-v1','cpu-model-admission-v1','primitive-inventory-v1','product-inventory-reviewed-v2','residual-inventory-v1','guard-inventory-v1','launch-abi-acceptance-v1','executor-native-acceptance-v3']
    reused=[a.ref(a.DATA/(n+'.json')) for n in proof_names]
    a.put(s.D/'acceptance-manifest.json',dict(identity='expanded-acceptance-manifest-v1',retained_checks=reused,
        ordinary_suite=a.ref(old_regular),retained_control_pairs=retained_pairs(),
        native_product_scenarios=dict(pairs=168,retained_image=a.ref(images[0]),source=a.ref(a.ROOT/'crates/optimizer-lp-cuda/src/tensor_cost.rs'),
            receipt=a.ref(s.OLD.parent/'acceptance-v1/project/tensor.stdout'),reason='Native/segmented kernels and their original launch implementation remain exact; new reference-buffer binding is independently checked by changed-window acceptance.'),
        new_product_pairs=112,new_controller_pairs=5,new_window_reference_pairs=20,new_fixed_work_pairs=10,
        instrumentation='Exclusive host-wall phases and CUDA-event kernel durations are distinct. Normalization inside fused products/updates is included in that kernel duration, without an invented separate time.',
        historical_profiles_rerun=False))
    files=set(p for p in s.D.iterdir() if p.is_file())
    files.update(a.ROOT/item['path'] for item in manifest['sources']);files.update(images)
    files.update(a.ROOT/item['path'] for item in reused)
    files.update(a.ROOT/'tools'/n for n in ['lp_tensor_expanded_study.py','lp_tensor_expanded_freeze.py','lp_tensor_expanded_authority.py','lp_cpu_admission.py','lp_tensor_cost_exec.py','gpu_job.sh','lp_supervise.py','lp_protocol.py','lp_tensor_warp32_screen.py','report_lp_tensor_warp32.py','benchmark_lp_tensor_warp32.py','benchmark_lp_refine.py','benchmark_lp_adaptive_cost.py'])
    files.update(a.checked(j['instance']['model']) for j in roster)
    files.update(a.checked(scalar[k]) for k in ['input','output'])
    a.put(s.D/'freeze.json',dict(identity='expanded-study-freeze-v1',files=[a.ref(p) for p in sorted(files)],
        numerical_changes_after_observation='refuse',ledger_prefix=dict(events=a.PREFIX_EVENTS,sha256=a.PREFIX_SHA256)))
    s.frozen()

def child():
    freeze()
    p=subprocess.run([sys.executable,'-m','unittest','discover','-s','tests/integration','-p','test_lp_tensor_expanded_study.py','-v'],cwd=a.ROOT,capture_output=True,text=True,timeout=50)
    (s.BASE/'adapter-tests.stdout').write_text(p.stdout);(s.BASE/'adapter-tests.stderr').write_text(p.stderr);print(p.stdout+p.stderr,flush=True)
    a.require(p.returncode==0,'new study adapter tests failed')
    a.put(a.DATA/'study-adapter-acceptance-v1.json',dict(status='passed',freeze=a.ref(s.D/'freeze.json'),stdout=a.ref(s.BASE/'adapter-tests.stdout'),stderr=a.ref(s.BASE/'adapter-tests.stderr'),gpu_seconds=0))

def run():
    j=a.read(s.JOURNAL);stage='study_adapter';a.stage_admission(j,stage,400*a.NS);out=s.BASE/'adapter-resource-v1.json'
    j['stage_attempts'][stage]=dict(output=str(out.relative_to(a.ROOT)),reserved_cpu_ns=400*a.NS);supervisor.atomic_json(s.JOURNAL,j)
    r=supervisor.run(dict(stage=stage,reserve_cpu_seconds=400,output=str(out),log=str(out)+'.log',journal=str(s.JOURNAL),lock=str(a.ROOT/'artifacts/lp-cpu-admission.lock'),slots=4,
        declared_memory_bytes=4<<30,rss_stop_bytes=6<<30,address_space_bytes=0,sources=[str(Path(__file__)),str(a.ROOT/'tools/lp_tensor_expanded_study.py')],
        bootstrap=False,show_log=True,max_gap_ns=100_000_000,command=[sys.executable,str(Path(__file__)),'child']))
    print(json.dumps(dict(status=r['status'],charged_cpu_ns=r['charged_cpu_ns'])));return 0 if r['status']=='passed' else 1

if __name__=='__main__':
    if sys.argv[1]=='initialize':initialize()
    elif sys.argv[1]=='child':child()
    elif sys.argv[1]=='run':raise SystemExit(run())
