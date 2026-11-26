"""CPU-only final verification and a post-settlement accounting checkpoint.

The verify action runs through the study supervisor. The settle action performs
only retained-receipt/identity checks and small checkpoint publication after that
reservation has settled. Neither action launches a scientific solve.
"""
import argparse
import json
from pathlib import Path
import re
import subprocess
import sys
import unittest

from lp_sp_pricing_budget import BASE, ROOT, CPU, GPU, NS, accounting, binding, put
from lp_sp_pricing_campaign import read, validate, verify as verify_binding
from lp_sp_pricing_complete_report import report
from lp_sp_pricing_gpu_admission import validate as validate_gpu
from lp_sp_pricing_recover import validated
from lp_sp_pricing_report import resource_summary


def check_bindings(value):
    if isinstance(value, dict):
        if set(value) == {'path', 'bytes', 'sha256'}:
            verify_binding(value)
            return 1
        return sum(check_bindings(v) for v in value.values())
    if isinstance(value, list):
        return sum(check_bindings(v) for v in value)
    return 0


def verify(identity):
    freeze = BASE/'confirmation-v1/freeze.json'
    frozen = read(freeze)
    validate(frozen)
    validated(BASE/'confirmation-recovery-v1/freeze.json')
    validate_gpu(ROOT/'research/lp-sp-pricing/target/release/liblp_sp_pricing.so')
    checked = check_bindings(frozen)
    for name in ['auxiliary-sanitizers-v2', 'flow-market-sanitizers-v1']:
        evidence = read(BASE/name/'binding.json')
        if evidence['status'] != 'passed':
            raise RuntimeError('native CPU admission missing')
        checked += check_bindings(evidence)
    sources = list((ROOT/'research/lp-sp-pricing/python').rglob('*.py'))
    sources += list((ROOT/'tools').glob('lp_sp_pricing_*.py'))
    sources += list((ROOT/'tests/integration').glob('test_lp_sp_pricing*.py'))
    for path in sources:
        compile(path.read_text(), str(path), 'exec')
    suite = unittest.defaultTestLoader.discover(str(ROOT/'tests/integration'), 'test_lp_sp_pricing*.py')
    outcome = unittest.TextTestRunner(verbosity=2).run(suite)
    if not outcome.wasSuccessful() or outcome.testsRun != 38:
        raise RuntimeError('incomplete final component/control acceptance')
    report(identity, freeze)
    result = read(BASE/identity/'result.json')
    checked += check_bindings(result)
    if sum(row['attempted'] for row in result['rows']) != 246:
        raise RuntimeError('an admitted original-LP slot is still untouched')
    if any(not row['attempted'] and row['status'] != 'unsupported_capacity' for row in result['rows']):
        raise RuntimeError('unaccounted original-LP slot')
    docs = subprocess.run([sys.executable, '-B', str(ROOT/'tools/build_docs.py')],
                          cwd=ROOT, check=True, text=True, capture_output=True)
    print(docs.stdout, end='', flush=True)
    match = re.search(r'documentation built: (\d+) pages', docs.stdout)
    if not match:
        raise RuntimeError('documentation verification receipt missing')
    subprocess.run(['git', 'diff', '--check'], cwd=ROOT, check=True)
    untracked = subprocess.check_output(['git', 'ls-files', '--others', '--exclude-standard', '-z'], cwd=ROOT)
    text_count = 0
    for raw in untracked.split(b'\0'):
        if not raw:
            continue
        path = ROOT/raw.decode()
        if path.suffix not in {'.py', '.rs', '.cu', '.cpp', '.h', '.toml', '.md', '.json', '.csv'}:
            continue
        for number, line in enumerate(path.read_text().splitlines(), 1):
            if line.rstrip() != line:
                raise RuntimeError(f'trailing whitespace: {path}:{number}')
        text_count += 1
    put(BASE/identity/'verification.json', dict(status='passed', component_and_control_tests=outcome.testsRun,
        documentation_pages=int(match[1]), evidence_bindings_checked=checked,
        python_sources_compiled=len(sources), untracked_text_files_checked=text_count,
        result=binding(BASE/identity/'result.json'),
        compact_report=binding(ROOT/'docs/benchmarks/lp-sp-pricing-results.json'),
        confirmation_csv=binding(ROOT/'docs/benchmarks/lp-sp-pricing-confirmation.csv')))


def identities(value):
    if isinstance(value, dict):
        if 'pid' in value and 'start_ticks' in value:
            yield int(value['pid']), int(value['start_ticks'])
        for item in value.values():
            yield from identities(item)
    elif isinstance(value, list):
        for item in value:
            yield from identities(item)


def still_same_process(pid, ticks):
    try:
        stat = Path(f'/proc/{pid}/stat').read_text()
    except FileNotFoundError:
        return False
    return int(stat[stat.rfind(')')+2:].split()[19]) == ticks


def settle(identity, reservation):
    summary = resource_summary()
    if summary['pending_at_snapshot']:
        raise RuntimeError('settlement requested with an active reservation')
    cpu, gpu = accounting(BASE), accounting(BASE, True)
    for phase in CPU:
        if cpu[phase] > CPU[phase]*NS or gpu[phase] > GPU[phase]*NS:
            raise RuntimeError('phase limit exceeded')
    owned = set()
    for path in sorted((BASE/'resources').glob('*.settlement.json')):
        receipt = read(path)
        if receipt['resource']:
            verify_binding(receipt['resource'])
            owned.update(identities(read(receipt['resource']['path'])))
    live = sorted((pid, ticks) for pid, ticks in owned if still_same_process(pid, ticks))
    if live:
        raise RuntimeError('recorded owned identities still present: '+str(live))
    final_receipt = BASE/'resources'/(reservation+'.settlement.json')
    if read(final_receipt)['status'] != 'passed':
        raise RuntimeError('final reporting reservation did not pass')
    verification = read(BASE/identity/'verification.json')
    check_bindings(verification)
    result = read(BASE/identity/'result.json')
    checkpoint = dict(schema=2, status='practical_evaluation_settled_reference_literal_unvalidated',
        study='lp-sp-pricing-v1', cpu_ns=summary['cpu_ns'], gpu_ns=summary['gpu_ns'],
        cpu_cap_seconds=sum(CPU.values()), gpu_cap_seconds=sum(GPU.values()),
        cpu_phase_ns=cpu, gpu_phase_ns=gpu, failed_reservations=len(summary['failures']),
        failed_full_cpu_ns=sum(row['cpu_ns'] for row in summary['failures']),
        failed_full_gpu_ns=sum(row['gpu_ns'] for row in summary['failures']),
        failures=summary['failures'], active_reservations=[],
        retained_source_files_verified=summary['retained_source_files_verified'],
        recorded_owned_identities=len(owned), recorded_owned_identities_still_live=[],
        final_component_and_control_tests=verification['component_and_control_tests'],
        documentation_pages=verification['documentation_pages'], native_quality_combinations=224,
        gpu_sanitizers=['memcheck', 'racecheck', 'initcheck', 'synccheck'],
        native_cpu_sanitizers=['ASan', 'UBSan'], completed_batching_cells=167,
        incomplete_batching_cells=1, heldout_original_models=28, confirmation_slots=252,
        attempted_slots=246, capacity_refused_slots=6, lanes=result['lanes'],
        billion_original_solves_run=0, paper_reference_integration_present=True,
        paper_reference_literal_end_to_end_validated=False, broad_end_to_end_superiority=False,
        order_deviation=result['limitations'][1],
        verification=binding(BASE/identity/'verification.json'), final_reporting_resource=binding(final_receipt))
    put(BASE/identity/'settled-checkpoint.json', checkpoint)
    (ROOT/'docs/benchmarks/lp-sp-pricing-checkpoint.json').write_text(json.dumps(checkpoint, indent=2, sort_keys=True)+'\n')
    print(json.dumps({key:checkpoint[key] for key in ['status','cpu_ns','gpu_ns','failed_reservations',
        'recorded_owned_identities','attempted_slots','capacity_refused_slots']}), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['verify', 'settle'])
    parser.add_argument('identity')
    parser.add_argument('--reservation')
    args = parser.parse_args()
    if args.action == 'verify':
        verify(args.identity)
    else:
        settle(args.identity, args.reservation)
