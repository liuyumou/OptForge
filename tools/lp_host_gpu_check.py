"""Fixed-work GPUP-HOST old/new equivalence and replay; never primary timing."""
import os
from pathlib import Path
import subprocess
import time
from benchmark_lp_host import instances, endpoint_shape
from lp_host_budget import protocol
from lp_protocol import ROOT, checked_reference, file_hash, read_json, write_json
from report_lp_copt import numerical_digest


def main():
    if os.environ.get('AI_OPTIMIZER_GPU_LEASE') != 'inherited':
        raise ValueError('shared host lease required')
    value = protocol(); models = instances(value); archive = ROOT / value['output']
    binaries = {'baseline': archive / 'optimizer-baseline', 'repaired': archive / 'optimizer'}
    directory = ROOT / value['acceptance_output'] / ('cli-' + str(time.time_ns()))
    directory.mkdir(parents=True, exist_ok=False)
    write_json(directory / 'solve.json', dict(value['solve'], iteration_limit=value['acceptance_work']))
    write_json(directory / 'method.json', dict(value['lp_settings'], iteration_limit=value['acceptance_work']))
    report = dict(schema_version=1, binaries={k: file_hash(b) for k, b in binaries.items()}, pairs=[], replays=[], status='incomplete')
    env = dict(os.environ, AI_OPTIMIZER_CUDA_DIR=str(archive))

    def call(binary, args):
        result = subprocess.run([str(binary), *map(str, args)], env=env, capture_output=True, text=True, timeout=30)
        if result.returncode not in (0, 1, 2):
            raise ValueError(result.stderr)
        return result

    def check(path, model):
        endpoint = endpoint_shape(path, 'compact-v1')
        for binary in binaries.values():
            result = call(binary, ['lp-study', 'verify', '--model', model, '--evidence', path])
            if result.returncode:
                raise ValueError('independent verification: ' + result.stderr)
        if endpoint['record']['backend'] != 'cuda-lp-tuned' or endpoint['record']['termination'] in ('interrupted', 'time_limit'):
            raise ValueError('fixed-work fallback/deadline changed endpoint')
        return endpoint

    try:
        for name in value['acceptance_instances']:
            model = checked_reference(ROOT, models[name]['model'])
            for config in value['acceptance_configurations']:
                base = ['lp-study', 'solve', '--model', model, '--config', directory / 'solve.json', '--backend', config['backend'],
                        '--device', value['device'], '--lp-settings', directory / 'method.json', '--evidence-format', 'compact-v1']
                for key, flag in [('execution', '--lp-execution'), ('precision', '--lp-precision'), ('adaptive', '--lp-adaptive')]:
                    if key in config:
                        path = directory / (config['id'] + '.' + key + '.json'); write_json(path, config[key]); base += [flag, path]
                endpoints = {}; files = {}
                for variant, binary in binaries.items():
                    path = directory / f'{name}-{config["id"]}-{variant}.json'
                    result = call(binary, [*base, '--lp-evidence', path])
                    if not path.exists():
                        raise ValueError(result.stderr)
                    endpoints[variant] = check(path, model); files[variant] = path
                left, right = endpoints['baseline'], endpoints['repaired']
                if numerical_digest(left) != numerical_digest(right) or left.get('execution') != right.get('execution'):
                    raise ValueError('input reuse changed numerical bits or work')
                report['pairs'].append(dict(instance=name, configuration=config['id'], numerical_sha256=numerical_digest(left),
                                            endpoints={k: dict(path=str(v.relative_to(ROOT)), sha256=file_hash(v)) for k, v in files.items()}))
                replay = directory / f'{name}-{config["id"]}-replay.json'
                result = call(binaries['repaired'], ['lp-study', 'replay', '--model', model, '--evidence', files['baseline'], '--output', replay, '--device', value['device']])
                if not replay.exists():
                    raise ValueError(result.stderr)
                repeated = check(replay, model)
                if numerical_digest(right) != numerical_digest(repeated) or right.get('execution') != repeated.get('execution'):
                    raise ValueError('compact replay changed numerical bits or work')
                report['replays'].append(dict(instance=name, configuration=config['id'], numerical_sha256=numerical_digest(repeated),
                                              endpoint=dict(path=str(replay.relative_to(ROOT)), sha256=file_hash(replay))))
        report['status'] = 'passed'
    finally:
        write_json(directory / 'report.json', report)
    write_json(ROOT / value['acceptance_output'] / 'cli-host.json', report)
    print('Six old/new fixed-work pairs and six compact replays passed; 18 endpoints accepted by both verifiers')


if __name__ == '__main__':
    main()
