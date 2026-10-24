"""Frozen ADR-0046 stage adapter; original forecast/statistics bodies are reused."""
import contextlib
import copy
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

import lp_cpu_admission as supervisor
import lp_tensor_expanded_authority as a
import lp_tensor_expanded_recovery as recovery
import lp_tensor_expanded_telemetry_build as native
import benchmark_lp_tensor_warp32 as legacy
import lp_tensor_warp32_screen as screen
from lp_protocol import Ledger
from benchmark_lp_adaptive_cost import endpoint_shape
from report_lp_tensor_warp32 import gain,profile_eligible,useful_tensor,worker_bounds

ROOT=a.ROOT
BASE=a.BASE/'continuation-v1'
D=a.BASE/'study-v1'
JOURNAL=BASE/'cpu-journal-v18.json'
OLD=ROOT/'artifacts/gpup-tensor-warp32-v1/study-v1'
PREFIX='gpup-tensor-expanded-v1'
STAGES={'acceptance':4000,'profiles':3200,'timings':6400}
SCOPES=[('primitive',84),('project',180),('memcheck',30),('racecheck',50),('initcheck',30),('synccheck',30)]

def value():return a.read(D/'campaign.json')
def identity():return a.read(D/'execution.json')
def jobs(v=None):return a.read(D/'roster.json')
def numeric(command):return [sys.executable,str(ROOT/'tools/lp_tensor_cost_exec.py'),'--memory-bytes',str(2<<30),'--',*map(str,command)]

def preserve_history():
    bridge=a.read(a.BASE/'source-bridge-v1.json');a.checked(bridge['supervisor'])
    snapshots={x['current']:x['preserved'] for x in bridge['prior_mutable']}
    for item in a.read(a.checked(bridge['prior_worktree']))['files']:a.checked(snapshots.get(item['path'],item))
    for item in a.read(ROOT/'artifacts/gpup-tensor-warp32-v1/receipt-recovery-v1/pins.json')['historical_refs']:a.checked(item)
    for item in bridge['retained_arithmetic']:a.checked(item)
    for item in a.read(recovery.BASE/'prior-files.json')['files']:a.checked(item)
    events=a.ledger_events()
    allowed={j['id'] for j in jobs()}|{PREFIX+'-acceptance-'+name for name,_ in SCOPES}
    a.require(all(e['trial_id'] in allowed for e in events[a.PREFIX_EVENTS:]),'unallocated ledger suffix')
    a.aggregate(events)
    return events

def frozen():
    document=a.read(D/'freeze.json')
    for item in document['files']:a.checked(item)
    preserve_history()
    return document

def remaining(stage):
    j=a.read(JOURNAL);active=j['active']
    a.require(not j['failed'] and not j.get('scientific_closed') and active and active['stage']==stage,'inactive CPU stage')
    allowed=set(json.loads(os.environ['LP_CPU_ALLOWED_CPUS']))
    a.require(len(allowed)==4 and os.sched_getaffinity(0)<=allowed,'CPU affinity differs')
    return max(0,active['started_ns']+active['reserved_cpu_ns']//4-2*a.NS-time.monotonic_ns())

class JointLedger(Ledger):
    def __init__(self,stage):
        v=value();self.stage=stage
        super().__init__(a.LEDGER.parent,v['budget_authority']['sha256'],v['phase_gpu_seconds'],cumulative_ns=25202574545061)
    def reserve(self,key,seconds,resource='gpu',phase=None):
        a.require(resource=='gpu','GPU-only ledger adapter')
        a.require(remaining(self.stage)>=(seconds+120)*a.NS,'joint CPU reservation/tail exhausted')
        a.gpu_admission(a.authority(),self.events,self.stage,key,round(seconds*a.NS))
        return super().reserve(key,seconds,resource,a.PHASES[self.stage])

def make_request(c,model,horizon,seconds,diagnostic=None):
    v=value();info=identity();work=480 if horizon in [64,400] else 50000
    return dict(identity='lp-tensor-expanded-v1',model_sha256=a.ref(model)['sha256'],
        source_tree_sha256=info['source_tree_sha256'],executable_sha256=info['binary']['sha256'],
        layout=c['layout'],method=dict(v['lp_settings'],iteration_limit=work),settings=c['settings'],
        options=dict(v['solve'],iteration_limit=work,time_limit_ms=seconds*1000),horizon=horizon,
        images=info['images'],device=v['device'],diagnostic=horizon!=0 if diagnostic is None else diagnostic,
        norm_policy=c.get('norm_policy','disjoint-interval-gram-v1'),audit_policy=c.get('audit_policy','device_ordered_v1'))

def worker(key,command,seconds,directory=D):
    return dict(schema_version=2,gpu_admission_seconds=3,command=list(map(str,command)),directory=str(directory),prefix=key,
        solve_seconds=seconds,cleanup_seconds=2,host_rss_bytes=8<<30,poll_ms=10,output_bytes=32<<20)

def inputs(j):
    v=value();info=identity();key=j['id'];c=j['configuration'];_,_,seconds=legacy.effective(v,j)
    if c['backend']=='cuda-lp-tuned':
        request,docs=legacy.control_inputs(legacy.control_value(v,j),legacy.control_job(v,j),D,info['control_identity'])
        request['command']=request['command'][:2]+numeric(request['command'][2:])
        return request,docs
    model=a.checked(j['instance']['model']);rp=D/(key+'.expanded-request.json');ep=D/(key+'.endpoint.json')
    request=make_request(c,model,2000 if j['kind']=='profile' else 0,seconds)
    return worker(key,numeric([D/'lp_tensor_expanded','solve',model,rp,ep]),seconds),{rp.name:request}

def verification_binding(model,rp,ep,binary):
    return dict(model=a.ref(model),request=a.ref(rp),endpoint=a.ref(ep),binary=a.ref(binary),
        producer_source_tree_sha256=identity()['source_tree_sha256'],reader=a.ref(Path(__file__)))

def verify_new(model,rp,ep,cache,binary=None,control=False,j=None):
    binary=binary or D/'lp_tensor_expanded';binding=verification_binding(model,rp,ep,binary)
    if cache.exists():
        receipt=a.read(cache);a.require(receipt['status']=='passed' and receipt['binding']==binding,'verification cache mismatch');return receipt['assessment']
    started=time.monotonic_ns()
    if control:
        v=value();e=endpoint_shape(ep,'compact-v1');solve,method,_=legacy.effective(v,j)
        a.require(e['model_sha256']==j['instance']['model']['sha256'] and e['record']['options']==solve and e['record']['lp_settings']==method,'control input mismatch')
        a.require(e['requested_backend']=='cuda-lp-tuned' and e['execution']['settings']==j['configuration']['execution'],'control execution mismatch')
        a.require(e['execution']['code_object_sha256']==a.read(D/'code-objects.json')['lp_pdhg_tuned.cubin'],'control image mismatch')
        command=numeric([binary,'lp-study','verify','--model',model,'--model-byte-limit',v['model_byte_limit'],'--evidence',ep])
    else:
        e=a.read(ep);a.require(e['request']==a.read(rp) and e['executor']=='gpu','producer binding mismatch')
        command=numeric([binary,'verify',model,rp,ep])
    process=subprocess.run(command,capture_output=True,text=True,timeout=120)
    stdout=cache.with_suffix('.stdout');stderr=cache.with_suffix('.stderr');stdout.write_text(process.stdout);stderr.write_text(process.stderr)
    a.require(process.returncode==0,'endpoint verification failed: '+process.stderr[:1200])
    a.require(json.loads(process.stdout)==e['assessment'] if control else process.stdout.strip()=='verified','verification output differs')
    a.put(cache,dict(status='passed',binding=binding,assessment=e['assessment'],elapsed_ns=time.monotonic_ns()-started,
        stdout=a.ref(stdout),stderr=a.ref(stderr)))
    return e['assessment']

def verify_cached(v,j,d,info):
    key=j['id'];control=j['configuration']['backend']=='cuda-lp-tuned'
    rp=d/(key+('.frozen.json' if control else '.expanded-request.json'))
    ep=d/(key+'.endpoint.json');cache=d/(key+'.verification.json')
    a.require(cache.exists(),'missing independent verification receipt')
    trial=a.read(d/(key+'.trial.json'))
    a.require(trial['verification']==a.ref(cache),'receipt link differs')
    return verify_new(a.checked(j['instance']['model']),rp,ep,cache,d/('optimizer' if control else 'lp_tensor_expanded'),control,j)

@contextlib.contextmanager
def inherited_readers():
    saved=(legacy.jobs,legacy.verify_endpoint)
    legacy.jobs=jobs;legacy.verify_endpoint=verify_cached
    try:yield
    finally:legacy.jobs,legacy.verify_endpoint=saved

def execute_worker(ledger,key,request):
    frozen();path=D/(key+'.request.json');a.require(not path.exists() and key not in ledger.attempted(),'duplicate identity')
    a.require(a.read(D/(key+'.frozen.json'))==request,'worker freeze mismatch')
    reservation=ledger.reserve(key,request['solve_seconds']+6)
    a.put(path,request)
    process=subprocess.Popen(['bash',str(ROOT/'tools/gpu_job.sh'),value()['device'],'--lp-study-request',str(path)],pass_fds=(ledger.lock.fileno(),))
    try:process.wait(timeout=request['solve_seconds']+130)
    finally:
        if process.poll() is None:process.terminate();process.wait(timeout=3)
        wp=D/(key+'.worker.json');result=a.read(wp) if wp.exists() else None
        charge=result['leased_ns'] if result else reservation['reserved_ns'];ledger.settle(reservation,charge)
    a.require(result is not None,'missing worker accounting')
    worker_bounds(result,reservation['reserved_ns'],value()['device'])
    a.require(process.returncode==0 and result['returncode']==0 and result['reason']=='completed','GPU worker failed: '+str(result.get('reason')))
    return result,charge

def project_child():
    info=identity();directory=D/'acceptance-project';directory.mkdir(exist_ok=False)
    scope=D/'acceptance-scope.request.json'
    command=numeric([D/'lp_tensor_expanded','device-checks','project',D/'scalar-fixture.json',scope,directory/'differential.json'])
    p=subprocess.run(command,capture_output=True,text=True,timeout=100)
    (directory/'differential.stdout').write_text(p.stdout);(directory/'differential.stderr').write_text(p.stderr)
    a.require(p.returncode==0,'new device differential failure: '+p.stderr[:1600])
    rows=[]
    retained=a.read(ROOT/'artifacts/gpup-tensor-warp32-v1/deadline-recovery-v1/project-composite.json')
    for name in value()['timing_instances']:
        for c in value()['configurations']:
            if c['id']=='tuned-fp64':
                row=next(r for r in retained['rows'] if r['instance']==name and r['configuration']==c['id'])
                for key in ['endpoint','replay']:a.checked(row[key])
                for item in row['verification'].values():a.checked(item)
                rows.append(dict(row,evidence_reused=True));continue
            model=a.checked(legacy.instances(value())[name]['model']);stem=name+'-'+c['id'];rp=D/(stem+'.acceptance-request.json')
            ep=directory/(stem+'.endpoint.json');replay=directory/(stem+'.replay.json')
            for action,target in [('solve',ep),('replay',replay)]:
                command=[D/'lp_tensor_expanded',action,model,rp]+([ep,target] if action=='replay' else [target])
                p=subprocess.run(numeric(command),capture_output=True,text=True,timeout=40)
                (directory/(stem+'.'+action+'.stdout')).write_text(p.stdout);(directory/(stem+'.'+action+'.stderr')).write_text(p.stderr)
                a.require(p.returncode==0,'fixed-work '+action+' failed: '+p.stderr[:1600])
                verify_new(model,rp,target,directory/(stem+'.'+action+'.verification.json'))
                e=a.read(target);a.require(e['outcome']['core']['stop']=='work_horizon' and e['outcome']['core']['iterations']==64,'fixed-work horizon failed')
            rows.append(dict(instance=name,configuration=c['id'],status='passed',endpoint=a.ref(ep),replay=a.ref(replay),
                verification=dict(endpoint=a.ref(directory/(stem+'.solve.verification.json')),replay=a.ref(directory/(stem+'.replay.verification.json'))),evidence_reused=False))
            if c['id']=='matched-fp64' and name==value()['timing_instances'][0]:
                trace=directory/(stem+'.cpu-controller.json')
                p=subprocess.run(numeric([D/'lp_tensor_expanded','trace-cpu',model,rp,trace]),capture_output=True,text=True,timeout=40)
                (directory/'matched-controller.stderr').write_text(p.stderr)
                a.require(p.returncode==0,'matched controller CPU authority failed')
                a.require(a.read(trace)['outcome']==a.read(ep)['outcome'],'matched FP64 controller differs')
    a.require(len(rows)==12,'fixed-work roster incomplete')
    a.put(directory/'acceptance.json',dict(status='passed',rows=rows,differential=a.ref(directory/'differential.json')))

def acceptance():
    with JointLedger('acceptance') as ledger:
        for name,_ in SCOPES:
            key=PREFIX+'-acceptance-'+name;request=a.read(D/(key+'.frozen.json'))
            result,charge=execute_worker(ledger,key,request)
            if name in ['memcheck','racecheck','initcheck','synccheck']:
                text=(D/(key+'.stdout')).read_text()+(D/(key+'.stderr')).read_text()
                a.require('ERROR SUMMARY: 0 errors' in text or 'RACECHECK SUMMARY: 0 hazards' in text,'missing sanitizer success')
            a.put(D/(key+'.receipt.json'),dict(status='passed',worker=a.ref(D/(key+'.worker.json')),charged_ns=charge))
            print(name+' device acceptance passed',flush=True)
    a.put(D/'acceptance.json',dict(status='passed',jobs=[a.ref(D/(PREFIX+'-acceptance-'+n+'.receipt.json')) for n,_ in SCOPES],
        project=a.ref(D/'acceptance-project/acceptance.json'),ordinary_suite_reused=a.ref(ROOT/'artifacts/gpup-tensor-warp32-v1/acceptance-v1/gpup-tensor-warp32-v1-accept-regular.worker.json')))

def trial(j,ledger):
    key=j['id'];began=time.monotonic_ns();request,docs=inputs(j)
    for name,doc in docs.items():a.require(a.read(D/name)==doc,'frozen producer input differs')
    try:
        result,charge=execute_worker(ledger,key,request)
        control=j['configuration']['backend']=='cuda-lp-tuned'
        rp=D/(key+('.frozen.json' if control else '.expanded-request.json'));ep=D/(key+'.endpoint.json');cache=D/(key+'.verification.json')
        assessment=verify_new(a.checked(j['instance']['model']),rp,ep,cache,D/('optimizer' if control else 'lp_tensor_expanded'),control,j)
        document=dict(status='completed',id=key,job=j,worker=a.ref(D/(key+'.worker.json')),charged_ns=charge,
            assessment=assessment,endpoint=a.ref(ep),verification=a.ref(cache),coordinator_wall_ns=time.monotonic_ns()-began)
    except Exception as error:
        document=dict(status='incomplete',id=key,job=j,error=str(error),coordinator_wall_ns=time.monotonic_ns()-began)
        a.put(D/(key+'.trial.json'),document);raise
    a.put(D/(key+'.trial.json'),document);print(key+' completed and verified',flush=True)

def profiles():
    a.require(a.read(D/'acceptance.json')['status']=='passed','device acceptance incomplete')
    with JointLedger('profiles') as ledger:
        for j in jobs():
            if j['kind']=='profile':trial(j,ledger)
    with inherited_readers():result=screen.forecast(value(),D,identity())
    a.put(D/'forecast-binding.json',dict(result=a.ref(D/'forecast.json'),inputs=[a.ref(D/(j['id']+'.trial.json')) for j in jobs() if j['kind']=='profile'],
        reader=a.ref(ROOT/'tools/lp_tensor_warp32_screen.py')))
    a.require(result['passed'],'unchanged gain forecast refused')

def timings():
    a.require(a.read(D/'forecast.json')['passed'],'gain forecast incomplete')
    with inherited_readers():estimate=screen.resource_estimate(value(),D,identity())
    available=4*max(0,remaining('timings')-120*a.NS)
    result=dict(identity='gpup-tensor-expanded-resource-fit-v1',estimate=estimate,available_cpu_ns=available,
        gpu_allowance_ns=990*a.NS,multiplier=1.25,budget_amendment=a.ref(D/'timing-budget-amendment.json'),
        passed=bool(estimate['available'] and estimate['leased_ns']<=990*a.NS and estimate['cpu_ns']<=available))
    a.put(D/'resource-fit.json',result);a.require(result['passed'],'unchanged resource estimator refused active reservation')
    with JointLedger('timings') as ledger:
        for j in jobs():
            if j['kind']=='timing':trial(j,ledger)

def report():
    frozen();rows=[];times={};v=value()
    for j in jobs():
        key=j['id'];tp=D/(key+'.trial.json');row=dict(id=key,model=j['instance']['id'],configuration=j['configuration']['id'],kind=j['kind'],repetition=j['repetition'],status='not_executed',verified=False,certified=False)
        if tp.exists():
            trial_doc=a.read(tp);row['status']=trial_doc['status']
            if trial_doc['status']=='completed':
                assessment=verify_cached(v,j,D,identity());worker_doc=a.read(D/(key+'.worker.json'));ep=D/(key+'.endpoint.json')
                e=endpoint_shape(ep,'compact-v1') if j['configuration']['backend']=='cuda-lp-tuned' else a.read(ep)
                custom='outcome' in e;row['verified']=True
                numerical=(e['executor']=='gpu' and e['outcome']['core']['stop']=='certified' and e['outcome']['core']['failure'] is None) if custom else e['record']['backend']=='cuda-lp-tuned' and e['record']['termination']=='optimal'
                row['certified']=bool(j['kind']=='timing' and worker_doc['reason']=='completed' and worker_doc['returncode']==0 and assessment['gap_closed'] and numerical)
                if custom:row['useful']=useful_tensor(e)
                if j['configuration']['id'] in ['int8-tensor','fp16-tensor','bf16-tensor'] and not row.get('useful'):row['certified']=False
                if row['certified']:times[(row['model'],row['configuration'],j['repetition'])]=worker_doc['elapsed_ns']/a.NS
        rows.append(row)
    comparisons=[]
    for c in v['configurations'][:3]:
        coverage=all(sum((n,c['id'],r) in times for r in range(5))>=sum((n,'tuned-fp64',r) in times for r in range(5)) for n in v['timing_instances'])
        for n in v['timing_instances']:
            pairs=[(times[(n,'tuned-fp64',r)],times[(n,c['id'],r)]) for r in range(5) if (n,'tuned-fp64',r) in times and (n,c['id'],r) in times]
            comparisons.append(dict(model=n,configuration=c['id'],paired=len(pairs),coverage_equal=coverage,result=gain(pairs,coverage) if len(pairs)==5 else None))
    forecast=a.read(D/'forecast.json') if (D/'forecast.json').exists() else dict(passed=False)
    resource=a.read(D/'resource-fit.json') if (D/'resource-fit.json').exists() else dict(passed=False)
    useful={r['configuration'] for r in rows if r['certified'] and r.get('useful')};working='int8-tensor' in useful and bool(useful&{'fp16-tensor','bf16-tensor'})
    winning=any(c['result'] and c['result']['gain'] for c in comparisons)
    phases,_,settled,pending=a.aggregate(a.ledger_events());a.require(not pending,'unsettled ledger')
    charges={k:sum(e['charged_ns'] for e in settled if e['resource']=='gpu' and e['trial_id'].startswith(PREFIX+'-'+k+'-')) for k in a.PHASES}
    return dict(identity='gpup-tensor-expanded-report-v1',status='complete' if working and winning and forecast['passed'] and resource['passed'] and len(times)==60 else 'incomplete',
        planned_study_cells=76,rows=rows,comparisons=comparisons,forecast=forecast,resource_forecast=resource,working_families=working,certified_latency_gain=winning,
        certified_timings=len(times),new_gpu_ns=sum(charges.values()),phase_gpu_ns=charges,campaign_gpu_ns=sum(phases.values()),ledger=a.ref(a.LEDGER),ledger_events=len(a.ledger_events()))

def run_stage(stage):
    frozen();j=a.read(JOURNAL);amount=STAGES[stage]*a.NS;a.stage_admission(j,stage,amount)
    output=BASE/(stage+'-resource-v1.json');j['stage_attempts'][stage]=dict(output=str(output.relative_to(ROOT)),reserved_cpu_ns=amount);supervisor.atomic_json(JOURNAL,j)
    r=supervisor.run(dict(stage=stage,reserve_cpu_seconds=STAGES[stage],output=str(output),log=str(output)+'.log',journal=str(JOURNAL),
        lock=str(ROOT/'artifacts/lp-cpu-admission.lock'),slots=4,declared_memory_bytes=4<<30,rss_stop_bytes=6<<30,address_space_bytes=0,
        sources=[str(ROOT/i['path']) for i in a.read(D/'freeze.json')['files'] if i['path'].endswith(('.py','.sh','.rs','.cu','.h'))],
        bootstrap=False,show_log=True,max_gap_ns=100_000_000,command=[sys.executable,str(Path(__file__)),'child',stage]))
    if r['status']!='passed':
        j=a.read(JOURNAL);j['scientific_closed']=True;supervisor.atomic_json(JOURNAL,j)
    print(json.dumps(dict(stage=stage,status=r['status'],charged_cpu_ns=r['charged_cpu_ns'])))
    return 0 if r['status']=='passed' else 1

if __name__=='__main__':
    if sys.argv[1]=='project-child':project_child()
    elif sys.argv[1]=='child':globals()[sys.argv[2]]()
    elif sys.argv[1]=='run':raise SystemExit(run_stage(sys.argv[2]))
    elif sys.argv[1]=='report':a.put(BASE/'scientific-report-v1.json',report())
    else:raise SystemExit('unknown action')
