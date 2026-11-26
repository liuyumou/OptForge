"""Report separate million-nonzero original LPs and auxiliary throughput."""
import argparse
import csv
import json
from pathlib import Path
import re
import statistics
import subprocess
import sys
import unittest

from lp_sp_pricing_million import STUDY, AUX, validate_freeze
from lp_sp_pricing_budget import BASE, ROOT, CPU, GPU, NS, accounting, binding, put
from lp_sp_pricing_gpu_opt_compare import read
from lp_sp_pricing_gpu_opt_report import bindings
from lp_sp_pricing_report import resource_summary
from lp_sp_pricing_finish import identities, still_same_process


def report(identity):
    f = validate_freeze(); out = BASE / identity; out.mkdir(exist_ok=False)
    auxiliary = read(STUDY / 'auxiliary-audit.json')
    original = read(STUDY / 'original-results.json')
    checked = bindings(auxiliary) + bindings(original)
    expected = len(f['auxiliary_cells'])//2
    if len(auxiliary['pairs']) + len({r['cell'].rsplit('-', 1)[0] for r in auxiliary['failures']}) != expected:
        raise RuntimeError('incomplete auxiliary dispositions')
    if len(original['rows']) != len(f['original_models'])*f['original_repetitions']:
        raise RuntimeError('incomplete original roster')
    groups = []
    for spec in AUX:
        for storage in ('dense', 'csr'):
            for width in (64, 256, 1000):
                rows = [r for r in auxiliary['pairs'] if r['case'] == spec['name']
                        and r['storage'] == storage and r['width'] == width]
                if not rows: continue
                med = statistics.median
                groups.append(dict(case=spec['name'], storage=storage, width=width, repetitions=len(rows),
                    coefficient_positions=spec['r']*spec['s'], nonzeros=spec['r']*spec['degree'],
                    lean_device_ms=med(r['lean']['device_ms'] for r in rows),
                    wave_device_ms=med(r['wave']['device_ms'] for r in rows),
                    device_ratio=med(r['lean']['device_ms']/r['wave']['device_ms'] for r in rows),
                    lean_cold_seconds=med(r['lean_process_ns']/NS for r in rows),
                    wave_cold_seconds=med(r['wave_process_ns']/NS for r in rows),
                    cold_ratio=med(r['lean_process_ns']/r['wave_process_ns'] for r in rows),
                    lean_preparation_seconds=med(r['lean']['preparation_ns']/NS for r in rows),
                    wave_preparation_seconds=med(r['wave']['preparation_ns']/NS for r in rows)))
    checker = []
    for spec in AUX:
        rows = [r for r in auxiliary['checks'] if r['case'] == spec['name']]
        if not rows: continue
        checker.append(dict(case=spec['name'], samples=len(rows), coverage_equal=all(r['coverage_equal'] for r in rows),
            median_gmp_ms=statistics.median(r['gmp_ns']/1e6 for r in rows),
            median_interval_ms=statistics.median(r['interval_ns']/1e6 for r in rows),
            median_ratio=statistics.median(r['gmp_ns']/r['interval_ns'] for r in rows),
            gmp_fallbacks=sum(r['interval']['gmp_fallbacks'] for r in rows)))
    result = dict(status='million_scale_experiments_audited', freeze=binding(STUDY / 'freeze.json'),
        auxiliary_audit=binding(STUDY / 'auxiliary-audit.json'), original_audit=binding(STUDY / 'original-results.json'),
        groups=groups, checker=checker, original=original['rows'], capacity=read(STUDY / 'capacity.json')['rows'],
        failed_auxiliary_cells=auxiliary['failures'], checked_bindings=checked,
        limitations=f['limitations'], resources=resource_summary())
    put(out / 'result.json', result)
    (ROOT / 'docs/benchmarks/lp-sp-pricing-million-results.json').write_text(json.dumps(result, indent=2, sort_keys=True)+'\n')
    with (ROOT / 'docs/benchmarks/lp-sp-pricing-million-auxiliary.csv').open('w', newline='') as stream:
        if groups:
            writer = csv.DictWriter(stream, fieldnames=list(groups[0])); writer.writeheader(); writer.writerows(groups)
    lines = ['# Million-scale pricing experiments', '',
        'The original-LP cohort contains three matrices with exactly **1,000,000 nonzeros** each. The current candidate cannot execute them: its original explicit-geometry guard rejects all three before numerical work. COPT is attempted on all three with two cold repetitions. Separate auxiliary experiments measure the admitted GPU kernels at their one-million-coefficient capacity.', '',
        'See the [complete results](lp-sp-pricing-million-results.json), [auxiliary table](lp-sp-pricing-million-auxiliary.csv), [settled checkpoint](lp-sp-pricing-million-checkpoint.json), and [previous small-LP comparison](lp-sp-pricing-wave-policy.md).', '',
        '## Original LPs', '',
        'The fresh seed is 121951. Coefficients and construction certificates are exact dyadic values; each planted optimum passes the unchanged independent original-model 1e-9 checker before the comparison. Construction witnesses are never passed to COPT. All variables are free. The retained COPT scale-off GPU-PDLP configuration receives 30 native seconds and a 45-second outer process allowance. This is not automatic COPT configuration.', '',
        '| Model | Rows | Columns | Nonzeros | Initial geometry entries / cap | Paired basis entries / cap |',
        '| --- | ---: | ---: | ---: | ---: | ---: |']
    for m in f['original_models']:
        cap=m['capacity']; lines.append(f"| {m['name']} | {m['m']} | {m['n']} | {m['nonzeros']} | {cap['geometry_entries']} / 100000 | {cap['paired_entries']} / 1000000 |")
    lines += ['', 'CPU and opportunistic-GPU candidate slots remain visible as unsupported capacity. The preflight calls the actual unchanged guard with dimension-only inputs; it neither constructs an invalid dense input nor changes admission limits. No candidate solve time or candidate/COPT speedup is reported.', '',
        '| Model / repetition | COPT status | GPU startup logged | Timely strict acceptance | Native s | Complete s |',
        '| --- | ---: | --- | --- | ---: | ---: |']
    for r in original['rows']:
        native='—' if r['native_ns'] is None else f"{r['native_ns']/NS:.3f}"
        lines.append(f"| {r['model']} / {r['repetition']} | {r['status']} | {r['gpu_confirmed']} | {r['timely'] and r['accepted']} | {native} | {r['complete_ns']/NS:.3f} |")
    lines += ['', 'Complete time includes original encoding, cold process startup, import/CSR-to-CSC conversion, internal GPU setup and solve, teardown, output and the independent endpoint audit. Construction-certificate validation and resource monitoring are separately charged. Vendor status 1 means numerical optimality; independent strict acceptance is reported separately. Internal device preparation remains inside the opaque COPT solve call.', '',
        '## Auxiliary throughput', '',
        'Fresh synthetic bounded auxiliary LPs use one million coefficient positions. Dense-square (1000×1000) and dense-wide (500×2000) contain one million nonzeros. Sparse-wide (500×2000) contains **16,000 nonzeros**, not one million. These matrices are not original-LP calibrated bases and have no opposite-slot separation assumption.', '',
        'Each cold process constructs the same rational input and runs 128 FP64 PDHG steps. Widths are 64, 256 and 1000 distinct signed objectives. Lean runs active batches of at most 64; wave advances all states at common steps. Three alternating repetitions cover both dense and CSR storage. CUDA-event time excludes setup and transfers. Cold auxiliary process time includes generation, preparation, execution, downloads, teardown and state-file publication; it excludes subsequent checking and is not complete original-LP solve time.', '',
        '| Case / storage | Searches | Lean device ms | Wave device ms | Device speedup | Lean cold s | Wave cold s | Cold speedup |',
        '| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |']
    for g in groups:
        lines.append(f"| {g['case']} / {g['storage']} | {g['width']} | {g['lean_device_ms']:.3f} | {g['wave_device_ms']:.3f} | {g['device_ratio']:.3f}× | {g['lean_cold_seconds']:.3f} | {g['wave_cold_seconds']:.3f} | {g['cold_ratio']:.3f}× |")
    lines += ['', 'Ratios are medians of matched repetitions; values above one favor wave. The CSV also retains preparation times. Failed or missing cells remain in the evidence and never become successful pairs.', '',
        '## Host checks and numerical audit', '',
        'The audit compares every returned primal and dual state between paired implementations at normalized tolerance 1e-12. Two objectives per matrix/storage pair also use independent NumPy equations at 1e-10. These are numerical implementation comparisons, not certificate tolerances.', '',
        'Four evenly spaced proposals from every paired wave cell receive interval/GMP checking, with identical inputs and resolution order. All interval decisions must be established by GMP. Context construction is shared and excluded from checker-only timings; original rational threshold tests remain exact. The final endpoint checker remains at 1e-9.', '',
        '| Case | Check batches | GMP ms | Interval/GMP ms | Speedup | Same label coverage | GMP fallbacks |',
        '| --- | ---: | ---: | ---: | ---: | --- | ---: |']
    for c in checker:
        lines.append(f"| {c['case']} | {c['samples']} | {c['median_gmp_ms']:.3f} | {c['median_interval_ms']:.3f} | {c['median_ratio']:.3f}× | {c['coverage_equal']} | {c['gmp_fallbacks']} |")
    lines += ['', f"Audited auxiliary pairs: {len(auxiliary['pairs'])}/{expected}; failed cells: {len(auxiliary['failures'])}. Independent scalar comparisons: {len(auxiliary['scalar'])*2}; sampled proposal slots: {sum(len(c['sampled_slots']) for c in auxiliary['checks'])}.", '',
        'This study does not demonstrate million-scale complete-solve capability for the candidate. The next original-LP scaling barrier is explicit rational geometry and the mixed optimality reduction, which can become dense even for sparse original input. Increasing a GPU batch cap alone cannot resolve it. All numerical source hashes, prior failures and study budgets remain unchanged.', '']
    (ROOT / 'docs/benchmarks/lp-sp-pricing-million.md').write_text('\n'.join(lines))
    return result


def verify_all(identity):
    report(identity)
    for path in (ROOT / 'tools').glob('lp_sp_pricing_million*.py'):
        compile(path.read_text(), str(path), 'exec')
    suite = unittest.defaultTestLoader.discover(str(ROOT / 'tests/integration'), 'test_lp_sp_pricing*.py')
    outcome = unittest.TextTestRunner(verbosity=2).run(suite)
    if not outcome.wasSuccessful() or outcome.skipped or outcome.testsRun != 72:
        raise RuntimeError('incomplete final tests')
    docs = subprocess.run([sys.executable, '-B', str(ROOT / 'tools/build_docs.py')], check=True,
                          cwd=ROOT, text=True, capture_output=True)
    print(docs.stdout, end='', flush=True)
    match = re.search(r'documentation built: (\d+) pages', docs.stdout)
    if not match: raise RuntimeError('missing documentation receipt')
    subprocess.run(['git', 'diff', '--check'], cwd=ROOT, check=True)
    put(BASE / identity / 'verification.json', dict(status='passed', tests=outcome.testsRun,
        documentation_pages=int(match[1]), result=binding(BASE / identity / 'result.json'),
        outputs=[binding(ROOT / 'docs/benchmarks' / n) for n in ['lp-sp-pricing-million.md',
            'lp-sp-pricing-million-results.json', 'lp-sp-pricing-million-auxiliary.csv']]))


def settle(identity, reservation):
    validate_freeze()
    verification = BASE / identity / 'verification.json'; bindings(read(verification))
    summary = resource_summary()
    if summary['pending_at_snapshot']: raise RuntimeError('active reservation')
    receipt = BASE / 'resources' / (reservation + '.settlement.json')
    if read(receipt)['status'] != 'passed': raise RuntimeError('verification reservation failed')
    cpu, gpu = accounting(BASE), accounting(BASE, True)
    if any(cpu[p] > CPU[p]*NS or gpu[p] > GPU[p]*NS for p in CPU): raise RuntimeError('phase cap')
    owned = set()
    for pattern in ('*.resource.json', '*.journal.json'):
        for path in (BASE / 'resources').glob(pattern): owned.update(identities(read(path)))
    if any(still_same_process(*p) for p in owned): raise RuntimeError('owned process remains')
    checkpoint = dict(status='million_scale_settled', resources=summary, cpu_phase_ns=cpu, gpu_phase_ns=gpu,
        verification=binding(verification), reporting_settlement=binding(receipt),
        tests=read(verification)['tests'], documentation_pages=read(verification)['documentation_pages'],
        owned_identities=len(owned), live_owned_identities=[], active_reservations=[])
    put(BASE / identity / 'settled-checkpoint.json', checkpoint)
    target = ROOT / 'docs/benchmarks/lp-sp-pricing-million-checkpoint.json'
    target.write_text(json.dumps(checkpoint, indent=2, sort_keys=True)+'\n')
    (ROOT / 'book/docs/benchmarks' / target.name).write_bytes(target.read_bytes())
    print(json.dumps(dict(status=checkpoint['status'], cpu_seconds=summary['cpu_ns']/NS,
        gpu_seconds=summary['gpu_ns']/NS, owned_identities=len(owned))), flush=True)


if __name__ == '__main__':
    p=argparse.ArgumentParser(); p.add_argument('action', choices=['verify', 'settle']); p.add_argument('identity')
    p.add_argument('--reservation'); a=p.parse_args()
    if a.action == 'verify': verify_all(a.identity)
    else: settle(a.identity, a.reservation)
