"""Leased fixed-work format/replay acceptance for SPEC-0015, never timing evidence."""
import os
from pathlib import Path
import subprocess
import time
from benchmark_lp import source_identity
from benchmark_lp_evidence import instances
from lp_evidence_budget import protocol
from lp_protocol import ROOT, checked_reference, file_hash, read_json, write_json
from report_lp_copt import numerical_digest
from validate_artifacts import validator


def main():
    if os.environ.get('AI_OPTIMIZER_GPU_LEASE') != 'inherited':
        raise ValueError('shared host lease required')
    value = protocol(); models = instances(value)
    directory = ROOT / value['acceptance_output'] / ('cli-' + str(time.time_ns()))
    directory.mkdir(parents=True, exist_ok=False)
    binary = ROOT / 'target/release/optimizer'
    method = dict(value['lp_settings'], iteration_limit=value['acceptance_work'])
    solve = dict(value['solve'], iteration_limit=value['acceptance_work'])
    write_json(directory / 'solve.json', solve); write_json(directory / 'method.json', method)
    report = dict(schema_version=1, source_tree_sha256=source_identity(), binary_sha256=file_hash(binary), pairs=[], replays=[], status='incomplete')

    def call(args):
        result = subprocess.run([str(binary), *map(str, args)], capture_output=True, text=True, timeout=30)
        if result.returncode not in (0, 1, 2):
            raise ValueError(result.stderr)
        return result

    def check(path, model, fmt):
        data = read_json(path)
        validator('lp-compact-endpoint-v1.schema.json' if fmt == 'compact-v1' else f'lp-endpoint-v{data["schema_version"]}.schema.json').validate(data)
        endpoint = data['endpoint'] if fmt == 'compact-v1' else data
        result = call(['lp-study', 'verify', '--model', model, '--evidence', path])
        if result.returncode or endpoint['record']['backend'] != 'cuda-lp-tuned':
            raise ValueError('verification/fallback: ' + result.stderr)
        if endpoint['record']['termination'] in ('interrupted', 'time_limit'):
            raise ValueError('fixed-work acceptance deadline became binding')
        return endpoint

    try:
        for name in value['acceptance_instances']:
            model = checked_reference(ROOT, models[name]['model'])
            for config in value['acceptance_configurations']:
                base = ['lp-study', 'solve', '--model', model, '--config', directory / 'solve.json', '--backend', config['backend'],
                        '--device', value['device'], '--lp-settings', directory / 'method.json']
                for key, flag in [('execution', '--lp-execution'), ('precision', '--lp-precision'), ('adaptive', '--lp-adaptive')]:
                    if key in config:
                        path = directory / (config['id'] + '.' + key + '.json'); write_json(path, config[key]); base += [flag, path]
                endpoints = {}; files = {}
                for fmt in ['legacy', 'compact-v1']:
                    path = directory / f'{name}-{config["id"]}-{fmt}.json'
                    result = call([*base, '--lp-evidence', path, '--evidence-format', fmt])
                    if not path.exists():
                        raise ValueError(result.stderr)
                    endpoints[fmt] = check(path, model, fmt); files[fmt] = path
                left, right = endpoints['legacy'], endpoints['compact-v1']
                if numerical_digest(left) != numerical_digest(right) or left.get('execution') != right.get('execution'):
                    raise ValueError('format changed numerical bits or device work')
                report['pairs'].append(dict(instance=name, configuration=config['id'], digest=numerical_digest(left),
                                            legacy_sha256=file_hash(files['legacy']), compact_sha256=file_hash(files['compact-v1'])))
                replay = directory / f'{name}-{config["id"]}-replay.json'
                result = call(['lp-study', 'replay', '--model', model, '--evidence', files['compact-v1'], '--output', replay, '--device', value['device']])
                if not replay.exists():
                    raise ValueError(result.stderr)
                repeated = check(replay, model, 'compact-v1')
                if numerical_digest(right) != numerical_digest(repeated) or right.get('execution') != repeated.get('execution'):
                    raise ValueError('compact replay changed numerical bits or device work')
                report['replays'].append(dict(instance=name, configuration=config['id'], digest=numerical_digest(repeated), endpoint_sha256=file_hash(replay)))
        report['status'] = 'passed'
    finally:
        write_json(directory / 'report.json', report)
    write_json(ROOT / value['acceptance_output'] / 'cli-evidence.json', dict(report=dict(path=str((directory / 'report.json').relative_to(ROOT)), sha256=file_hash(directory / 'report.json'))))
    print('Six fixed-work format pairs and six compact replays passed; all 18 endpoints independently verify')


if __name__ == '__main__':
    main()
