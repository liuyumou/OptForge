"""Exact-source device acceptance, six policy pairs and twelve replays (ADR-0039)."""
import argparse
import os
from pathlib import Path
import re
import subprocess
from benchmark_lp import reference
from benchmark_lp_assess import instances
from lp_assess_budget import protocol,ledger_for,validate_command
from lp_protocol import ROOT,checked_reference,file_hash,read_json,write_json,digest,encoded

def numerical(e):
    o=e['witness']['outcome']
    return {k:o[k] for k in ['status','failure','point','physical_steps','logical_steps','proposed_steps','controller_checks','kkt_evaluations','restarts']}

def numerical_digest(e):return digest(encoded(numerical(e)))

def replay_matches(original,replayed):
    return original['witness']['request']==replayed['witness']['request'] and encoded(original['witness']['outcome'])==encoded(replayed['witness']['outcome']) and encoded(original['assessment'])==encoded(replayed['assessment']) and [r['sha256'] for r in original['witness']['traces']]==[r['sha256'] for r in replayed['witness']['traces']]

def project(v):
    if os.environ.get('AI_OPTIMIZER_GPU_LEASE')!='inherited' or os.environ.get('CUDA_VISIBLE_DEVICES')!=v['device']:raise ValueError('selected shared host lease required')
    study=ROOT/v['output'];identity=read_json(study/'execution.json');key=os.environ.get('AI_OPTIMIZER_ASSESS_ACCEPT_KEY','project')
    directory=ROOT/v['acceptance_output']/(key+'-project');directory.mkdir(parents=True,exist_ok=False)
    binary=study/'lp_precision_assess';images=read_json(study/'code-objects.json');binaries=read_json(study/'acceptance-binaries.json')
    device_binary=checked_reference(ROOT,binaries['assess'])
    test=subprocess.run([str(device_binary),'--test-threads','1','--nocapture'],capture_output=True,text=True,timeout=45,env=dict(os.environ,AI_OPTIMIZER_GPU='1'))
    (directory/'device.stdout').write_text(test.stdout);(directory/'device.stderr').write_text(test.stderr)
    print(test.stdout,flush=True);print(test.stderr,flush=True)
    if test.returncode or '3 passed; 0 failed' not in test.stdout or 'SKIP ' in test.stdout+test.stderr:raise ValueError('assessment device differentials failed')
    rows=[];models=instances(v)
    result=dict(status='incomplete',source_tree_sha256=identity['source_tree_sha256'],executable_sha256=file_hash(binary),test_binary=binaries['assess'],pairs=rows)
    try:
        for name in v['acceptance_instances']:
            for arithmetic in ['tuned_fp64','accumulation_fp32']:
                endpoints={};references={};replays={}
                for policy in ['fixed_200','bounded_800']:
                    stem=name+'-'+arithmetic+'-'+policy;endpoint=directory/(stem+'.endpoint.json');request=directory/(stem+'.request.json');model=checked_reference(ROOT,models[name]['model'])
                    payload=dict(schema_version=1,identity='lp-assess-v1',arithmetic=arithmetic,policy=policy,model_sha256=models[name]['model']['sha256'],source_tree_sha256=identity['source_tree_sha256'],executable_sha256=file_hash(binary),code_object_sha256=images['lp_pdhg_tuned.cubin' if arithmetic=='tuned_fp64' else 'lp_pdhg_precision.cubin'],device=v['device'],options=dict(v['solve'],iteration_limit=v['acceptance_work'],time_limit_ms=30000),method=dict(v['lp_settings'],iteration_limit=v['acceptance_work']),diagnostic=True,device_buffer_bytes=v['limits']['device_buffer_bytes'])
                    write_json(request,payload)
                    for action in ['solve','verify','replay']:
                        r=subprocess.run([str(binary),action,str(model),str(request),str(endpoint)],capture_output=True,text=True,timeout=30)
                        (directory/(stem+'.'+action+'.stdout')).write_text(r.stdout);(directory/(stem+'.'+action+'.stderr')).write_text(r.stderr)
                        if r.returncode:raise ValueError('assessment '+action+' failed '+r.stderr[:2000])
                    e=read_json(endpoint)
                    if e['witness']['request']!=payload or e['witness']['outcome']['physical_steps']!=v['acceptance_work'] or e['witness']['outcome']['status']!='iteration_limit':raise ValueError('assessment fixed-work acceptance differs')
                    endpoints[policy]=e;references[policy]=reference(ROOT,endpoint);replays[policy]=reference(ROOT,endpoint.with_name(endpoint.name+'.replay.json'))
                a,b=(endpoints[p] for p in ['fixed_200','bounded_800'])
                if numerical_digest(a)!=numerical_digest(b) or [r['sha256'] for r in a['witness']['traces']]!=[r['sha256'] for r in b['witness']['traces']]:raise ValueError('assessment policies changed numerical trajectory')
                rows.append(dict(instance=name,arithmetic=arithmetic,numerical_sha256=digest(encoded(numerical(a))),endpoints=references,replays=replays))
        result['status']='passed'
    finally:write_json(ROOT/v['acceptance_output']/(key+'.project.json'),result)
    print('six assessment fixed-work pairs and twelve same-device replays pass',flush=True)

def check_acceptance(v,identity):
    directory=ROOT/v['acceptance_output'];study=ROOT/v['output'];events=[__import__('json').loads(x) for x in ledger_for(v).path.read_bytes().splitlines()];found={}
    for path in sorted(directory.glob('*.source.json')):
        source=read_json(path);key=path.name[:-len('.source.json')];gate=source['gate']
        if source['source_tree_sha256']!=identity['source_tree_sha256']:raise ValueError('assessment acceptance source differs')
        request_path=directory/(key+'.request.json');request=read_json(request_path);worker_path=directory/(key+'.worker.json');worker=read_json(worker_path)
        if file_hash(request_path)!=source['request_sha256'] or request['command'][:2]!=['/usr/bin/env','AI_OPTIMIZER_CUDA_DIR='+str(study)]:raise ValueError('assessment acceptance command/source differs')
        validate_command(gate,request['command'][2:])
        if request['prefix']!=key or request['directory']!=str(directory) or request['solve_seconds']!=(120 if gate in ['regular','project'] else 60):raise ValueError('assessment acceptance limits differ')
        for ref in source['binaries']:
            binary=checked_reference(ROOT,ref)
            if binary.parent!=study or str(binary) not in request['command']:raise ValueError('assessment acceptance executable binding differs')
        transactions=[e for e in events if e['trial_id']==key]
        if len(transactions)!=2 or transactions[0]['kind']!='reserve' or transactions[1]['kind']!='settle' or transactions[1]['charged_ns']!=worker['leased_ns'] or any(e['reserved_ns']!=(request['solve_seconds']+6)*10**9 or e['phase']!='repeatability' for e in transactions):raise ValueError('assessment acceptance charge differs')
        if worker['reason']!='completed' or worker['returncode']!=0 or worker['activity']['device']!=v['device'] or worker['leased_ns']>transactions[0]['reserved_ns']:raise ValueError('assessment acceptance worker failed')
        stdout=(directory/(key+'.stdout')).read_text();stderr=(directory/(key+'.stderr')).read_text()
        if 'SKIP ' in stdout+stderr:raise ValueError('assessment skipped device coverage')
        if gate=='regular' and re.findall(r'test result: ok\. (\d+) passed; 0 failed;',stdout)!=['14','6','46']:raise ValueError('assessment ordinary 66-device gate incomplete')
        if gate not in ['regular','project'] and ('1 passed; 0 failed' not in stdout or not any('ERROR SUMMARY: 0 errors' in text or 'RACECHECK SUMMARY: 0 hazards' in text for text in [stdout,stderr])):raise ValueError('assessment scoped sanitizer receipt incomplete')
        if gate=='project':
            project=read_json(directory/'project.project.json')
            if project['status']!='passed' or project['source_tree_sha256']!=identity['source_tree_sha256'] or project['executable_sha256']!=identity['exec_binary_sha256'] or len(project['pairs'])!=6:raise ValueError('assessment project receipt incomplete')
            checked_reference(ROOT,project['test_binary'])
            expected=[(name,arithmetic) for name in v['acceptance_instances'] for arithmetic in ['tuned_fp64','accumulation_fp32']]
            if [(p['instance'],p['arithmetic']) for p in project['pairs']]!=expected:raise ValueError('assessment project roster differs')
            images=read_json(study/'code-objects.json')
            for pair in project['pairs']:
                endpoints={}
                for policy,ref in pair['endpoints'].items():
                    ep=checked_reference(ROOT,ref);e=read_json(ep);r=e['witness']['request'];model=checked_reference(ROOT,instances(v)[pair['instance']]['model'])
                    expected_request=dict(schema_version=1,identity='lp-assess-v1',arithmetic=pair['arithmetic'],policy=policy,model_sha256=file_hash(model),source_tree_sha256=identity['source_tree_sha256'],executable_sha256=identity['exec_binary_sha256'],code_object_sha256=images['lp_pdhg_tuned.cubin' if pair['arithmetic']=='tuned_fp64' else 'lp_pdhg_precision.cubin'],device=v['device'],options=dict(v['solve'],iteration_limit=v['acceptance_work'],time_limit_ms=30000),method=dict(v['lp_settings'],iteration_limit=v['acceptance_work']),diagnostic=True,device_buffer_bytes=v['limits']['device_buffer_bytes'])
                    if r!=expected_request or e['witness']['outcome']['physical_steps']!=v['acceptance_work']:raise ValueError('assessment acceptance complete request differs')
                    rp=ep.with_name(ep.name.replace('.endpoint.json','.request.json'))
                    if read_json(rp)!=r:raise ValueError('assessment acceptance request file differs')
                    for evidence_path in [ep,checked_reference(ROOT,pair['replays'][policy])]:
                        result=subprocess.run([str(study/'lp_precision_assess'),'verify',str(model),str(rp),str(evidence_path)],capture_output=True,text=True,timeout=v['verification_seconds'])
                        if result.returncode or result.stdout.strip()!='verified':raise ValueError('assessment acceptance host verification failed '+result.stderr[:1000])
                        replayed=read_json(evidence_path)
                        if not replay_matches(e,replayed):raise ValueError('assessment replay numerical/request differs')
                    endpoints[policy]=e
                if numerical_digest(endpoints['fixed_200'])!=numerical_digest(endpoints['bounded_800']) or digest(encoded(numerical(endpoints['fixed_200'])))!=pair['numerical_sha256']:raise ValueError('assessment pair numerical digest differs')
        if gate in found:raise ValueError('duplicate assessment acceptance gate')
        found[gate]=reference(ROOT,worker_path)
    if set(found)!={'regular','project','memcheck','racecheck','initcheck','synccheck'}:raise ValueError('assessment missing exact-source acceptance '+str(sorted(set(['regular','project','memcheck','racecheck','initcheck','synccheck'])-set(found))))
    return found

def main():
    p=argparse.ArgumentParser();p.add_argument('action',choices=['project']);a=p.parse_args();project(protocol())
if __name__=='__main__':main()
