"""Offline phase attribution; never equate host phase time with GPU utilization."""
import argparse
import json
from pathlib import Path

from lp_billion_common import ROOT, load, put, ref, resolve
from lp_billion_timing import validate_profile


def summarize(response):
    profile = validate_profile(response)
    costs = profile['exclusive_ns']
    assessments = response['assessments']
    last = assessments[-1] if assessments else None
    same_endpoint = bool(last and last['endpoint'] == response['endpoint'])
    same_certificate = bool(last and last['certificate'] == response['certificate'])
    calls = profile['phase_entries']['strict_certificate']
    # Content descriptors bind the actual original-coordinate vectors. Matching
    # iteration counters alone would incorrectly reuse a rolled-back endpoint.
    duplicate = (response['status'] != 'certified' and same_endpoint
                 and same_certificate and calls == len(assessments) + 1)
    return dict(
        status=response['status'], logical_updates=response['logical'],
        solver_profile_ns=profile['total_ns'], phase_ns=costs,
        advance_host_fraction=costs['device_advance'] / profile['total_ns']
        if profile['total_ns'] else None,
        certificate_entries=calls, intermediate_assessments=len(assessments),
        final_matches_last_endpoint=same_endpoint,
        final_matches_last_certificate=same_certificate,
        duplicate_final_assessment_candidate=duplicate,
        duplicate_duration_ns=None, kernel_active_time_ns=None,
        utilization_percent=None,
    )


def inspect_row(row, cohort, read_response):
    result = dict(cohort=cohort, family=row['family'],
                  lane=row.get('lane', row.get('version')),
                  status=row['status'], response=row.get('response'))
    if not row.get('response'):
        result.update(phase_attribution='unavailable',
                      duplicate_final_assessment_candidate=None)
        return result
    response = read_response(row['response'])
    if 'solver_profile' not in response:
        result['phase_attribution'] = 'opaque_vendor_solve'
        return result
    result.update(summarize(response), phase_attribution='exclusive_host_wall')
    return result


def report():
    sources = [ROOT/'docs/benchmarks'/name for name in [
        'lp-billion-gpu-control-results.json', 'lp-billion-copt-fair-results.json']]
    rows = []
    for cohort in load(sources[0])['cohorts']:
        for row in cohort['cells']:
            if row['version'] == 'v11':
                rows.append(inspect_row(row, 'gpu-control-'+cohort['scale'],
                                        lambda r: load(resolve(r))))
    for row in load(sources[1])['full']['cells']:
        rows.append(inspect_row(row, 'copt-fair-1b', lambda r: load(resolve(r))))
    return dict(
        schema_version=1, status='retained_evidence_diagnosis',
        sources=[ref(p) for p in sources], reader_source=ref(__file__),
        runtime_sources=[ref(ROOT/'research/lp-billion-lowbit/src'/name)
                         for name in ['billion.rs', 'array_assessment.rs',
                                      'bounded_certificate.rs', 'control.rs']],
        rows=rows,
        limitations=[
            'Host phase totals have no timestamped kernel/memory correlation.',
            'Advance includes submission and synchronization, not kernel-active time.',
            'Strict certification includes GPU feasibility and CPU dual/gap work.',
            'Duplicate assessment detection compares retained content descriptors; '
            'deleted raw vectors are not reread or numerically rechecked.',
            'No per-assessment timing exists; do not divide total cost to claim savings.',
            'No runtime change or measured utilization/speed improvement.',
        ],
        new_gpu_seconds=0,
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    result = report()
    put(args.output, result)
    print(json.dumps(dict(rows=len(result['rows']),
        duplicate_candidates=sum(r.get('duplicate_final_assessment_candidate') is True
                                 for r in result['rows']),
        output=str(args.output))))


if __name__ == '__main__':
    main()
