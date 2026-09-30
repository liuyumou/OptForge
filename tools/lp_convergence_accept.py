"""ADR-0032 fixed-work profiles/replay and independent COPT min/max acceptance."""
import argparse
import copy
import os
from pathlib import Path
import subprocess
from benchmark_lp import reference
from benchmark_lp_convergence import instances, endpoint_shape
from lp_copt_adapter_accept import environment
from lp_convergence_budget import protocol
from lp_protocol import ROOT, checked_reference, file_hash, read_json, write_json
from lp_cost import validate_profile
from report_lp_copt import numerical_digest


def call(command, env=None, timeout=120):
    result = subprocess.run(list(map(str, command)), env=env, capture_output=True, text=True, timeout=timeout)
    if result.returncode not in (0, 1, 2): raise ValueError(result.stderr[:2000])
    return result


def require_lease(value):
    if os.environ.get('AI_OPTIMIZER_GPU_LEASE') != 'inherited' or os.environ.get('CUDA_VISIBLE_DEVICES') != value['device']:
        raise ValueError('acceptance requires inherited shared host lease and UUID')


def project(value):
    require_lease(value)
    archive = ROOT / value['output']; directory = ROOT / value['acceptance_output'] / 'project'
    directory.mkdir(parents=True, exist_ok=False)
    binary = archive / 'optimizer'; models = instances(value)
    solve = dict(value['solve'], iteration_limit=value['acceptance_work'], time_limit_ms=30000)
    method = dict(value['lp_settings'], iteration_limit=value['acceptance_work'])
    write_json(directory / 'solve.json', solve); write_json(directory / 'method.json', method)
    env = dict(os.environ, AI_OPTIMIZER_CUDA_DIR=str(archive))
    report = dict(status='incomplete', source_tree_sha256=read_json(archive / 'execution.json')['source_tree_sha256'], binary_sha256=file_hash(binary), pairs=[])
    try:
        for name in value['acceptance_instances']:
            model = checked_reference(ROOT, models[name]['model'])
            for config in [c for c in value['configurations'] if c['backend'] == 'cuda-lp-tuned']:
                key = name + '-' + config['id']; endpoints = {}; paths = {}
                args = [binary, 'lp-study', 'solve', '--model', model, '--model-byte-limit', value['model_byte_limit'], '--config', directory / 'solve.json',
                        '--lp-settings', directory / 'method.json', '--backend', config['backend'], '--device', value['device'], '--evidence-format', 'compact-v1']
                for field in ['execution', 'precision', 'adaptive']:
                    if field in config:
                        path = directory / (config['id'] + '.' + field + '.json'); write_json(path, config[field]); args += ['--lp-' + field, path]
                for profile in [False, True]:
                    label = 'on' if profile else 'off'; path = directory / (key + '-' + label + '.json')
                    command = [*args, '--lp-profile', str(profile).lower(), '--lp-evidence', path]
                    if profile: command += ['--cost-profile', directory / (key + '.cost.json')]
                    result = call(command, env, 40)
                    (directory / (key + '-' + label + '.stdout')).write_text(result.stdout)
                    (directory / (key + '-' + label + '.stderr')).write_text(result.stderr)
                    endpoints[label] = endpoint_shape(path, 'compact-v1'); paths[label] = path
                replay = directory / (key + '-replay.json')
                result = call([binary, 'lp-study', 'replay', '--model', model, '--model-byte-limit', value['model_byte_limit'], '--evidence', paths['off'],
                               '--output', replay, '--device', value['device']], env, 40)
                (directory / (key + '-replay.stdout')).write_text(result.stdout); (directory / (key + '-replay.stderr')).write_text(result.stderr)
                endpoints['replay'] = endpoint_shape(replay, 'compact-v1'); paths['replay'] = replay
                for label, endpoint in endpoints.items():
                    check = call([binary, 'lp-study', 'verify', '--model', model, '--model-byte-limit', value['model_byte_limit'], '--evidence', paths[label]])
                    if check.returncode or endpoint['record']['backend'] != config['backend'] or endpoint['record']['termination'] in ('interrupted', 'time_limit'):
                        raise ValueError('fixed-work endpoint failed independent verification or hit deadline')
                if len({numerical_digest(e) for e in endpoints.values()}) != 1 or any(e['execution'] != endpoints['off']['execution'] for e in endpoints.values()):
                    raise ValueError('profile/replay changed numerical state or executed work')
                validate_profile(read_json(directory / (key + '.cost.json')))
                report['pairs'].append(dict(instance=name, configuration=config['id'], numerical_sha256=numerical_digest(endpoints['off']),
                                           endpoints={label: reference(ROOT, path) for label, path in paths.items()}, cost=reference(ROOT, directory / (key + '.cost.json'))))
        report['status'] = 'passed'
    finally: write_json(ROOT / value['acceptance_output'] / 'project.json', report)
    print('12 fixed-work profile pairs and 12 replays match; 36 endpoints independently verified')


def external(value, gpu):
    if gpu: require_lease(value)
    directory = ROOT / value['acceptance_output']; directory.mkdir(parents=True, exist_ok=True)
    binary = ROOT / value['output'] / 'optimizer'; method = 'copt-gpu-pdlp' if gpu else 'copt-cpu-pdlp'
    config = directory / 'external-solve.json'; write_json(config, dict(value['solve'], time_limit_ms=30000))
    original = read_json(checked_reference(ROOT, instances(value)['gpup-development-irregular-256']['model']))
    results = []
    for sense in ['minimize', 'maximize']:
        doc = copy.deepcopy(original); doc['objective'].update(sense=sense, offset=7.0)
        if sense == 'maximize':
            for t in doc['objective']['terms']: t['coefficient'] = -t['coefficient']
        model = directory / ('accept-' + sense + '.model.json'); write_json(model, doc)
        for profile in [False, True]:
            key = 'accept-' + sense + '-' + method + ('-on' if profile else '-off'); output = directory / (key + '.json')
            if output.exists(): raise ValueError('acceptance endpoint already attempted')
            command = [ROOT / value['copt_python'], '-B', ROOT / 'tools/lp_copt_comparison.py', '--model', model, '--config', config,
                       '--output', output, '--binary', binary, '--method', method, '--device', value['device'] if gpu else 'cpu']
            if profile: command += ['--cost-profile', directory / (key + '.cost.json')]
            result = call(command, environment(value, gpu), 40)
            (directory / (key + '.stdout')).write_text(result.stdout); (directory / (key + '.stderr')).write_text(result.stderr)
            e = read_json(output)
            if result.returncode or e['witness']['executed_backend'] != method or e['assessment']['classification'] != 'certified_success':
                raise ValueError('external acceptance did not certify requested backend')
            check = call([binary, 'lp-study', 'external-verify', '--model', model, '--evidence', output])
            if check.returncode: raise ValueError('external acceptance independent verification failed')
            if profile: validate_profile(read_json(directory / (key + '.cost.json')))
            results.append(dict(sense=sense, method=method, profile=profile, model=reference(ROOT, model), endpoint=reference(ROOT, output), numerical_sha256=numerical_digest(e)))
    for sense in ['minimize', 'maximize']:
        if len({r['numerical_sha256'] for r in results if r['sense'] == sense}) != 1: raise ValueError('COPT profile changed state/work')
    execution = read_json(ROOT / value['output'] / 'execution.json')
    write_json(directory / ('external-gpu.json' if gpu else 'external-cpu.json'), dict(status='passed', source_tree_sha256=execution['source_tree_sha256'],
               binary_sha256=file_hash(binary), dependencies_sha256=value['dependencies']['sha256'], results=results))
    print('4 COPT min/max/profile endpoints independently certify and match')


def check_acceptance(value):
    directory = ROOT / value['acceptance_output']; archive = ROOT / value['output']; execution = read_json(archive / 'execution.json')
    for name, command in [('regular', ['bash', 'tools/lp_setup_gpu_check.sh', 'regular']),
                          ('project', ['python3', '-B', 'tools/lp_convergence_accept.py', 'project']),
                          ('external', ['python3', '-B', 'tools/lp_convergence_accept.py', 'gpu'])]:
        key = value['id'] + '-accept-' + name; path = directory / (key + '.request.json')
        binding = read_json(directory / (key + '.source.json')); worker = read_json(directory / (key + '.worker.json'))
        if binding['source_tree_sha256'] != execution['source_tree_sha256'] or binding['request_sha256'] != file_hash(path) or read_json(path)['command'] != command:
            raise ValueError('acceptance source/request differs')
        if worker['reason'] != 'completed' or worker['returncode'] != 0: raise ValueError('acceptance failed: ' + name)
    data = read_json(directory / 'project.json')
    if data['status'] != 'passed' or data['source_tree_sha256'] != execution['source_tree_sha256'] or data['binary_sha256'] != execution['binary_sha256']:
        raise ValueError('project acceptance identity differs')
    expected = {(i,c['id']) for i in value['acceptance_instances'] for c in value['configurations'] if c['backend']=='cuda-lp-tuned'}
    if len(data['pairs']) != 12 or {(p['instance'],p['configuration']) for p in data['pairs']} != expected: raise ValueError('project acceptance coverage differs')
    for p in data['pairs']:
        if set(p['endpoints']) != {'off','on','replay'}: raise ValueError('acceptance endpoint coverage differs')
        for ref in p['endpoints'].values():
            e = endpoint_shape(checked_reference(ROOT, ref), 'compact-v1')
            if numerical_digest(e) != p['numerical_sha256']: raise ValueError('project acceptance bits differ')
    for name, method in [('external-cpu.json','copt-cpu-pdlp'),('external-gpu.json','copt-gpu-pdlp')]:
        data = read_json(directory / name)
        if data['status'] != 'passed' or data['source_tree_sha256'] != execution['source_tree_sha256'] or data['binary_sha256'] != execution['binary_sha256'] or data['dependencies_sha256'] != value['dependencies']['sha256']:
            raise ValueError('external acceptance identity differs')
        if len(data['results']) != 4 or {(r['sense'],r['profile']) for r in data['results']} != {(s,p) for s in ['minimize','maximize'] for p in [False,True]}:
            raise ValueError('external acceptance coverage differs')
        for r in data['results']:
            checked_reference(ROOT,r['model']); e=read_json(checked_reference(ROOT,r['endpoint']))
            if r['method'] != method or e['witness']['executed_backend'] != method or e['assessment']['classification'] != 'certified_success' or numerical_digest(e) != r['numerical_sha256']:
                raise ValueError('external acceptance bits differ')
    return dict(project_pairs=12,replays=12,external_endpoints=8)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('mode',choices=['project','cpu','gpu']);a=p.parse_args();v=protocol()
    if a.mode=='project':project(v)
    else:external(v,a.mode=='gpu')


if __name__=='__main__':main()
