"""CPU-only independent comparison of corrected singles with archived variants.

Re-verifies every admitted control and every selected historical per-solve record.
Writes a new result; never modifies the frozen original study or its analysis.
"""
import argparse
import json
from pathlib import Path
import subprocess
import tempfile
from analyze_lp_throughput import inspect, identity_count, research_bits, tuned_bits
from benchmark_lp_throughput import CONFIG, jobs, label, protocol, settings_for
from lp_protocol import ROOT, checked_reference, file_hash, read_json, write_json

CONTROLS = ROOT / 'benchmarks/configs/lp-throughput-controls-v1.json'


def compare(config=CONTROLS):
    value, base, manifest = protocol(config)
    directory = ROOT / value['output']
    analysis = inspect(directory, config)
    controls = {}
    for job in jobs(value, base, manifest):
        key = label(job)
        path = directory / (key + '.endpoint.json')
        row = next((r for r in analysis['rows'] if r['id'] == key), None)
        if row and row.get('verified') and row.get('process_complete') and row.get('executed'):
            controls[job['instance']['id'], job['config']['id'], job['tier'], job['variant']] = (job, path)
    original, original_base, original_manifest = protocol(CONFIG)
    archive = ROOT / original['output']
    frozen = read_json(archive / 'protocol.json')
    if frozen['protocol'] != original or frozen['jobs'] != list(jobs(original, original_base, original_manifest)):
        raise ValueError('original protocol changed')
    comparisons, missing = [], []
    with tempfile.TemporaryDirectory() as temporary:
        temporary = Path(temporary)
        for job in jobs(original, original_base, original_manifest):
            if job['kind'] != 'batch-variant':
                continue
            key = label(job)
            record_path = archive / (key + '.batch') / 'batch.json'
            if not record_path.is_file():
                missing.append(key)
                continue
            result = read_json(archive / (key + '.result.json'))
            if file_hash(record_path) != result['endpoint_sha256']:
                raise ValueError('original batch changed')
            batch = read_json(record_path)
            for index in (0, 7):
                if index >= job['size']:
                    continue
                partner = controls.get((job['instance']['id'], job['config']['id'], job['tier'], index))
                if partner is None:
                    missing.append(key + '/solve-' + str(index))
                    continue
                control_job, control_path = partner
                model = directory / (label(control_job) + '.model.json')
                summary = batch['solves'][index]
                endpoint_path = record_path.parent / ('solve-%03d.json' % index)
                research = 'mode' in job['config']
                hash_field = 'evidence_sha256' if research else 'endpoint_sha256'
                if (summary['model_sha256'] != file_hash(model)
                        or summary[hash_field] != file_hash(endpoint_path)):
                    raise ValueError('historical variant/endpoint identity changed')
                endpoint, control = read_json(endpoint_path), read_json(control_path)
                if research:
                    request = dict(read_json(archive / (key + '.research.json')))
                    del request['batch']
                    request.update(schema_version=2, model_sha256=file_hash(model))
                    request_path = temporary / 'request.json'
                    write_json(request_path, request)
                    command = [str(directory / 'lp_precision_research'), 'verify', str(model), str(request_path), str(endpoint_path)]
                    bits = research_bits
                else:
                    options, method, _, _ = settings_for(job, original_base, original)
                    record = endpoint['record']
                    if (record['options'] != options or record['lp_settings'] != method
                            or record['lp_execution']['settings'] != job['config']['execution']
                            or record['lp_execution']['code_object_sha256'] != original_base['code_object_sha256']):
                        raise ValueError('historical tuned method/execution differs')
                    command = [str(directory / 'optimizer'), 'lp-study', 'verify', '--model', str(model), '--evidence', str(endpoint_path)]
                    bits = tuned_bits
                verified = subprocess.run(command, capture_output=True, text=True, timeout=120)
                if verified.returncode:
                    raise ValueError('historical variant verification failed: ' + verified.stderr)
                count = identity_count([(bits(endpoint), bits(control))])
                comparisons.append(dict(batch=key, index=index, control=label(control_job),
                                        endpoint_sha256=file_hash(endpoint_path), control_sha256=file_hash(control_path), **count))
    return dict(schema_version=1, control_analysis=analysis, comparisons=comparisons, missing=missing,
                identity_totals={field: sum(row[field] for row in comparisons) for field in ('compared', 'identical')},
                comparison='archived variant sessions vs ordinary fresh single solves; binary64 encodings',
                tool_sha256=file_hash(Path(__file__)))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError('refusing to overwrite analysis')
    result = compare()
    write_json(args.output, result)
    print(json.dumps(dict(controls=result['control_analysis']['verified'], **result['identity_totals'],
                          missing=len(result['missing']))))


if __name__ == '__main__':
    main()
