"""ADR-0037 scoped acceptance, bound to the frozen study sources and requests."""
import argparse
import re
from pathlib import Path
import subprocess
from lp_protocol import ROOT,checked_reference,file_hash,read_json,write_json
from lp_refine_budget import protocol
from benchmark_lp_refine import instances,prepare_inputs

GATES=['regular','oracle','project','memcheck','racecheck','initcheck','synccheck']

def check_acceptance(value,identity):
    directory=ROOT/value['acceptance_output']
    for gate in GATES:
        key=value['id']+'-accept-'+gate
        binding=read_json(directory/(key+'.source.json'));worker=read_json(directory/(key+'.worker.json'));request=read_json(directory/(key+'.request.json'))
        if binding['gate']!=gate or binding['source_tree_sha256']!=identity['source_tree_sha256'] or binding['request_sha256']!=file_hash(directory/(key+'.request.json')) or worker['reason']!='completed' or worker['returncode']!=0:raise ValueError('acceptance gate/source/worker differs: '+gate)
        command=request['command']
        if command[:2]!=['/usr/bin/env','AI_OPTIMIZER_CUDA_DIR='+str(ROOT/value['output'])]:raise ValueError('acceptance image directory differs')
        from lp_refine_budget import validate_command
        validate_command(gate,command[2:])
        if worker['activity']['device']!=value['device']:raise ValueError('acceptance worker device differs')
        logs=''.join((directory/(key+suffix)).read_text(errors='replace') for suffix in ['.stdout','.stderr'])
        if 'SKIP ' in logs:raise ValueError('device acceptance has skipped coverage: '+gate)
        if gate=='regular' and re.findall(r'test result: ok\. (\d+) passed; 0 failed;',logs)!=['14','6','46']:raise ValueError('regular device acceptance must cover all 66 tests')
        if gate=='oracle' and ('test result: ok. 3 passed; 0 failed;' not in logs or 'refine independent fixture product checks=1920' not in logs):raise ValueError('refine oracle coverage missing')
        if gate in ['memcheck','racecheck','initcheck','synccheck']:
            logs=''.join((directory/(key+suffix)).read_text(errors='replace') for suffix in ['.stdout','.stderr'])
            expected='ERROR SUMMARY: 0 errors' if gate!='racecheck' else 'RACECHECK SUMMARY: 0 hazards'
            if expected not in logs:raise ValueError('sanitizer zero summary missing: '+gate)
        if request['solve_seconds']!=(90 if gate in GATES[3:] else 120):raise ValueError('acceptance deadline differs')
    summary=read_json(directory/'project.json')
    if summary['source_tree_sha256']!=identity['source_tree_sha256'] or summary['pairs']!=9:raise ValueError('project replay coverage/source differs')
    expected={(name,c['id']) for name in value['acceptance_instances'] for c in value['configurations'][1:]}
    if {(p['model'],p['configuration']) for p in summary['artifacts']}!=expected or len(summary['artifacts'])!=9:raise ValueError('project acceptance model/configuration coverage differs')
    configurations={c['id']:c for c in value['configurations']}
    for pair in summary['artifacts']:
        key='accept-'+pair['model']+'-'+pair['configuration'];request_path=directory/(key+'.request.json');endpoint_path=directory/(key+'.endpoint.json');replay_path=Path(str(endpoint_path)+'.replay.json')
        if any(file_hash(path)!=pair[field] for path,field in [(request_path,'request_sha256'),(endpoint_path,'endpoint_sha256'),(replay_path,'replay_sha256')]):raise ValueError('project acceptance artifact binding differs')
        request=read_json(request_path);configuration=configurations[pair['configuration']]
        model=instances(value)[pair['model']]['model']
        if request['width']!=configuration['width'] or request['anchored']!=configuration['anchored'] or request['model_sha256']!=model['sha256'] or request['source_tree_sha256']!=identity['source_tree_sha256'] or request['executable_sha256']!=identity['exec_binary_sha256'] or request['code_object_sha256']!=identity['code_object_sha256'] or request['device']!=value['device'] or request['profile'] or request['method']!=dict(value['lp_settings'],iteration_limit=8) or request['options']!=dict(value['solve'],iteration_limit=8,time_limit_ms=30000):raise ValueError('project acceptance request identity differs')
        endpoint=read_json(endpoint_path);replay=read_json(replay_path)
        if endpoint['witness']['outcome']!=replay['witness']['outcome'] or endpoint['assessment']!=replay['assessment']:raise ValueError('project acceptance replay differs')
        subprocess.run([str(ROOT/value['output']/'lp_precision_refine'),'verify',str(checked_reference(ROOT,model)),str(request_path),str(endpoint_path)],check=True,capture_output=True,timeout=120)

    return True

def project():
    value=protocol();directory=ROOT/value['acceptance_output'];study=ROOT/value['output'];identity=read_json(study/'execution.json');models=instances(value)
    pairs=[]
    for name in value['acceptance_instances']:
        for configuration in value['configurations'][1:]:
            job=dict(kind='profile',instance=models[name],configuration=configuration,id='accept-'+name+'-'+configuration['id'])
            request,documents=prepare_inputs(value,job,study,identity)
            key=job['id'];payload=documents[key+'.refine-request.json'];payload['profile']=False;payload['method']['iteration_limit']=8;payload['options']['iteration_limit']=8;payload['options']['time_limit_ms']=30000
            model=checked_reference(ROOT,models[name]['model']);path=directory/(key+'.request.json');endpoint=directory/(key+'.endpoint.json');write_json(path,payload)
            binary=study/'lp_precision_refine'
            for command in ['solve','verify','replay']:
                subprocess.run([str(binary),command,str(model),str(path),str(endpoint)],check=True,timeout=35)
            # Bind every replay and model/configuration, not only a pair count.
            pairs.append(dict(model=name,configuration=configuration['id'],request_sha256=file_hash(path),endpoint_sha256=file_hash(endpoint),replay_sha256=file_hash(str(endpoint)+'.replay.json')))
    write_json(directory/'project.json',dict(source_tree_sha256=identity['source_tree_sha256'],pairs=len(pairs),artifacts=pairs))

def main():
    p=argparse.ArgumentParser();p.add_argument('command',choices=['project','verify']);a=p.parse_args()
    if a.command=='project':project()
    else:
        value=protocol();check_acceptance(value,read_json(ROOT/value['output']/'execution.json'));print('refine seven acceptance gates verified')

if __name__=='__main__':main()
