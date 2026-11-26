"""Seal completed scale verification without regrading failed supervision."""
import argparse
import json
from pathlib import Path
import re
from lp_sp_pricing_budget import ROOT, BASE, NS, binding, put
from lp_sp_pricing_gpu_opt_compare import read, verify
from lp_sp_pricing_gpu_opt_report import bindings
from lp_sp_pricing_finish import identities, still_same_process
from lp_sp_pricing_scale_experiment import validate
from lp_sp_pricing_scale_long import validate as validate_long
from lp_sp_pricing_scale_reconstruct import validate as validate_reconstruction
from lp_sp_pricing_scale_report import settle as settle_report

FAILED = BASE/'resources/scale-final-verify-v1'
REPORT = BASE/'scale-report-v1'
OUT = BASE/'scale-final-seal-v1'


def seal():
    validate(); validate_long(); validate_reconstruction()
    receipt = read(str(FAILED)+'.settlement.json')
    resource = read(str(FAILED)+'.resource.json')
    reservation = read(str(FAILED)+'.reservation.json')
    if (receipt['status'] != 'refused' or not receipt['cleanup_empty'] or receipt['overrun']
            or receipt['cpu_ns'] != 2400*NS or receipt['gpu_ns'] != 0
            or reservation['phase'] != 'reporting' or resource['result']['reason'] != 'coordinator_lost'):
        raise RuntimeError('unexpected final verification disposition')
    verify(receipt['resource'])
    for source in reservation['sources']:
        verify({k:source[k] for k in ('path', 'bytes', 'sha256')})
        snapshot = binding(source['retained'])
        if any(snapshot[k] != source[k] for k in ('bytes', 'sha256')):
            raise RuntimeError('retained final verification source changed')
    owned = set(identities(resource)) | set(identities(read(str(FAILED)+'.journal.json')))
    if any(still_same_process(*item) for item in owned):
        raise RuntimeError('recorded verification process remains')
    log = Path(str(FAILED)+'.log').read_text()
    verified = read(REPORT/'verification.json')
    if not re.search(r'Ran 99 tests in [0-9.]+s\s+OK\s', log):
        raise RuntimeError('completed test output missing')
    if 'documentation built: 404 pages; internal links and anchors passed' not in log:
        raise RuntimeError('completed documentation output missing')
    if verified['status'] != 'passed' or verified['tests'] != 99 or verified['documentation_pages'] != 404:
        raise RuntimeError('completed verification receipt missing')
    checked = bindings(verified)+bindings(read(REPORT/'result.json'))
    compile(Path(__file__).read_text(), __file__, 'exec')
    OUT.mkdir(exist_ok=False)
    put(OUT/'result.json', dict(status='completed_verification_sealed', source=binding(__file__),
        tests=99, documentation_pages=404, checked_bindings=checked,
        verification=binding(REPORT/'verification.json'), retained_log=binding(str(FAILED)+'.log'),
        original_failure=binding(str(FAILED)+'.settlement.json'), original_failure_regraded=False,
        original_failure_full_cpu_seconds=2400, reason='coordinator_lost',
        preceding_cause='not established by retained evidence',
        numerical_recomputation=False, owned_identities=len(owned), live_owned_identities=[]))
    print(json.dumps(dict(status='completed_verification_sealed', checked_bindings=checked)), flush=True)


def settle():
    result = read(OUT/'result.json'); bindings(result)
    if result['status'] != 'completed_verification_sealed':
        raise RuntimeError('incomplete read-only seal')
    receipt = BASE/'resources/scale-final-seal-v1.settlement.json'
    if read(receipt)['status'] != 'passed':
        raise RuntimeError('read-only seal supervision failed')
    settle_report('scale-report-v1', 'scale-final-seal-v1')
    completion = dict(status='verification_and_resources_settled', read_only_seal=binding(OUT/'result.json'),
        seal_settlement=binding(receipt), original_failed_settlement=binding(str(FAILED)+'.settlement.json'),
        checkpoint=binding(REPORT/'settled-checkpoint.json'), original_failure_regraded=False,
        repeated_scientific_runs=0, repeated_test_suites=0)
    put(OUT/'settled-checkpoint.json', completion)
    target = ROOT/'docs/benchmarks/lp-sp-pricing-scale-finalization.json'
    target.write_text(json.dumps(completion, indent=2, sort_keys=True)+'\n')
    (ROOT/'book/docs/benchmarks'/target.name).write_bytes(target.read_bytes())


if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('action', choices=['seal', 'settle'])
    args = p.parse_args()
    seal() if args.action == 'seal' else settle()
