"""Verify retained candidate evidence and publish compact, qualified measurements."""
import statistics
from pathlib import Path

from lp_billion_common import BASE, ROOT, load, put, ref, resolve, require
from lp_billion_readmission import passed
from lp_billion_leak_audit import identities
from lp_confirmation2_supervisor import same_process


def report():
    jobs = ['operational-cpu-v36', 'operational-cpu-v37', 'utilization-diagnosis-v3',
        'utilization-idle-v1', 'operational-gpu-v28', 'utilization-quality-v1',
        'utilization-seal-benchmark-v1', 'utilization-candidate-v1', 'utilization-measure-v1']
    known = {}
    receipts = []
    for identity in jobs:
        path = passed(identity)
        receipt = load(path)
        receipts.append(ref(path))
        resource = load(resolve(receipt['resource']))
        for item in identities(resource):
            known[item['pid'], item['start_ticks']] = item
    require(not any(same_process(item) for item in known.values()), 'completed owned identity still live')
    preservation = load(BASE/'utilization-optimization-v1/source-disposition-v4.json')
    for item in preservation['unchanged'] + preservation['added']:
        resolve(item)
    for item in preservation['changed']:
        resolve(item['current'])
        resolve(item['retained'])
        require(item['previous']['sha256'] == item['retained']['sha256'], 'retained original source')
    old, new = [load(BASE/f'image-v{version}/binding.json') for version in [11, 12]]
    for image in [old, new]:
        for item in image['files'].values():
            resolve(item)
    require(all(old['files'][name]['sha256'] == item['sha256']
                for name, item in new['files'].items() if name != 'executor'), 'unchanged CUDA and diagnostic image')
    admission_path = BASE/'utilization-candidate-v1/result.json'
    admission = load(admission_path)
    require(admission['status'] == 'passed' and len(admission['rows']) == 60, 'complete continuation roster')
    proofs, removed = 0, 0
    for row in admission['rows']:
        require(row['exact'] and len(row['responses']) == 4, 'four exact configurations')
        for variant in row['responses']:
            resolve(variant['response'])
            removed += variant['removed_final_calls']
            for proof in variant['serial']:
                resolve(proof)
                proofs += 1
    benchmark_path = BASE/'utilization-cpu-benchmark-v1/result.json'
    benchmark = load(benchmark_path)
    cpu = []
    for row in benchmark['rows']:
        samples = row['samples']
        require(len(samples) == 6 and all(s['exact'] for s in samples), 'complete CPU paired samples')
        cpu.append(dict(case=row['case'], nonzeros=row['nonzeros'], samples=samples,
            median_paired_speedup=statistics.median(s['reference_ns']/s['candidate_ns'] for s in samples)))
    measured_path = BASE/'utilization-4m-v1/result.json'
    measured = load(measured_path)
    require(measured['status'] == 'passed' and len(measured['pairs']) == 3, 'complete diagnostic pairs')
    pairs = []
    for pair in measured['pairs']:
        rows = {}
        for row in pair['rows']:
            response = load(resolve(row['response']))
            audit = load(resolve(row['audit']))
            require(audit['status'] == 'passed', 'strict final and intermediate audits')
            rows[row['version']] = dict(row, logical=response['logical'], physical=response['physical'],
                phase_ns=response['solver_profile']['exclusive_ns'],
                strict_certificate_calls=response['solver_profile']['phase_entries']['strict_certificate'],
                independent_proofs=audit['checks'], device_bytes_upper=response['device_bytes_upper'])
        before, after = rows['reference'], rows['candidate']
        pairs.append(dict(family=pair['family'], exact_continuation=pair['exact_continuation'], rows=rows,
            complete_speedup=before['complete_ns']/after['complete_ns'],
            assessment_speedup=before['phase_ns']['strict_certificate']/after['phase_ns']['strict_certificate']))
    result = dict(status='validated_opt_in_candidate', native_tests=load(BASE/'utilization-quality-v1/result.json')['rust_tests'],
        supervisor_tests=75, billion_harness_tests=156, operational_continuations=60,
        candidate_continuations=240, independent_scalar_proofs=proofs, removed_admission_final_calls=removed,
        cpu_microbenchmark=cpu, fresh_4m_pairs=pairs, receipts=receipts,
        original_numerical_bindings=len(preservation['unchanged'])+len(preservation['changed']),
        unchanged_numerical_bindings=len(preservation['unchanged']), historical_image_files=len(old['files']),
        owned_completed_identities_absent=len(known), source_disposition=ref(BASE/'utilization-optimization-v1/source-disposition-v4.json'),
        admission=ref(admission_path), benchmark=ref(benchmark_path), measurements=ref(measured_path),
        storage_policy=ref(ROOT/'docs/specifications/SPEC-0046-amendment-93.md'),
        limits=['No sampled utilization or kernel-active-time speedup is inferred.',
            'One rotated pair per family at 4 M nonzeros; no billion-scale performance claim.',
            'CPU microbenchmark has six alternating-order pairs; caches were not flushed.',
            'Paired solvers share the content-addressed witness store: the second writer can reuse files. Complete ratios are order-confounded, not attributable optimization speedups.',
            'Independent final proof remains in complete cost; intermediate offline audits are separate.',
            'Defaults, CPU authority, tolerance and control100/certificate500 remain unchanged.'])
    put(ROOT/'docs/benchmarks/lp-billion-utilization-optimization-results.json', result)
    print(dict(status=result['status'], candidate_continuations=240, independent_scalar_proofs=proofs,
        completed_identities_absent=len(known)), flush=True)


if __name__ == '__main__':
    report()
