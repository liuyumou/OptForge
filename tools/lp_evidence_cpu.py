"""CPU-only compact codec size, durable-write and independent-verification study."""
import argparse
import os
from pathlib import Path
import resource
import subprocess
import time
from benchmark_lp import source_identity
from benchmark_lp_evidence import instances
from lp_evidence_budget import protocol
from lp_protocol import ROOT, checked_reference, file_hash, ordered, read_json, write_json
from validate_artifacts import validator


def usage():
    rows = [resource.getrusage(k) for k in [resource.RUSAGE_SELF, resource.RUSAGE_CHILDREN]]
    return dict(user_seconds=sum(r.ru_utime for r in rows), system_seconds=sum(r.ru_stime for r in rows))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id', default='initial')
    parser.add_argument('--binary', type=Path, default=ROOT / 'target/release/optimizer')
    parser.add_argument('--fixture-binary', type=Path, default=ROOT / 'target/release/examples/lp_evidence_fixture')
    args = parser.parse_args()
    if not args.run_id or Path(args.run_id).name != args.run_id:
        raise ValueError('one new CPU run name required')
    value = protocol(); models = instances(value); start = time.monotonic_ns(); before = usage()
    root = ROOT / value['cpu_output']; directory = root / args.run_id
    directory.mkdir(parents=True, exist_ok=False)
    report = dict(schema_version=1, id='gpup-evidence-cpu-v1-' + args.run_id, status='incomplete',
                  source_tree_sha256=source_identity(), binary_sha256=file_hash(args.binary),
                  fixture_binary_sha256=file_hash(args.fixture_binary), rows=[], commands=[], error=None,
                  limitations=['CPU codec/byte-write diagnostics, not solve latency.',
                               'Retained and synthetic fixtures are derived evidence; no historical solve is retried.',
                               'Write wall includes flush/fsync of already encoded bytes; encoding is excluded.'])
    write_json(directory / 'solve.json', value['solve'])

    def call(command, name):
        elapsed = time.monotonic_ns(); cpu = usage()
        result = subprocess.run(list(map(str, command)), capture_output=True, timeout=value['verification_seconds'])
        duration = time.monotonic_ns() - elapsed; after = usage()
        (directory / (name + '.stdout')).write_bytes(result.stdout)
        (directory / (name + '.stderr')).write_bytes(result.stderr)
        report['commands'].append(dict(command=list(map(str, command)), id=name, returncode=result.returncode,
                                       elapsed_ns=duration, user_seconds=after['user_seconds'] - cpu['user_seconds'],
                                       system_seconds=after['system_seconds'] - cpu['system_seconds']))
        if sum(usage().values()) - sum(before.values()) > value['cpu_cap_seconds']:
            raise ValueError('CPU study budget exhausted')
        if result.returncode:
            raise ValueError(name + ': ' + result.stderr.decode(errors='replace')[:1000])
        return duration

    try:
        for fixture in value['cpu_sources']:
            instance = models[fixture['instance_id']]; name = instance['id']
            model = checked_reference(ROOT, instance['model'])
            if fixture['kind'] == 'retained':
                source = checked_reference(ROOT, fixture['source'])
            else:
                source = directory / (name + '.synthetic.json')
                call([args.fixture_binary, model, directory / 'solve.json', source], name + '-fixture')
            compact = directory / (name + '.compact.json'); restored = directory / (name + '.restored.json')
            base = [args.binary, 'lp-study', 'transcode', '--model', model, '--model-byte-limit', value['model_byte_limit']]
            compact_ns = call([*base, '--evidence', source, '--output', compact, '--evidence-format', 'compact-v1'], name + '-compact')
            restored_ns = call([*base, '--evidence', compact, '--output', restored, '--evidence-format', 'legacy'], name + '-restore')
            envelope = read_json(compact); validator('lp-compact-endpoint-v1.schema.json').validate(envelope)
            if not envelope['validation_sha256'] or not envelope['endpoint']['record'].get('candidate'):
                raise ValueError('CPU fixture must carry a full candidate and reconstructed validation')
            if file_hash(source) != file_hash(restored):
                raise ValueError('legacy serialization bytes changed on compact roundtrip')
            if compact.stat().st_size >= value['limits']['output_bytes']:
                raise ValueError('compact full witness reaches the frozen output cap')
            row = dict(instance_id=name, kind=fixture['kind'], model=instance['model'],
                       source=dict(path=str(source.relative_to(ROOT)), sha256=file_hash(source)),
                       compact=dict(path=str(compact.relative_to(ROOT)), sha256=file_hash(compact)),
                       restored=dict(path=str(restored.relative_to(ROOT)), sha256=file_hash(restored)),
                       payload_sha256=envelope['endpoint']['payload_sha256'], classification=envelope['endpoint']['assessment']['classification'],
                       legacy_bytes=source.stat().st_size, compact_bytes=compact.stat().st_size,
                       candidate_values=len(envelope['endpoint']['record']['candidate']['values']),
                       transcode_ns=compact_ns, restore_ns=restored_ns, roundtrip_bytes_equal=True,
                       measurements=[])
            report['rows'].append(row)
            paths = {'legacy': source, 'compact-v1': compact}
            for repetition in range(value['cpu_repetitions']):
                for config in ordered(value['configurations'], value['order_seed'], name, repetition):
                    fmt = config['evidence_format']; path = paths[fmt]
                    data = path.read_bytes(); copy = directory / f'{name}-{fmt}-{repetition}.bytes.json'
                    started = time.monotonic_ns()
                    with copy.open('xb') as stream:
                        stream.write(data); stream.flush(); os.fsync(stream.fileno())
                    write_ns = time.monotonic_ns() - started
                    del data
                    verify_ns = call([args.binary, 'lp-study', 'verify', '--model', model, '--model-byte-limit', value['model_byte_limit'], '--evidence', copy],
                                     f'{name}-{fmt}-{repetition}-verify')
                    row['measurements'].append(dict(format=fmt, repetition=repetition, bytes=copy.stat().st_size,
                                                    write_ns=write_ns, verification_ns=verify_ns,
                                                    artifact=dict(path=str(copy.relative_to(ROOT)), sha256=file_hash(copy))))
            print(name + ': ' + str(row['legacy_bytes']) + ' -> ' + str(row['compact_bytes']) + ' bytes; full roundtrip and six independent verifications passed', flush=True)
        report['status'] = 'passed'
    except BaseException as error:
        report['status'] = 'failed'; report['error'] = str(error)
        raise
    finally:
        after = usage()
        report.update(elapsed_ns=time.monotonic_ns() - start, cpu={k: after[k] - before[k] for k in before})
        write_json(directory / 'report.json', report)
    write_json(root / 'accepted.json', dict(report=dict(path=str((directory / 'report.json').relative_to(ROOT)), sha256=file_hash(directory / 'report.json'))))


if __name__ == '__main__':
    main()
