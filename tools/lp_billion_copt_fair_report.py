"""Compact all outcomes and exact complete costs without ranking uncertified runs."""
import csv
import re
from lp_billion_common import BASE, ROOT, load, put, ref, resolve, require
from lp_billion_copt_fair_policy import FAMILIES


def seconds(value):
    return '—' if value is None else f'{value / 1e9:.3f}'


def outcome(row):
    if row['status'] == 'missing_response' and row.get('supervision_reason'):
        return 'missing response; recorded ' + row['supervision_reason']
    if row['lane'] != 'copt-gpu-pdlp' or not isinstance(row['status'], int): return str(row['status'])
    return {1: 'vendor optimal', 2: 'vendor infeasible', 3: 'vendor unbounded', 4: 'ambiguous',
            5: 'numerical error', 7: 'imprecise', 8: 'time limit', 9: 'unfinished',
            10: 'interrupted', 11: 'iteration limit', 12: 'memory limit'}.get(row['status'], str(row['status']))


def prune_completed():
    """Honor the retained tall proof seal without regrading its failed audits."""
    from lp_billion_full_report import record
    from lp_billion_copt_fair_recovery_v2 import CELL, recovered_record
    from lp_billion_copt_fair_headroom import MANIFEST
    from lp_billion_copt_fair_run import cleanup
    from lp_billion_prepare_continue import completed
    require(completed('copt-fair-tall-proof-seal-v1'), 'retained tall proof seal passed')
    frozen = load(MANIFEST)
    for cell in frozen['cells']:
        recovered_record(cell) if cell['id'] == CELL else record(cell)
    bindings = load(BASE / 'gpu-control-settled-checkpoint-v1.json')['numerical_bindings']
    protected = {resolve(item).resolve() for item in bindings}
    cleanup('1b', 'degenerate')
    root = BASE / 'objects'; deleted = []
    for path in sorted(root.iterdir()):
        if path.suffix != '.bin' or path.stat().st_size < 8 << 20: continue
        require(not path.is_symlink() and path.resolve().parent == root.resolve()
                and len(path.stem) == 64 and all(c in '0123456789abcdef' for c in path.stem), 'exact owned obsolete large object')
        require(path.resolve() not in protected, 'preserve all numerical bindings')
        deleted.append(dict(name=path.name, bytes=path.stat().st_size)); path.unlink()
    put(BASE / 'copt-fair-final-large-object-prune-v1.json', dict(status='obsolete_completed_and_failed_attempt_large_objects_deleted',
        deleted=deleted, released_bytes=sum(p['bytes'] for p in deleted), source=ref(__file__),
        tall_proof_seal=ref(BASE / 'copt-fair-tall-proof-seal-v1/result.json'),
        failed_cleanup=ref(BASE / 'resources/copt-fair-prune-1b-degenerate-v1.settlement.json'),
        all_small_results_and_failures_preserved=True, replay_requires_regeneration=True))


def main():
    destination = ROOT / 'docs/benchmarks/lp-billion-copt-fair-results.json'
    require(not destination.exists(), 'fresh complete comparison report')
    path = BASE / 'copt-fair-results-v1.json'; full = load(path)
    require(full['status'] == 'all_fair_comparison_outcomes_retained', 'complete full comparison')
    frozen = load(resolve(full['freeze']))
    require(len(full['cells']) == 12 and len(full['comparisons']) == 6, 'retain every family and lane slot')
    for row in full['cells']:
        identity = row['id']; journal = BASE / identity / 'response.phases.jsonl'
        if row.get('settlement'):
            settled = load(resolve(row['settlement']))
            if settled['status'] != 'passed':
                resource = load(resolve(settled['resource']))
                row['supervision_reason'] = resource.get('result', {}).get('reason')
        if journal.exists(): row['durable_phase_journal'] = ref(journal)
        if identity == 'copt-fair-1b-v1-coupled_blocks-project' and row['status'] == 'missing_response':
            error = BASE / identity / 'stderr'
            if error.exists() and error.read_text().strip() == 'invalid solver settings':
                row.update(supervision_reason='command_failed: invalid solver settings', native_error=ref(error),
                           failure_stage='native_settings_validation')
        log = BASE / identity / 'response.copt.log'
        if log.exists():
            match = re.search(r'^\s*0\s+[+-].*?\s+(\d+(?:\.\d+)?)s\s*$', log.read_text(), re.M)
            row['vendor_logged_iteration_zero_seconds'] = float(match.group(1)) if match else None
        if row.get('complete_cost_ledger'):
            ledger = row['complete_cost_ledger']
            require(sum(ledger['exclusive_ns'].values()) == ledger['total_ns'] == row['complete_ns'], 'exclusive complete cost sum')
        if row.get('response'):
            response = load(resolve(row['response']))
            if row['lane'] == 'copt-gpu-pdlp': row['parameters'] = response['parameters']
        if row.get('audit'):
            audit = load(resolve(row['audit']))
            row['independent_checks'] = audit.get('checks', 0)
            row['independently_covered_endpoints'] = audit.get('covered_endpoints', 0)
    cohorts = frozen.get('allowance_cohorts', [])
    if cohorts:
        allowances = {identity: (c['wall_seconds'], c['outer_seconds']) for c in cohorts for identity in c['ids']}
        require(sum(len(c['ids']) for c in cohorts) == len(allowances) == len(frozen['cells']), 'disjoint complete allowance cohorts')
        require(set(allowances) == {c['id'] for c in frozen['cells']}, 'allowances cover the exact roster')
    else:
        allowances = {c['id']: (frozen['common_solver_wall_seconds'], 1800) for c in frozen['cells']}
    for family in FAMILIES:
        cells = [c for c in frozen['cells'] if c['family'] == family]
        require(len(cells) == 2 and cells[0]['model']['sha256'] == cells[1]['model']['sha256'], 'identical original model hash in each pair')
        require(all((c['wall_seconds'], c['seconds']) == allowances[c['id']] for c in cells), 'exact prospective allowance cohorts')
        comparison = next(p for p in full['comparisons'] if p['family'] == family)
        if allowances[cells[0]['id']] != allowances[cells[1]['id']]:
            require(comparison['copt_over_project_complete_ratio'] is None, 'unequal allowances cannot produce a timing ratio')
    retention = [ref(p) for p in sorted(BASE.glob('copt-fair-prune-*-v1.json'))]
    early = BASE / 'copt-fair-ill-scaled-endpoint-prune-v1.json'
    if early.exists(): retention.append(ref(early))
    final_prune = BASE / 'copt-fair-final-large-object-prune-v1.json'
    if final_prune.exists(): retention.append(ref(final_prune))
    combined = dict(status='complete_diagnostic_capacity_and_fair_comparison',
                    adapter_admission=load(BASE / 'copt-diagnostic-admission-v1/result.json'),
                    diagnosis=load(BASE / 'copt-diagnostic-results-v1.json'),
                    retrospective=load(BASE / 'copt-diagnostic-retrospective-v1.json'),
                    capacity=load(BASE / 'copt-fair-capacity-v1.json'), full=full,
                    full_source=ref(path), source=ref(__file__), allocation=ref(BASE / 'approved-copt-fair-extension-v1.json'),
                    retention=retention, numerical_image_unchanged=True, public_adoption=False, fresh_full_portable_replay=False)
    resume_path = BASE / 'copt-fair-idle-resume-v1/plan.json'
    if resume_path.exists(): combined['idle_readmission'] = load(resume_path)
    latest_resume = BASE / 'copt-fair-headroom-resume-v1/plan.json'
    if latest_resume.exists(): combined['latest_explicit_user_resumption'] = load(latest_resume)
    recovery = BASE / 'copt-fair-degenerate-tail-v1/plan.json'
    if recovery.exists():
        combined['degenerate_input_recovery'] = load(recovery)
        combined['degenerate_recovery_admission'] = load(recovery.parent / 'started.json')
        combined['degenerate_recovered_chunks'] = ref(BASE / 'copt-fair-degenerate-partial-recovery-v1.json')
        combined['degenerate_regenerated_input'] = ref(BASE / 'copt-fair-regenerated-1b-degenerate-v2/result.json')
    finalization = BASE / 'copt-fair-finalization-v1/plan.json'
    if finalization.exists(): combined['final_missing_response_disposition'] = load(finalization)
    put(destination, combined)
    phase_path = ROOT / 'docs/benchmarks/lp-billion-copt-fair-phases.csv'
    require(not phase_path.exists(), 'fresh phase table')
    with phase_path.open('w', newline='') as stream:
        writer = csv.writer(stream); writer.writerow(['family', 'lane', 'outcome', 'timely_strict_certificate', 'phase', 'seconds'])
        for row in full['cells']:
            for phase, elapsed in row.get('complete_cost_ledger', {}).get('exclusive_ns', {}).items():
                writer.writerow([row['family'], row['lane'], row['status'], row['timely_strict_certificate'], phase, f'{elapsed / 1e9:.9f}'])
            if not row.get('complete_cost_ledger'):
                writer.writerow([row['family'], row['lane'], row['status'], False, 'unavailable', ''])
                for phase, elapsed in row.get('observed_process_cost_ledger', {}).get('exclusive_ns', {}).items():
                    writer.writerow([row['family'], row['lane'], row['status'], False, 'observed_process.' + phase, f'{elapsed / 1e9:.9f}'])
    allowance_text = ('Historical cells retain their 1200-second native / 1800-second outer allowances. '
                      'The first three resumed attempts use 2100/2700 seconds; the coupled project attempt rejects this unsupported native setting before solving. '
                      'The final four untouched ill-scaled/degenerate cells use the sealed executable’s maximum supported 1800-second native allowance, '
                      'with the enlarged 2700-second outer reserve and separate audits. Both lanes in these two pairs have equal limits. '
                      'The tall pair spans different allowances and receives no time ratio. ' if len(cohorts) == 3 else
                      'The seven untouched cells resume with a 2100-second native solver allowance and a 2700-second outer reservation. '
                      'Historical cells retain their 1200/1800-second allowances. The tall pair spans different allowances and receives no time ratio. ' if cohorts else
                      f"Both lanes use a {frozen['common_solver_wall_seconds']}-second native solver allowance and the same 1800-second outer reservation. ")
    lines = ['### Billion-scale comparison', '', allowance_text +
             'All six original billion-nonzero families and both lane slots remain visible. '
             'The project uses unchanged image-v11 with a 10000-update safety cap, '
             'control100/certificate500 and strict original-model 1e-9 acceptance. '
             'COPT 8.0.6 uses GPU PDLP, Presolve=0, Scaling=0, automatic Dualize, '
             'MatrixTol=0, FeasTol/DualTol=1e-9 and PDLPTol=1e-12.', '',
             '| Family | Project complete (s) | COPT complete (s) | Eligible timely strict project / COPT | COPT / project certified-time ratio |',
             '| --- | ---: | ---: | --- | ---: |']
    for comparison in full['comparisons']:
        family = comparison['family']; rows = {r['lane']: r for r in full['cells'] if r['family'] == family}
        project, vendor = rows['fp4x2'], rows['copt-gpu-pdlp']
        ratio = comparison['copt_over_project_complete_ratio']
        lines.append(f"| {family} | {seconds(project.get('complete_ns'))} | {seconds(vendor.get('complete_ns'))} | "
                     f"{project['timely_strict_certificate']} / {vendor['timely_strict_certificate']} | "
                     + ('—' if ratio is None else f'{ratio:.3f}x') + ' |')
    lines += ['', 'Complete cost includes original input validation/conversion, all preparation, execution, '
              'output/teardown and the cold independent final proof. The CSV retains every exclusive phase. '
              'Additional independent intermediate audits are recorded separately. Native solver timers have '
              'different input/conversion boundaries, so their raw elapsed values are not used as end-to-end speedups. '
              'Only jointly timely, strictly certified pairs with equal requested allowances receive a solve-time ratio; other displayed costs are '
              'the costs of the recorded bounded outcomes.', '',
              '| Family / lane | Outcome | Strict endpoint accepted | Solver elapsed (s) | Fresh process (s) | Offline intermediate audit (s) | Actual FP4 work |',
              '| --- | --- | --- | ---: | ---: | ---: | ---: |']
    for row in full['cells']:
        fp4 = '—' if row.get('accepted_fp4_share') is None else f"{100 * row['accepted_fp4_share']:.1f}%"
        accepted = 'no endpoint' if row.get('has_solution') is False else ('—' if not row.get('response') else str(row['strict_endpoint_accepted']))
        lines.append(f"| {row['family']} / {row['lane']} | {outcome(row)} | {accepted} | "
                     f"{seconds(row.get('solver_wall_ns'))} | {seconds(row.get('fresh_process_ns'))} | {seconds(row.get('offline_audit_ns'))} | {fp4} |")
    for row in full['cells']:
        if row.get('timing_exclusion_reason'):
            lines += ['', f"The {row['family']} / {row['lane']} endpoint passes strict independent verification, but its complete-cost timing is excluded: "
                      + row['timing_exclusion_reason'] + '. The retained completed proof and supplemental missing-proof check cover every assessment. '
                      'Its observed solver and fresh-process times remain above; no replacement cold-final timing or certified-time ratio is reported. '
                      f"Supplemental verification took {seconds(row.get('recovery_verification_ns'))} seconds; the original failure retains its full charge."]
            if row.get('supplemental_failed_audit'):
                lines += ['', 'The supplemental numerical check also completed before a refused supervision receipt. '
                          'A separately supervised read-only seal validates both retained proof outputs and their exact bindings. '
                          'Both failed audit charges remain; the seal performs no LP update or numerical proof recomputation.']
    lines += ['', 'Every unavailable response and capacity refusal remains in the compact evidence. '
              'A recorded supervision stop identifies the retained receipt; it does not establish the underlying '
              'numerical or system cause. Missing responses have no eligible solve-time measurement and are never retried. '
              'The project requests FP4; ineligible tiles use the established FP32 fallback, and actual accepted FP4 work is reported above. '
              'The vendor soft MemLimit stays at its admitted 48000 MB setting, alongside the common physical '
              '128 GiB host / 80 GiB owned GPU limits. Empirical capacity forecasts are not hard vendor enclosures. '
              'Construction witnesses and warm starts are never supplied. At most one rotated pair per family and unflushed '
              'caches limit timing inference; this does not establish broad FP4 or general COPT superiority.', '',
              '[Compact diagnosis, capacity and full results](lp-billion-copt-fair-results.json) and '
              '[exclusive complete-cost phases](lp-billion-copt-fair-phases.csv) retain all outcomes. '
              'Completed large input/endpoint chunks are deleted after dependent audits; raw replay requires '
              'regeneration. All small results, phase journals, exact sources and failure charges remain.', '']
    if frozen.get('host_reservation_protocol'):
        lines += ['The untouched ill-scaled and degenerate COPT cells use a smaller 120 GiB per-job host RSS stop, '
                  'with the unchanged additional 4 GiB physical headroom and global 128 GiB cap. This exceeds their '
                  'already padded empirical forecasts of about 110.1 GiB by almost 10 GiB. The native MemLimit and '
                  'all numerical settings remain unchanged; the forecast is not a hard vendor enclosure. '
                  'Audited ill-scaled project endpoint objects were deleted before the COPT lane while preserving '
                  'all original model objects and small proof evidence.', '']
    if recovery.exists():
        lines += ['Degenerate input generation was interrupted before either LP started. Its original '
                  'cleanup-incomplete receipt and full 3600 CPU-second charge remain. A separate check '
                  'finds all four recorded owned identities absent; additional CPU/GPU admission and a '
                  'fresh sustained idle/RAM window precede recovery under a new input identity. Existing '
                  'chunks and the regenerated model are checked against the original hashes. Neither '
                  'scientific cell is repeated, and no resource or certificate guard is relaxed.', '']
    if finalization.exists():
        lines += ['The final degenerate project attempt stops after 1367.952 supervised active seconds '
                  'with no response and a cleanup-incomplete receipt. Its preceding stop trigger is '
                  'unavailable. All four recorded owned identities are independently absent afterward. '
                  'The full 10800 CPU / 2700 GPU-second charge remains; no complete solve timing or '
                  'certificate is assigned, and the attempt is never repeated. The original audit '
                  'records a missing response with zero endpoint claims. All admitted LP identities '
                  'are now attempted; missing or uncertified outcomes remain part of the comparison. '
                  'Remaining obsolete large objects, including partial failed-attempt data, are '
                  'removed after the full audit dispositions, with a retained size inventory.', '']
    report = ROOT / 'docs/benchmarks/lp-billion.md'; text = report.read_text()
    marker = '\nThe planned full pairs use'
    require(text.count(marker) == 1, 'replace the one prospective full-comparison paragraph')
    text = text.split(marker)[0].rstrip() + '\n\n' + '\n'.join(lines)
    report.write_text(text)
    print(dict(cells=len(full['cells']), timely_strict=sum(r['timely_strict_certificate'] for r in full['cells']),
               jointly_timely_strict=sum(p['both_timely_strict_certified'] for p in full['comparisons'])), flush=True)


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(); parser.add_argument('action', choices=['report', 'prune'], nargs='?', default='report')
    prune_completed() if parser.parse_args().action == 'prune' else main()
