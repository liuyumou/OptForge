"""Source-bound ADR-0035 fixed-work/cache equivalence and replay acceptance."""
import argparse
import os
from pathlib import Path
import subprocess
import struct
from benchmark_lp import source_identity,reference
from benchmark_lp_exec import instances
from lp_exec_budget import protocol,validate_gate_command,ledger_for
from lp_protocol import ROOT,checked_reference,file_hash,read_json,write_json,digest,encoded

def numerical(e):
    w=e['witness']
    return dict(primal=None if w['primal'] is None else [struct.pack('>d',v).hex() for v in w['primal']],dual=None if w['dual'] is None else [struct.pack('>d',v).hex() for v in w['dual']],status=w['status'],failure=w['failure'],proposed=w['proposed_steps'],committed=w['committed_steps'],witness_iteration=w['witness_iteration'],flags=w['rounding_flags'],assessment=e['assessment'])

def project(value,binary):
    if os.environ.get('AI_OPTIMIZER_GPU_LEASE')!='inherited' or os.environ.get('CUDA_VISIBLE_DEVICES')!=value['device']:raise ValueError('project acceptance requires the selected shared lease')
    key=os.environ['AI_OPTIMIZER_EXEC_ACCEPT_KEY'];directory=ROOT/value['acceptance_output']/(key+'-project');directory.mkdir(parents=True,exist_ok=False)
    report=dict(status='incomplete',source_tree_sha256=source_identity(),executable_sha256=file_hash(binary),image_sha256=file_hash(Path(os.environ['AI_OPTIMIZER_CUDA_DIR'])/'lp_pdhg_exec.cubin'),pairs=[])
    models=instances(value)
    try:
        for name in value['acceptance_instances']:
            endpoints={}
            for mode in ['cached','uncached']:
                prefix=name+'-'+mode;model=checked_reference(ROOT,models[name]['model']);request_path=directory/(prefix+'.request.json');endpoint=directory/(prefix+'.endpoint.json')
                request=dict(schema_version=1,mode=mode,model_sha256=models[name]['model']['sha256'],source_tree_sha256=report['source_tree_sha256'],executable_sha256=report['executable_sha256'],code_object_sha256=report['image_sha256'],device=value['device'],options=dict(value['solve'],iteration_limit=value['acceptance_work'],time_limit_ms=30000),method=dict(value['lp_settings'],iteration_limit=value['acceptance_work']),profile=False,device_buffer_bytes=value['limits']['device_buffer_bytes'])
                write_json(request_path,request)
                for action in ['solve','verify','replay']:
                    result=subprocess.run([str(binary),action,str(model),str(request_path),str(endpoint)],capture_output=True,text=True,timeout=35)
                    (directory/(prefix+'.'+action+'.stdout')).write_text(result.stdout);(directory/(prefix+'.'+action+'.stderr')).write_text(result.stderr)
                    if result.returncode:raise ValueError(action+' failed: '+result.stderr[:2000])
                evidence=read_json(endpoint)
                if evidence['witness']['request']!=request or evidence['witness']['committed_steps']!=value['acceptance_work'] or evidence['witness']['status'] not in ['accepted','iteration_limit']:raise ValueError('fixed-work endpoint differs')
                endpoints[mode]=evidence
            if numerical(endpoints['cached'])!=numerical(endpoints['uncached']):raise ValueError('cached/uncached trajectory differs')
            report['pairs'].append(dict(instance=name,numerical_sha256=digest(encoded(numerical(endpoints['cached']))),endpoints={mode:reference(ROOT,directory/(name+'-'+mode+'.endpoint.json')) for mode in endpoints},replays={mode:reference(ROOT,directory/(name+'-'+mode+'.endpoint.json.replay.json')) for mode in endpoints}))
        report['status']='passed'
    finally:write_json(ROOT/value['acceptance_output']/(key+'.project.json'),report)
    print('three cached/uncached fixed-work pairs and six same-device replays pass')

def check_project_request(value,identity,name,mode,request):
    expected=dict(schema_version=1,mode=mode,model_sha256=instances(value)[name]['model']['sha256'],source_tree_sha256=identity['source_tree_sha256'],executable_sha256=identity['exec_binary_sha256'],code_object_sha256=identity['code_object_sha256'],device=value['device'],options=dict(value['solve'],iteration_limit=value['acceptance_work'],time_limit_ms=30000),method=dict(value['lp_settings'],iteration_limit=value['acceptance_work']),profile=False,device_buffer_bytes=value['limits']['device_buffer_bytes'])
    if request!=expected:raise ValueError('project complete request identity differs')

def check_acceptance(value,identity):
    directory=ROOT/value['acceptance_output'];found={}
    ledger_bytes=ledger_for(value).path.read_bytes()
    if not ledger_bytes.endswith(b'\n'):raise ValueError('acceptance ledger is torn')
    from lp_protocol import strict_loads
    events=[strict_loads(line) for line in ledger_bytes.splitlines()]
    for path in sorted(directory.glob('*.gate.json')):
        gate=read_json(path)
        if gate['source_tree_sha256']!=identity['source_tree_sha256'] or gate['status']!='passed':continue
        if gate['image_sha256']!=identity['code_object_sha256']:raise ValueError('acceptance image differs')
        request=read_json(checked_reference(ROOT,gate['request']));worker=read_json(checked_reference(ROOT,gate['worker']))
        ledger_rows=[e for e in events if e['trial_id']==request['prefix']]
        if len(ledger_rows)!=2 or ledger_rows[0]['kind']!='reserve' or ledger_rows[1]['kind']!='settle' or ledger_rows[1]['charged_ns']!=worker['leased_ns'] or any(e['phase']!='repeatability' or e['resource']!='gpu' or e['reserved_ns']!=(request['solve_seconds']+6)*10**9 for e in ledger_rows):raise ValueError('acceptance ledger binding differs')
        if gate['command']!=request['command'] or gate['command'][:1]!=['/usr/bin/env']:raise ValueError('acceptance command differs')
        for ref in [*gate['binaries'],*gate['images'].values()]:checked_reference(ROOT,ref)
        if gate['images']['lp_pdhg_exec.cubin']['sha256']!=identity['code_object_sha256']:raise ValueError('acceptance archived image differs')
        command=gate['command'][3:]
        validate_gate_command(gate['gate'],command)
        stdout=checked_reference(ROOT,gate['stdout']).read_text();stderr=checked_reference(ROOT,gate['stderr']).read_text()
        if 'SKIP ' in stdout+stderr:raise ValueError('acceptance skipped device coverage')
        if gate['gate'] in ['oracle','memcheck','racecheck','initcheck','synccheck'] and '3 passed; 0 failed' not in stdout:raise ValueError('new device suite did not run all cases')
        if gate['gate']=='regular' and stdout.count('test result: ok.')!=3:raise ValueError('regular suites incomplete')
        if worker['reason']!='completed'  or worker['returncode']!=0 or worker['leased_ns']>(request['solve_seconds']+6)*1000000000:raise ValueError('acceptance worker failed')
        if gate['gate']=='project':
            project=read_json(checked_reference(ROOT,gate['project']))
            if project['status']!='passed' or project['source_tree_sha256']!=identity['source_tree_sha256'] or project['executable_sha256']!=identity['exec_binary_sha256'] or project['image_sha256']!=identity['code_object_sha256']:raise ValueError('project acceptance identity differs')
            if [r['instance'] for r in project['pairs']]!=value['acceptance_instances']:raise ValueError('project acceptance roster differs')
            binaries=[checked_reference(ROOT,ref) for ref in gate['binaries'] if ref['sha256']==identity['exec_binary_sha256']]
            if len(binaries)!=1:raise ValueError('project archived verifier differs')
            for pair in project['pairs']:
                endpoints={mode:read_json(checked_reference(ROOT,ref)) for mode,ref in pair['endpoints'].items()}
                for mode,e in endpoints.items():
                    r=e['witness']['request']
                    check_project_request(value,identity,pair['instance'],mode,r)
                    if e['witness']['committed_steps']!=value['acceptance_work']:raise ValueError('project work differs')
                    endpoint=checked_reference(ROOT,pair['endpoints'][mode])
                    request_path=endpoint.with_name(endpoint.name.replace('.endpoint.json','.request.json'))
                    if read_json(request_path)!=r:raise ValueError('project request file differs')
                    model=checked_reference(ROOT,instances(value)[pair['instance']]['model'])
                    for evidence_path in [endpoint,checked_reference(ROOT,pair['replays'][mode])]:
                        result=subprocess.run([str(binaries[0]),'verify',str(model),str(request_path),str(evidence_path)],capture_output=True,text=True,timeout=value['verification_seconds'])
                        if result.returncode or result.stdout.strip()!='verified':raise ValueError('independent project verification failed')
                if numerical(endpoints['cached'])!=numerical(endpoints['uncached']) or digest(encoded(numerical(endpoints['cached'])))!=pair['numerical_sha256']:raise ValueError('project numerical receipt differs')
                for mode,ref in pair['replays'].items():
                    replay=read_json(checked_reference(ROOT,ref))
                    if replay['witness']['request']!=endpoints[mode]['witness']['request'] or numerical(replay)!=numerical(endpoints[mode]):raise ValueError('project replay differs')
        found[gate['gate']]=reference(ROOT,path)
    required={'regular','oracle','memcheck','racecheck','initcheck','synccheck','project'}
    if set(found)!=required:raise ValueError('missing exact-source acceptance: '+str(sorted(required-set(found))))
    return found

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['project']);p.add_argument('--binary',type=Path,required=True);a=p.parse_args();project(protocol(),a.binary)
