"""Independent ADR-0026 coverage, component costs and paired uncertainty report."""
import argparse
from collections import Counter,defaultdict
import csv
import fcntl
import os
from pathlib import Path
import statistics
import subprocess
import shutil
import time
from benchmark_lp_copt import jobs,effective,verify_endpoint
from lp_copt_budget import CONFIG,protocol,ledger_for
from lp_protocol import ROOT,checked_reference,digest,encoded,file_hash,read_json,validate,write_json
from lp_cost import validate_profile
from lp_report import paired_ratio,successful
from validate_artifacts import validator
from lp_copt_trace import analyze as analyze_trace


def decode(directory,value,importer=None,library=None):
    if file_hash(Path(value['nsys']))!=read_json(directory/'profiler.json')['sha256']:raise ValueError('offline exporter differs from measured profiler')
    importer=importer or Path('/opt/nvidia/nsight-compute/2025.3.0/host/linux-desktop-glibc_2_11_3-x64/QdstrmImporter')
    library=library or Path('/tmp/gpup2-nsys-libs/root/usr/lib/x86_64-linux-gnu')
    env={**os.environ,'LD_LIBRARY_PATH':str(library)};records=[];inputs=[]
    for j in jobs(value):
        if j['kind']!='trace':continue
        base=directory/j['id'];raw=Path(str(base)+'.qdstrm');rep=Path(str(base)+'.nsys-rep');sql=Path(str(base)+'.sqlite');commands=[]
        if raw.exists():
            ref=read_json(directory/(j['id']+'.cost.json'))['trace']
            if checked_reference(directory,ref)!=raw.resolve():raise ValueError('raw trace identity/path differs')
        if raw.exists() and not rep.exists():
            workspace=directory/'offline-import-work';workspace.mkdir(exist_ok=True)
            working=workspace/(j['id']+'-'+str(time.time_ns())+'.qdstrm');shutil.copy2(raw,working)
            inputs.append(dict(original=raw.name,sha256=file_hash(raw),working=str(working.relative_to(directory))))
            commands.append([str(importer),'--input-file',str(working),'--output-file',str(rep)])
        if (raw.exists() or rep.exists()) and not sql.exists():commands.append([value['nsys'],'export','--type=sqlite','--output='+str(sql),str(rep)])
        for cmd in commands:
            try:
                r=subprocess.run(cmd,env=env,capture_output=True,text=True,timeout=120)
                records.append(dict(command=cmd,returncode=r.returncode,stdout=r.stdout,stderr=r.stderr))
                if r.returncode:break
            except subprocess.TimeoutExpired:records.append(dict(command=cmd,returncode=None,stdout='',stderr='offline export timeout'));break
    for item in inputs:
        if file_hash(directory/item['original'])!=item['sha256']:raise ValueError('raw trace changed during offline import')
        item['working_after_sha256']=file_hash(directory/item['working'])
    if records:write_json(directory/('offline-import-'+str(time.time_ns())+'.json'),dict(gpu_work=False,nsys_sha256=file_hash(Path(value['nsys'])),importer_sha256=file_hash(importer),libdw_sha256=file_hash(library/'libdw.so.1') if (library/'libdw.so.1').exists() else None,commands=records,inputs=inputs))


def component_group(path):
    # Attribute a reference update and its nested arithmetic to recovery. Copy
    # synchronization belongs to that transfer's host envelope in this chart.
    if isinstance(path,str):path=[path]
    if any(any(part in name for part in ['adaptive_audit','adaptive_probe','reference_fp64_update','reference_correction','fp64_correction','checkpoint','window_rollback','reference_adoption']) for name in path):return 'recovery'
    if any(name in ['host_to_device','device_to_host'] for name in path):return 'transfers'
    name=path[-1]
    groups={
      'input_representation':['input','json','model_validation','sparse','hash','model_serialization'],
      'preparation':['precondition','ruiz','pock','norm','operator_preparation','precision_preparation','ladder_preparation','working_host_allocation','highs_model_conversion','native_preparation'],
      'device_setup':['device_context','module_load','kernel_lookup','stream_creation','device_allocation','residency','invariant_allocation'],
      'transfers':['host_to_device','device_to_host','working_upload','readback'],
      'iteration_control':['kernel_submission','synchronization','kernels_and','precision_chunk','cpu_arithmetic','controller','kkt','restart','working_state','iteration'],
      'recovery':['checkpoint','reference','correction','audit','rollback','transition','demotion','adaptive_probe'],
      'certification':['candidate_feasibility','dual_certification','gap_assessment','host_checks','original_program_assessment','independent_endpoint','endpoint_verification','external_assessment','host_certification','study_verification'],
      'output_teardown':['serialization','write','output','teardown','module_unload','device_free','native_extraction','witness_extraction'],
      'copt_setup':['import_bindings','environment_license','model_creation','variable_construction','constraint_construction','objective_construction','parameter_setup'],
      'native_solve':['native_solve'],
    }
    for group,parts in groups.items():
        if any(part in name for part in parts):return group
    return 'other_host'


def numerical_digest(endpoint):
    """Binary64-aware retained state identity, excluding clocks/native memory reports."""
    import struct
    if 'witness' in endpoint:
        w=endpoint['witness']
        state={k:w[k] for k in ['model_sha256','requested_backend','executed_backend','options','parameters','row_ids','variable_ids','primal','dual','status','iterations']}
        state['native_iterations']={k:w['native'][k] for k in ['simplex_iterations','barrier_iterations','pdlp_iterations']} if w['native'] else None
    else:
        state={k:endpoint.get(k) for k in ['control','precision','adaptive']};state['record']={k:v for k,v in endpoint['record'].items() if k not in ['elapsed_ms','validation']}
        state['model_sha256']=endpoint.get('model_sha256')
        state['diagnostics']={k:endpoint['diagnostics'][k] for k in ['dual','iterations','assessment_iteration','restarts']}
    state['assessment']=endpoint['assessment']
    def bits(value):
        if isinstance(value,float):return {'binary64':struct.pack('>d',value).hex()}
        if isinstance(value,list):return [bits(v) for v in value]
        if isinstance(value,dict):return {k:bits(v) for k,v in value.items()}
        return value
    return digest(encoded(bits(state)))


def checked_component_rows(cost,directory,endpoint,external):
    """Check child envelopes and transfer counts without summing subprocess walls."""
    rows={}
    for observation in cost['observations']:
        name=observation['process'];parent=observation['parent_scope']
        if name in rows:raise ValueError('duplicate process cost observation')
        if name=='solve':
            if parent is not None:raise ValueError('solve cannot have parent scope')
        elif name=='host-certifier':
            if not external or parent!=['copt','host_certification']:raise ValueError('invalid certifier parent')
        else:raise ValueError('unknown component process')
        raw=read_json(checked_reference(directory,observation['artifact']));validate_profile(raw);rows[name]=raw
    if 'host-certifier' in rows and 'solve' not in rows and not cost.get('partial',False):raise ValueError('complete certifier observation lacks parent')
    if 'host-certifier' in rows and 'solve' in rows:
        parent=next((x for x in rows['solve']['scopes'] if x['path']==['copt','host_certification']),None)
        if parent is None or rows['host-certifier']['elapsed_ns']>parent['inclusive_ns']:raise ValueError('child exceeds parent envelope')
    if not external and endpoint is not None and endpoint.get('execution') and 'solve' in rows:
        for counter,field in [('device_allocated_bytes','allocated_bytes'),('host_to_device_bytes','upload_bytes'),('device_to_host_bytes','readback_bytes')]:
            observed=rows['solve']['counters'].get(counter);expected=endpoint['execution'][field]
            # A guard can terminate before this operation is observed. Preserve
            # the absent raw counter as unavailable instead of manufacturing zero.
            if observed is None and expected==0:continue
            if observed!=expected:raise ValueError('device byte accounting differs')
    return rows


def check_worker(trial,worker):
    """Bind latency and resource observations to the supervised process receipt."""
    for key in ['elapsed_ns','queue_ns','leased_ns','peak_rss_bytes','memory_method']:
        if trial[key]!=worker[key]:raise ValueError('trial/worker '+key+' differs')
    if trial['error']=='supervisor failed':
        if trial['status']!='process_failure':raise ValueError('supervisor failure cannot qualify')
    elif trial['status'] not in ['invalid_evidence','missing_evidence'] and trial['status']!=worker['reason']:
        raise ValueError('trial/worker outcome differs')


def check_collector_envelope(raw,process,elapsed_ns):
    if process=='solve' and raw['elapsed_ns']>elapsed_ns:
        raise ValueError('collector exceeds worker envelope')


def qualified_trial(trial,backend,classification,worker):
    """Keep the immutable first assessment; only recover its explicit byte-limit omission."""
    result=dict(trial)
    if trial['status']=='invalid_evidence':
        if 'input exceeds 16 MiB' not in (trial.get('error') or ''):
            raise ValueError('unresolved initial invalid evidence: '+str(trial.get('error')))
        result.update(status=worker['reason'],executed_backend=backend,endpoint_class=classification)
    elif (backend,classification)!=(trial['executed_backend'],trial['endpoint_class']):
        raise ValueError('endpoint/trial assessment differs')
    return result


def report(directory,config,binary,output,verifier=None,verifier_execution=None):
    if output.exists():raise ValueError('refusing to overwrite a report')
    value=protocol(config);schedule=list(jobs(value));planned={j['id']:j for j in schedule};verifier=verifier or binary
    if read_json(directory/'campaign.json')!=value:raise ValueError('archived protocol differs')
    identities=read_json(directory/'configuration-executions.json');execution=read_json(directory/'execution.json')
    if file_hash(directory/'source.tar')!=execution['source_archive_sha256'] or file_hash(binary)!=execution['binary_sha256']:raise ValueError('archived source/executable differs')
    for name,expected in read_json(directory/'code-objects.json').items():
        if file_hash(directory/name)!=expected:raise ValueError('archived code object differs')
    verification_identity=execution
    if verifier!=binary:
        if verifier_execution is None:raise ValueError('separate verifier requires archived execution identity')
        verification_identity=read_json(verifier_execution)
        if file_hash(verifier)!=verification_identity['binary_sha256'] or file_hash(verifier_execution.parent/'source.tar')!=verification_identity['source_archive_sha256']:
            raise ValueError('independent verifier archive identity differs')
    profiler=read_json(directory/'profiler.json');trials={};qualified={};endpoints={};costs=[];work=[];traces=[];native_observations=[];verification=[];validation_started=time.monotonic_ns()
    for path in sorted(directory.glob('*.trial.json')):
        t=validate('trial',read_json(path));key=t['id']
        if key not in planned or key in trials:raise ValueError('unplanned/duplicate trial')
        j=planned[key];c=j['configuration'];solve,method,limits=effective(value,j);identity=identities[c['id']]
        expected=dict(campaign_sha256=file_hash(config),instance_id=j['instance']['id'],model_sha256=j['instance']['model']['sha256'],config_id=c['id'],
            config_sha256=digest(encoded(dict(configuration=c,solve=solve,lp_settings=method))),requested_backend=c['backend'],repetition=j['repetition'],order=j['order'],mode=j['kind'],category=j['category'],
            block=f'{j["kind"]}:{j["instance"]["id"]}:{j["repetition"]}',solve=solve,lp_settings=method,limits=limits)
        if any(t[k]!=v for k,v in expected.items()):raise ValueError('trial differs from frozen request: '+key)
        for k,v in identity.items():
            if k not in ['telemetry_before','telemetry_after'] and t['provenance'][k]!=v:raise ValueError('execution identity differs: '+key)
        if t['provenance']['schema_snapshot_sha256']!=execution['schema_snapshot_sha256']:raise ValueError('schema identity differs')
        request=directory/(key+'.request.json')
        if file_hash(request)!=t['request_sha256']:raise ValueError('worker request hash differs')
        req=read_json(request)
        if any(req[k]!=limits[k] for k in ['solve_seconds','cleanup_seconds','host_rss_bytes','output_bytes','poll_ms']) or req['prefix']!=key:raise ValueError('worker limits/identity differ')
        for role in ['worker','stdout','stderr','endpoint','activity','cost']:
            if t[role] is not None:checked_reference(directory,t[role])
        if t['worker'] is not None:check_worker(t,read_json(checked_reference(directory,t['worker'])))
        e=None;qualified[key]=t
        if t['endpoint'] is not None:
            verify_started=time.monotonic_ns()
            backend,classification=verify_endpoint(value,j,directory,verifier,identity)
            worker=read_json(checked_reference(directory,t['worker']))
            qualified[key]=qualified_trial(t,backend,classification,worker)
            verification.append(dict(trial=key,endpoint_sha256=t['endpoint']['sha256'],elapsed_ns=time.monotonic_ns()-verify_started,
                initial_status=t['status'],initial_error=t['error'],classification=classification,executed_backend=backend,
                recovered_input_limit=t['status']=='invalid_evidence',certified_latency_eligible=successful(qualified[key])))
            e=read_json(checked_reference(directory,t['endpoint']))
            verification[-1]['assessment']=e['assessment']
            verification[-1]['numerical_state_sha256']=numerical_digest(e)
            endpoints[key]=dict(kernel_launches=e.get('diagnostics',{}).get('kernel_launches'))
            if c['backend'].startswith('copt-'):
                observations=dict(native=e['witness']['native'],work_units='aggregate native iterations; not project physical updates',physical_updates=None,iterations=e['witness']['iterations'])
            elif c['backend']=='highs':
                observations=dict(native=dict(simplex_iterations=e['diagnostics']['iterations']),work_units='HiGHS native simplex iterations; not project physical updates',physical_updates=None,iterations=e['diagnostics']['iterations'])
            else:
                a=e.get('adaptive');precision=e.get('precision');control=e.get('control') or {};d={k:v for k,v in e['diagnostics'].items() if k!='dual'}
                observations=dict(work_units='project physical updates',physical_updates=control.get('physical_iterations',d.get('iterations')),logical_iterations=control.get('logical_iterations',d.get('iterations')),
                    adaptive=a,precision=precision,execution=e.get('execution'),control=control,diagnostics=d)
            work.append(dict(trial=key,instance=j['instance']['id'],config=c['id'],kind=j['kind'],observations=observations))
        if t['cost']:
            cost=read_json(checked_reference(directory,t['cost']));validator('lp-cost-v1.schema.json').validate(cost)
            expected_cost=dict(trial_id=key,model_sha256=t['model_sha256'],request_sha256=t['request_sha256'],source_tree_sha256=identity['source_tree_sha256'],binary_sha256=identity['binary_sha256'],
                endpoint_sha256=t['endpoint']['sha256'] if t['endpoint'] else None,profiler_sha256=profiler['sha256'] if j['kind']=='trace' else None)
            if any(cost[k]!=v for k,v in expected_cost.items()):raise ValueError('component identity differs')
            raw_by_process=checked_component_rows(cost,directory,e,c['backend'].startswith('copt-'))
            for observation in cost['observations']:
                raw=raw_by_process[observation['process']];residual=validate_profile(raw)
                check_collector_envelope(raw,observation['process'],t['elapsed_ns'])
                groups=defaultdict(int)
                for scope in raw['scopes']:groups[component_group(scope['path'])]+=scope['exclusive_ns']
                costs.append(dict(trial=key,instance=j['instance']['id'],config=c['id'],kind=j['kind'],repetition=j['repetition'],process=observation['process'],parent_scope=observation['parent_scope'],
                    elapsed_ns=raw['elapsed_ns'],worker_elapsed_ns=t['elapsed_ns'],residual_ns=residual,groups_ns=dict(groups),scopes=raw['scopes'],counters=raw['counters'],unavailable=raw['unavailable'],partial=cost['partial']))
            for role in ['native_observations','trace']:
                if cost[role]:checked_reference(directory,cost[role])
            if cost['native_observations']:
                native=read_json(checked_reference(directory,cost['native_observations']))
                log=native['log_observations'];lines=log.pop('lines')
                native_observations.append(dict(trial=key,instance=j['instance']['id'],config=c['id'],observations=native,
                    artifact=cost['native_observations'],log_line_count=len(lines),
                    phase_messages=[line for line in lines if any(word in line['message'].lower() for word in ['presolv','scaling','barrier','simplex','pdlp','gpu','solving'])]))
            if j['kind']=='trace':
                sql=directory/(key+'.sqlite');trace=dict(trial=key,instance=j['instance']['id'],config=c['id'],status='unavailable',reason='no decoded trace; raw/partial collection retained')
                if sql.exists():
                    try:
                        data=analyze_trace(sql);timeline=data.pop('timeline');timeline_path=directory/(key+'.timeline.json')
                        if not timeline_path.exists():write_json(timeline_path,timeline)
                        expected_count=endpoints.get(key,{}).get('kernel_launches')
                        valid=expected_count is None or expected_count==data['kernel_count']
                        trace.update(status='measured' if valid and qualified[key]['status']=='completed' else 'partial',initial_cost_partial=cost['partial'],reason=None if valid else 'project endpoint/trace launch counts differ',data=data,
                            sqlite_sha256=file_hash(sql),timeline=dict(path=timeline_path.name,sha256=file_hash(timeline_path)))
                    except (ValueError,sqlite_error()) as error:trace['reason']=str(error)
                traces.append(trace)
        if j['kind']=='trace' and not t['cost']:
            traces.append(dict(trial=key,instance=j['instance']['id'],config=c['id'],status='unavailable',reason='no cost artifact; attempted trace files retained'))
        trials[key]=t
        if len(trials)%50==0:print('independently checked',len(trials),'trials',flush=True)
    ledger=ledger_for(value);snapshot=(directory/'ledger.jsonl').read_bytes()
    with (ledger.path.parent/'campaign.lock').open('rb') as lock:
        fcntl.flock(lock,fcntl.LOCK_SH|fcntl.LOCK_NB);active=ledger.path.read_bytes()
        if not snapshot.endswith(b'\n') or not active.startswith(snapshot):raise ValueError('historical snapshot prefix differs')
        ledger._load();ledger.events=ledger.events[:len(snapshot.splitlines())]
        if ledger.pending():raise ValueError('unsettled snapshot')
        attempted={e['trial_id'] for e in ledger.events if e['kind'] in ('settle','recover') and e['trial_id'].startswith(value['id']+'-') and '-accept-' not in e['trial_id']}
        if attempted!=set(trials):raise ValueError('ledger/attempt coverage differs')
        if any(ledger.usage(c)>v['seconds']*1e9 for c,v in value['categories'].items()) or sum(ledger.usage(c) for c in value['categories'])>value['combined_cap_seconds']*1e9:raise ValueError('category cap exceeded')
        if ledger.totals()>value['cumulative_gpu_ns'] or any(ledger.totals(phase=phase)>seconds*1e9 for phase,seconds in value['phase_gpu_seconds'].items()):raise ValueError('campaign ceiling/phase cap exceeded')
        budget=dict(categories_ns={c:ledger.usage(c) for c in value['categories']},campaign_phase_ns={phase:sum(e['charged_ns'] for e in ledger.events if e['resource']=='gpu' and e['phase']==phase) for phase in value['phase_gpu_seconds']},cumulative_ns=ledger.totals(),ceiling_ns=value['cumulative_gpu_ns'],ledger_sha256=file_hash(directory/'ledger.jsonl'),events=len(ledger.events),
                    cpu_worker_ns=sum(ledger.usage(c,'cpu') for c in value['categories']),additional_report_analysis_ns=time.monotonic_ns()-validation_started,independent_verification_wall_ns=sum(v['elapsed_ns'] for v in verification))
    rows=[];groups=defaultdict(dict)
    for j in schedule:
        if j['kind']=='timing' and j['id'] in trials:groups[(j['instance']['id'],j['configuration']['id'])][j['repetition']]=qualified[j['id']]
    verification_by_trial={v['trial']:v for v in verification};equivalence=[]
    instances=list(dict.fromkeys(j['instance']['id'] for j in schedule if j['kind']=='timing'));ratios=[];overhead=[]
    for instance in instances:
        for c in value['configurations']:
            observations=groups[(instance,c['id'])];accepted=[t for t in observations.values() if successful(t)]
            rows.append(dict(instance=instance,config=c['id'],planned=3,attempted=len(observations),certified=len(accepted),median_ns=statistics.median(t['elapsed_ns'] for t in accepted) if accepted else None,
                             outcomes=dict(Counter(trials[t['id']]['status']+'/'+str(trials[t['id']]['endpoint_class']) for t in observations.values())),initial_certified=sum(successful(trials[t['id']]) for t in observations.values())))
            for ref in ['copt-cpu-default','copt-cpu-pdlp','copt-gpu-pdlp','tuned-fp64']:
                if c['id']==ref:continue
                left=groups[(instance,ref)];pairs=[(left[r]['elapsed_ns'],t['elapsed_ns']) for r,t in observations.items() if r in left and successful(t) and successful(left[r])]
                ratios.append(dict(instance=instance,reference=ref,candidate=c['id'],statistics=paired_ratio(pairs,value['analysis']['seed'],value['analysis']['resamples'])))
            profiles=[t for t in qualified.values() if t['instance_id']==instance and t['config_id']==c['id'] and t['mode']=='profile']
            pairs=[(observations[t['repetition']]['elapsed_ns'],t['elapsed_ns']) for t in profiles if t['repetition'] in observations and successful(t) and successful(observations[t['repetition']])]
            for t in profiles:
                baseline=observations.get(t['repetition'])
                if baseline is None:continue
                left=verification_by_trial.get(baseline['id']);right=verification_by_trial.get(t['id'])
                comparable=left is not None and right is not None and successful(t) and successful(baseline)
                equivalence.append(dict(instance=instance,config=c['id'],repetition=t['repetition'],ordinary_trial=baseline['id'],profile_trial=t['id'],
                    comparable_certified_completed=comparable,bitwise_numerical_equivalent=(left['numerical_state_sha256']==right['numerical_state_sha256']) if comparable else None,
                    ordinary_state_sha256=left['numerical_state_sha256'] if left else None,profile_state_sha256=right['numerical_state_sha256'] if right else None))
            overhead.append(dict(instance=instance,config=c['id'],unprofiled_over_profiled=paired_ratio(pairs,value['analysis']['seed'],value['analysis']['resamples']),
                scope='Separate executions: ratio includes instrumentation and ordinary run variability; wall-limited divergence is retained.'))
    trace_overhead=[]
    for j in schedule:
        if j['kind']!='trace':continue
        t=qualified.get(j['id']);baseline=groups[(j['instance']['id'],j['configuration']['id'])].get(j['repetition'])
        paired=t is not None and baseline is not None and successful(t) and successful(baseline)
        left=verification_by_trial.get(baseline['id']) if baseline else None;right=verification_by_trial.get(j['id'])
        trace_overhead.append(dict(trial=j['id'],instance=j['instance']['id'],config=j['configuration']['id'],
            ordinary_trial=baseline['id'] if baseline else None,trace_elapsed_ns=t['elapsed_ns'] if t else None,ordinary_elapsed_ns=baseline['elapsed_ns'] if baseline else None,
            certified_pair=paired,trace_over_ordinary=t['elapsed_ns']/baseline['elapsed_ns'] if paired else None,
            bitwise_numerical_equivalent=left['numerical_state_sha256']==right['numerical_state_sha256'] if left and right else None,
            trace_status=t['status'] if t else 'missing',ordinary_status=baseline['status'] if baseline else 'missing',
            limitation='One diagnostic repetition; process ratio includes profiler startup/finalization and run variation. Native limits unchanged; supervisor has fifteen additional seconds.'))
    # Ratios divide only a documented enclosing phase by its actual recorded
    # work. Rejected and replay proposals overlap and are never added to totals.
    per_unit=[];rung_costs=[];work_by_trial={w['trial']:w['observations'] for w in work}
    for cost in costs:
        if cost['process']!='solve':continue
        observation=work_by_trial.get(cost['trial'],{});adaptive=observation.get('adaptive') or {};control=observation.get('control') or {}
        units=dict(physical_update=observation.get('physical_updates'),proposal=adaptive.get('proposed_steps',observation.get('physical_updates')),
                   audit=adaptive.get('audit_steps'),probe=adaptive.get('probe_steps'),assessment=control.get('assessments'),
                   host_to_device_byte=cost['counters'].get('host_to_device_bytes'),device_to_host_byte=cost['counters'].get('device_to_host_bytes'),
                   native_iteration=observation.get('iterations') if 'native' in observation else None)
        phases=dict(physical_update=['adaptive_iterations','kernels_and_synchronization','iteration'],proposal=['kernels_and_synchronization'],
                    audit=['adaptive_audit'],probe=['adaptive_probe'],assessment=['host_checks'],host_to_device_byte=['host_to_device'],
                    device_to_host_byte=['device_to_host'],native_iteration=['native_solve_call','native_solve'])
        for scope in cost['scopes']:
            if scope['path'][-1].startswith('adaptive_rung_'):
                rung=int(scope['path'][-1].rsplit('_',1)[-1]);ladder=adaptive.get('settings',{}).get('ladder',[])
                rung_costs.append(dict(trial=cost['trial'],instance=cost['instance'],config=cost['config'],kind=cost['kind'],rung=rung,
                    mode=ladder[rung] if rung<len(ladder) else None,windows=scope['calls'],inclusive_ns=scope['inclusive_ns'],exclusive_ns=scope['exclusive_ns'],
                    children=[x for x in cost['scopes'] if len(x['path'])==len(scope['path'])+1 and x['path'][:-1]==scope['path']]))
        metrics=[]
        for unit,count in units.items():
            selected=[row for row in cost['scopes'] if row['path'][-1] in phases[unit]]
            # Keep only outermost selected paths to prevent nested phase sums.
            selected=[row for row in selected if not any(other is not row and row['path'][:len(other['path'])]==other['path'] for other in selected)]
            duration=sum(row['inclusive_ns'] for row in selected) if selected else None
            metrics.append(dict(unit=unit,count=count,phase_ns=duration,ns_per_unit=duration/count if duration is not None and count else None,
                                paths=[row['path'] for row in selected]))
        per_unit.append(dict(trial=cost['trial'],instance=cost['instance'],config=cost['config'],kind=cost['kind'],metrics=metrics,
                             rejected_proposals=adaptive.get('rejected_steps'),replay_proposals=adaptive.get('replay_steps'),
                             overlap='rejected/replay are overlapping proposal subsets, not additive work or disjoint wall phases'))
    counts=Counter(t['status']+'/'+str(t['endpoint_class']) for t in trials.values())
    bad={'process_failure','invalid_evidence','missing_evidence','lease_timeout','lease_cancelled','cancelled_before_launch','activity_blocked'}
    result=dict(schema_version=6,id=value['id'],status='complete' if len(trials)==len(schedule) and not any(t['status'] in bad for t in trials.values()) else 'incomplete',
        planned=len(schedule),attempted=len(trials),verified_endpoints=len(endpoints),certified=sum(successful(t) for t in qualified.values()),initial_certified=sum(successful(t) for t in trials.values()),outcomes=dict(counts),
        protocol_sha256=file_hash(config),execution=execution,verification=dict(execution=verification_identity,analysis_source_tree_sha256=__import__('benchmark_lp').source_identity(),receipts=verification),budget=budget,rows=rows,ratios=ratios,instrumentation_overhead=overhead,observed_profile_equivalence=equivalence,trace_overhead=trace_overhead,work=work,costs=costs,traces=traces,per_unit=per_unit,rung_costs=rung_costs,native_observations=native_observations,
        missing=[j['id'] for j in schedule if j['id'] not in trials],
        diagnostic_coverage=[dict(trial=j['id'],kind=j['kind'],instance=j['instance']['id'],config=j['configuration']['id'],
            attempted=j['id'] in trials,initial_status=trials.get(j['id'],{}).get('status','missing'),
            verified=j['id'] in endpoints,final_status=qualified.get(j['id'],{}).get('status','missing'),final_classification=qualified.get(j['id'],{}).get('endpoint_class'),host_observed=any(c['trial']==j['id'] and c['process']=='solve' for c in costs),
            trace_status=next((t['status'] for t in traces if t['trial']==j['id']),None)) for j in schedule if j['kind']!='timing'],
        limitations=['Development only; three repetitions do not establish a preset or general superiority.',
            'Native COPT iterations differ from project physical updates; internal arithmetic and unavailable CPU phases remain opaque.',
            'Host certifier costs are children of COPT host_certification; do not add process envelopes.',
            'Instrumented and traced results never replace primary fresh-process certified latency.',
            'Original trials remain immutable. Explicit initial 16 MiB endpoint-parser failures may qualify only after independent verification under the approved 128 MiB study allowance; worker completion and all numerical criteria still apply.',
            'Historical 65536-row throughput timeouts and tuned_cases racecheck gap remain open.'])
    write_json(output,result)
    with output.with_suffix('.trials.csv').open('w',newline='') as f:
        keys=['id','instance','config','kind','repetition','status','classification','elapsed_ns','leased_ns','verified','final_status','final_classification','certified_latency_eligible','initial_error'];writer=csv.DictWriter(f,fieldnames=keys);writer.writeheader()
        for j in schedule:
            t=trials.get(j['id'],{});writer.writerow(dict(id=j['id'],instance=j['instance']['id'],config=j['configuration']['id'],kind=j['kind'],repetition=j['repetition'],status=t.get('status','missing'),classification=t.get('endpoint_class'),elapsed_ns=t.get('elapsed_ns'),leased_ns=t.get('leased_ns'),verified=j['id'] in endpoints,final_status=qualified.get(j['id'],{}).get('status','missing'),final_classification=qualified.get(j['id'],{}).get('endpoint_class'),certified_latency_eligible=successful(qualified[j['id']]) if j['id'] in qualified else False,initial_error=t.get('error')))
    with output.with_suffix('.costs.csv').open('w',newline='') as f:
        keys=['trial','instance','config','kind','repetition','process','path','calls','inclusive_ns','exclusive_ns','min_ns','max_ns','partial'];writer=csv.DictWriter(f,fieldnames=keys);writer.writeheader()
        for c in costs:
            for s in c['scopes']:writer.writerow({**{k:c[k] for k in keys if k in c},**{k:v for k,v in s.items() if k!='path'},'path':'/'.join(s['path'])})
    print(result['status'],result['attempted'],'attempted;',result['verified_endpoints'],'verified;',result['certified'],'certified',flush=True)
    return result

def sqlite_error():
    import sqlite3
    return sqlite3.Error

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--protocol',type=Path,default=CONFIG);p.add_argument('--directory',type=Path);p.add_argument('--output',type=Path);p.add_argument('--decode-traces',action='store_true');p.add_argument('--verifier',type=Path);p.add_argument('--verifier-execution',type=Path);a=p.parse_args()
    value=protocol(a.protocol);directory=a.directory or ROOT/value['output']
    if a.decode_traces:decode(directory,value)
    report(directory,a.protocol,directory/'optimizer',a.output or directory/'report.json',a.verifier,a.verifier_execution)
if __name__=='__main__':main()
