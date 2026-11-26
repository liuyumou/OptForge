"""Seal completed million-scale verification without regrading failed supervision."""
import argparse
import json
from pathlib import Path
import re
import subprocess
import sys

from lp_sp_pricing_budget import BASE, ROOT, NS, binding, put
from lp_sp_pricing_gpu_opt_compare import read, verify
from lp_sp_pricing_gpu_opt_report import bindings
from lp_sp_pricing_finish import identities, still_same_process
from lp_sp_pricing_million import validate_freeze
from lp_sp_pricing_million_report import settle as settle_report

REPORT = BASE / 'million-report-v1'
FAILED = BASE / 'resources/million-final-verify-v1'
OUTPUT = ROOT / 'docs/benchmarks/lp-sp-pricing-million-finalization.json'


def seal(identity):
    out = BASE / identity; out.mkdir(exist_ok=False)
    receipt = read(str(FAILED)+'.settlement.json')
    resource = read(str(FAILED)+'.resource.json')
    reservation = read(str(FAILED)+'.reservation.json')
    if (receipt['status'] != 'refused' or not receipt['cleanup_empty'] or receipt['overrun']
            or receipt['cpu_ns'] != 720*NS or receipt['gpu_ns'] != 0
            or reservation['phase'] != 'reporting' or resource['result']['reason'] != 'coordinator_lost'):
        raise RuntimeError('unexpected original reporting disposition')
    verify(receipt['resource'])
    for item in reservation['sources']:
        verify({k: item[k] for k in ('path', 'bytes', 'sha256')})
        retained = binding(item['retained'])
        if any(retained[k] != item[k] for k in ('bytes', 'sha256')):
            raise RuntimeError('retained verification source changed')
    owned = set(identities(resource)) | set(identities(read(str(FAILED)+'.journal.json')))
    if any(still_same_process(*item) for item in owned):
        raise RuntimeError('previous reporting process remains')
    log = Path(str(FAILED)+'.log').read_text()
    if not re.search(r'Ran 72 tests in [0-9.]+s\s+OK\s', log):
        raise RuntimeError('completed test output missing')
    verified = read(REPORT / 'verification.json')
    if verified['status'] != 'passed' or verified['tests'] != 72 or verified['documentation_pages'] != 401:
        raise RuntimeError('completed verification record missing')
    checked = bindings(verified) + bindings(read(REPORT / 'result.json'))
    validate_freeze()
    compile(Path(__file__).read_text(), __file__, 'exec')
    subprocess.run(['git', 'diff', '--check'], cwd=ROOT, check=True)
    docs = subprocess.run([sys.executable, '-B', str(ROOT / 'tools/build_docs.py')],
                          cwd=ROOT, check=True, text=True, capture_output=True)
    print(docs.stdout, end='', flush=True)
    expected = 'documentation built: 401 pages; internal links and anchors passed'
    if expected not in log or expected not in docs.stdout:
        raise RuntimeError('documentation verification incomplete')
    put(out / 'result.json', dict(status='completed_verification_sealed', tests=72,
        documentation_pages=401, checked_bindings=checked, numerical_recomputation=False,
        original_resource_failure_retained=True, previous_reason='coordinator_lost',
        preceding_cause='not established by retained evidence',
        owned_identities=len(owned), live_owned_identities=[], source=binding(__file__),
        retained_failure=binding(str(FAILED)+'.settlement.json'), retained_log=binding(str(FAILED)+'.log'),
        completed_verification=binding(REPORT / 'verification.json')))
    print(json.dumps(dict(status='completed_verification_sealed', checked_bindings=checked)), flush=True)


def settle(identity, reservation):
    path = BASE / identity / 'result.json'; result = read(path)
    if result['status'] != 'completed_verification_sealed': raise RuntimeError('incomplete seal')
    bindings(result)
    receipt = BASE / 'resources' / (reservation+'.settlement.json')
    if read(receipt)['status'] != 'passed': raise RuntimeError('seal supervision did not pass')
    settle_report('million-report-v1', reservation)
    completion = dict(status='verification_and_resources_settled', read_only_seal=binding(path),
        seal_settlement=binding(receipt), original_failed_settlement=binding(str(FAILED)+'.settlement.json'),
        checkpoint=binding(REPORT / 'settled-checkpoint.json'),
        original_failure_regraded=False, repeated_scientific_runs=0)
    put(BASE / identity / 'settled-checkpoint.json', completion)
    OUTPUT.write_text(json.dumps(completion, indent=2, sort_keys=True)+'\n')
    (ROOT / 'book/docs/benchmarks' / OUTPUT.name).write_bytes(OUTPUT.read_bytes())


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('action', choices=['seal', 'settle']); p.add_argument('identity'); p.add_argument('--reservation')
    a = p.parse_args()
    if a.action == 'seal': seal(a.identity)
    else: settle(a.identity, a.reservation)
