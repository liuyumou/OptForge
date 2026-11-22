"""Verify retained comparison proofs, exact sources, charges and owned cleanup."""
import argparse
import ast
import re
import subprocess
import sys
from pathlib import Path
from lp_billion_common import BASE, ROOT, CPU_CAPS, GPU_CAPS, load, put, ref, resolve, require
from lp_confirmation2_supervisor import same_process


def verify(identity):
    out = BASE / identity; out.mkdir(exist_ok=False)
    commands = []
    for name, command in [
        ('harness', [sys.executable, '-B', '-m', 'unittest', 'discover', '-s', 'tests/integration', '-p', 'test_lp_billion*.py']),
        ('documentation', [sys.executable, '-B', 'tools/build_docs.py']),
        ('diff', ['git', 'diff', '--check']),
    ]:
        result = subprocess.run(command, cwd=ROOT, text=True, capture_output=True, timeout=100)
        (out / (name + '.stdout')).write_text(result.stdout); (out / (name + '.stderr')).write_text(result.stderr)
        require(result.returncode == 0, name + ' verification')
        commands.append(dict(name=name, stdout=ref(out / (name + '.stdout')), stderr=ref(out / (name + '.stderr'))))
        print(name, result.stdout[-300:], result.stderr[-300:], flush=True)
    for source in (ROOT / 'tools').glob('lp_billion_copt*.py'): ast.parse(source.read_text(), filename=str(source))
    prior = load(BASE / 'gpu-control-settled-checkpoint-v1.json')
    for item in prior['numerical_bindings']: resolve(item)
    for failure in prior['failures']:
        resolve(failure['settlement']); resolve(failure['resource'])
    image = load(BASE / 'image-v11/binding.json')
    for item in image['files'].values(): resolve(item)
    from lp_billion_readmission import fair_approval
    fair_approval(load(BASE / 'approved-recovery-v1.json'), load(BASE / 'approved-copt-fair-extension-v1.json'),
                  load(BASE / 'approved-assessment-extension-v1.json'), load(BASE / 'approved-packing-transfer-v2.json'),
                  load(BASE / 'approved-packing-transfer-v1.json'))
    data = load(ROOT / 'docs/benchmarks/lp-billion-copt-fair-results.json'); seen = set()
    from lp_billion_copt_diagnostic import installation
    installed = installation(); admission = load(BASE / 'copt-diagnostic-admission-v1/result.json')
    require(admission['status'] == 'passed' and admission['installation'] == installed, 'unchanged admitted COPT installation')
    require(admission['adapter'] == ref(ROOT / 'tools/lp_billion_copt_diagnostic.py')
            and admission['input_adapter'] == ref(ROOT / 'tools/lp_billion_copt_run.py'), 'unchanged admitted COPT adapter')
    responses = set()
    def references(value):
        if isinstance(value, dict):
            if {'namespace', 'path', 'sha256', 'bytes'} <= value.keys():
                key = (value['namespace'], value['path'], value['sha256'])
                if key not in seen: resolve(value); seen.add(key)
            else:
                if isinstance(value.get('response'), dict):
                    response_ref = value['response']; key = (response_ref['namespace'], response_ref['path'], response_ref['sha256'])
                    if key not in responses:
                        response = load(resolve(response_ref)); responses.add(key)
                        if 'installation' in response:
                            require(response['installation'] == installed, 'same installed COPT for every diagnostic/capacity/full response')
                            parameters = response['parameters']
                            require(parameters['MatrixTol'] == 0 and parameters['FeasTol'] == parameters['DualTol'] == 1e-9
                                    and parameters['PDLPTol'] == 1e-12, 'strict vendor settings remain unchanged')
                for child in value.values(): references(child)
        elif isinstance(value, list):
            for child in value: references(child)
    references(data)
    identities = {}; settlements = []; cleanup_dispositions = []
    def collect(value):
        if isinstance(value, dict):
            if 'pid' in value and 'start_ticks' in value: identities[(value['pid'], value['start_ticks'])] = value
            for child in value.values(): collect(child)
        elif isinstance(value, list):
            for child in value: collect(child)
    for path in sorted((BASE / 'resources').glob('*.settlement.json')):
        name = path.name.removesuffix('.settlement.json')
        if name == identity or not (name.startswith(('copt-diagnostic-', 'copt-fair-')) or name in ['operational-cpu-v30', 'operational-gpu-v24', 'operational-cpu-v31', 'operational-cpu-v32', 'operational-gpu-v25', 'operational-cpu-v33', 'operational-cpu-v34', 'operational-gpu-v26', 'operational-cpu-v35', 'operational-gpu-v27']): continue
        settled = load(path)
        require(not settled['overrun'], 'new comparison overrun requires separate authorization')
        if not settled['cleanup_empty']:
            require(name in ['copt-fair-1b-v1-tall-project-full-audit', 'operational-cpu-v33', 'copt-fair-regenerate-1b-degenerate-v1', 'copt-fair-1b-v1-degenerate-project'], 'only the exact retained cleanup failures')
            disposition = path.with_name(name + '.cleanup-disposition.json'); cleanup = load(disposition)
            require(cleanup['status'] == 'cleanup_verified' and cleanup['settlement'] == ref(path), 'exact additive cleanup binding')
            require(cleanup['identities'] and not any(same_process(v) for v in cleanup['identities']), 'all exact interrupted-audit identities gone')
            for key in ['protocol', 'resource', 'journal', 'retained_coordinator_result', 'retained_coordinator_failure']:
                if cleanup.get(key): resolve(cleanup[key])
            collect(cleanup['identities'])
            if name == 'operational-cpu-v33':
                require(settled['resource'] is None and cleanup['resource'] is None, 'missing original receipt remains missing')
                require(all(cleanup.get(k) for k in ['journal', 'retained_coordinator_result', 'retained_coordinator_failure']), 'retained coordinator evidence')
            cleanup_dispositions.append(ref(disposition))
        if settled['resource']: collect(load(resolve(settled['resource'])))
        else: require(name == 'operational-cpu-v33', 'only the explicitly retained missing resource receipt')
        settlements.append(ref(path))
    from lp_billion_prepare_continue import completed
    from lp_billion_readmission import CPU, GPU
    require(CPU == 'operational-cpu-v34' and GPU == 'operational-gpu-v26' and completed(CPU) and completed(GPU), 'fresh source-bound operational gates passed')
    require(completed('operational-cpu-v35') and completed('operational-gpu-v27'), 'additional generation-recovery gates passed')
    require(not any(same_process(value) for value in identities.values()), 'all prior owned comparison identities gone')
    from lp_billion_idle import Nvml
    sensor = Nvml()
    try: sample = sensor.sample()
    finally: sensor.close()
    put(out / 'device-sample.json', sample)
    tests = re.search(r'Ran (\d+) tests', (out / 'harness.stderr').read_text())
    pages = re.search(r'documentation built: (\d+) pages', (out / 'documentation.stdout').read_text())
    require(tests and pages, 'verification counts')
    put(out / 'result.json', dict(status='passed', commands=commands, harness_tests=int(tests[1]), documentation_pages=int(pages[1]),
                                  unchanged_numerical_bindings=prior['numerical_bindings'], prior_failures_retained=len(prior['failures']),
                                  verified_references=len(seen), owned_identities_checked=len(identities), all_owned_identities_gone=True,
                                  settlements=settlements, cleanup_dispositions=cleanup_dispositions, final_device_observation=ref(out / 'device-sample.json'),
                                  results=ref(ROOT / 'docs/benchmarks/lp-billion-copt-fair-results.json'),
                                  phases=ref(ROOT / 'docs/benchmarks/lp-billion-copt-fair-phases.csv'), source=ref(__file__),
                                  fresh_full_portable_replay=False))


def settle(identity):
    from lp_billion_budget import accounting
    gate = BASE / 'resources' / (identity + '.settlement.json'); settled = load(gate)
    require(settled['status'] == 'passed' and settled['cleanup_empty'] and not settled['overrun'], 'settled final verification')
    active = []; failures = []
    for path in sorted((BASE / 'resources').glob('*.reservation.json')):
        receipt = path.with_name(path.name.replace('.reservation.', '.settlement.'))
        if not receipt.exists(): active.append(ref(path)); continue
        reservation, result = load(path), load(receipt)
        if result['status'] != 'passed':
            require(result['cpu_ns'] >= reservation['cpu_ns'] and result['gpu_ns'] >= reservation['gpu_ns'], 'every failure retains full reserved charge')
            failures.append(dict(result, settlement=ref(receipt)))
    require(not active, 'no active reservation at settlement')
    cpu, gpu = accounting()
    require(all(cpu[k] <= v * 1_000_000_000 for k, v in CPU_CAPS.items()) and all(gpu[k] <= v * 1_000_000_000 for k, v in GPU_CAPS.items()), 'settled exact phase caps')
    verification = load(BASE / identity / 'result.json')
    checkpoint = dict(status='open_settled_fair_comparison', active_reservations=[], cpu_ns=sum(cpu.values()), gpu_ns=sum(gpu.values()),
                      cpu_by_phase_ns=cpu, gpu_by_phase_ns=gpu, cpu_caps=CPU_CAPS, gpu_caps=GPU_CAPS,
                      failed_reservations=len(failures), failures=failures, failed_cpu_ns=sum(f['cpu_ns'] for f in failures),
                      failed_gpu_ns=sum(f['gpu_ns'] for f in failures), numerical_bindings=verification['unchanged_numerical_bindings'],
                      harness_tests=verification['harness_tests'], documentation_pages=verification['documentation_pages'],
                      all_owned_identities_gone=True, final_device_observation=verification['final_device_observation'],
                      results=verification['results'], phases=verification['phases'], verification=ref(BASE / identity / 'result.json'),
                      verification_settlement=ref(gate), approval=ref(BASE / 'approved-copt-fair-extension-v1.json'),
                      previous_checkpoint=ref(BASE / 'gpu-control-settled-checkpoint-v1.json'), source=ref(__file__),
                      general_allocation_unchanged=True, public_adoption=False, fresh_full_portable_replay=False)
    destination = BASE / 'copt-fair-settled-checkpoint-v1.json'; require(not destination.exists(), 'fresh settled checkpoint')
    put(destination, checkpoint); put(ROOT / 'docs/benchmarks/lp-billion-copt-fair-checkpoint.json', checkpoint)
    print(dict(cpu_seconds=checkpoint['cpu_ns'] / 1e9, gpu_seconds=checkpoint['gpu_ns'] / 1e9,
               failures=len(failures), harness_tests=checkpoint['harness_tests'], documentation_pages=checkpoint['documentation_pages']), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('action', choices=['verify', 'settle']); parser.add_argument('--id', required=True)
    args = parser.parse_args(); globals()[args.action](args.id)
