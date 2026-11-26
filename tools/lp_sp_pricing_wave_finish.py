"""Read-only seal of completed verification after failed resource finalization."""
import argparse
import json
from pathlib import Path
import re
import subprocess
import sys

from lp_sp_pricing_budget import BASE, ROOT, NS, binding, put
from lp_sp_pricing_finish import identities, still_same_process
from lp_sp_pricing_gpu_opt_compare import read, verify
from lp_sp_pricing_gpu_opt_report import bindings
from lp_sp_pricing_wave_compare import validate_freeze as validate_wave
from lp_sp_pricing_wave_policy import validate_freeze as validate_policy
from lp_sp_pricing_wave_policy_report import settle as settle_policy


REPORT = BASE / 'wave-final-report-v1'
FAILED = BASE / 'resources/wave-final-verify-v1'
OUTPUT = ROOT / 'docs/benchmarks/lp-sp-pricing-wave-finalization.json'


def seal(identity):
    out = BASE / identity
    out.mkdir(exist_ok=False)
    receipt = read(str(FAILED) + '.settlement.json')
    reservation = read(str(FAILED) + '.reservation.json')
    resource = read(str(FAILED) + '.resource.json')
    if (receipt['status'] != 'refused' or not receipt['cleanup_empty']
            or receipt['overrun'] or receipt['cpu_ns'] != 960 * NS
            or receipt['gpu_ns'] != 0 or reservation['phase'] != 'reporting'
            or resource['result']['reason'] != 'coordinator_lost'):
        raise RuntimeError('unexpected original finalization disposition')
    verify(receipt['resource'])
    for item in reservation['sources']:
        verify({k: item[k] for k in ('path', 'bytes', 'sha256')})
        retained = binding(item['retained'])
        if any(retained[k] != item[k] for k in ('bytes', 'sha256')):
            raise RuntimeError('retained verification source changed')
    owned = set(identities(resource)) | set(identities(read(str(FAILED) + '.journal.json')))
    if any(still_same_process(*item) for item in owned):
        raise RuntimeError('previous verification process remains')
    log = Path(str(FAILED) + '.log').read_text()
    if not re.search(r'Ran 67 tests in [0-9.]+s\s+OK\s', log):
        raise RuntimeError('completed test output missing')
    if 'documentation built: 400 pages; internal links and anchors passed' not in log:
        raise RuntimeError('completed documentation output missing')
    checked = 0
    for directory in (REPORT, REPORT / 'wave'):
        result = read(directory / 'verification.json')
        if result['status'] != 'passed' or result['tests'] != 67 or result['documentation_pages'] != 400:
            raise RuntimeError('completed verification record missing')
        checked += bindings(result)
        checked += bindings(read(directory / 'result.json'))
    wave = validate_wave(BASE / 'wave-confirmation-v1/freeze.json')
    policy = validate_policy(BASE / 'wave-policy-confirmation-v1/freeze.json')
    if len(wave['cells']) != 56 or len(policy['cells']) != 42:
        raise RuntimeError('frozen cohort changed')
    compile(Path(__file__).read_text(), __file__, 'exec')
    subprocess.run(['git', 'diff', '--check'], cwd=ROOT, check=True)
    docs = subprocess.run([sys.executable, '-B', str(ROOT / 'tools/build_docs.py')],
                          cwd=ROOT, check=True, text=True, capture_output=True)
    print(docs.stdout, end='', flush=True)
    if 'documentation built: 400 pages; internal links and anchors passed' not in docs.stdout:
        raise RuntimeError('updated documentation did not verify')
    put(out / 'result.json', dict(
        status='completed_verification_sealed', numerical_recomputation=False,
        original_resource_failure_retained=True, previous_reason='coordinator_lost',
        preceding_cause='not established by retained evidence',
        tests=67, documentation_pages=400, checked_bindings=checked,
        original_owned_identities=len(owned), live_original_owned_identities=[],
        source=binding(__file__), retained_failure=binding(str(FAILED) + '.settlement.json'),
        retained_log=binding(str(FAILED) + '.log'),
        completed_verification=binding(REPORT / 'verification.json'),
        completed_wave_verification=binding(REPORT / 'wave/verification.json')))
    print(json.dumps(dict(status='completed_verification_sealed', checked_bindings=checked)), flush=True)


def settle(identity, reservation):
    result_path = BASE / identity / 'result.json'
    result = read(result_path)
    if result['status'] != 'completed_verification_sealed':
        raise RuntimeError('read-only seal did not complete')
    bindings(result)
    receipt_path = BASE / 'resources' / (reservation + '.settlement.json')
    if read(receipt_path)['status'] != 'passed':
        raise RuntimeError('read-only seal supervision did not pass')
    settle_policy('wave-final-report-v1', reservation)
    completion = dict(status='verification_and_resources_settled',
        read_only_seal=binding(result_path), seal_settlement=binding(receipt_path),
        original_failed_settlement=binding(str(FAILED) + '.settlement.json'),
        policy_checkpoint=binding(REPORT / 'settled-checkpoint.json'),
        wave_checkpoint=binding(REPORT / 'wave/settled-checkpoint.json'),
        original_failure_regraded=False, repeated_scientific_runs=0)
    put(BASE / identity / 'settled-checkpoint.json', completion)
    OUTPUT.write_text(json.dumps(completion, indent=2, sort_keys=True) + '\n')
    (ROOT / 'book/docs/benchmarks' / OUTPUT.name).write_bytes(OUTPUT.read_bytes())


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['seal', 'settle'])
    parser.add_argument('identity')
    parser.add_argument('--reservation')
    args = parser.parse_args()
    if args.action == 'seal':
        seal(args.identity)
    else:
        settle(args.identity, args.reservation)
