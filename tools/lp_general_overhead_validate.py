"""Final source, resource, preservation and portable-replay validation."""
import argparse
import ast
import subprocess
from pathlib import Path
from lp_general_common import BASE, ROOT, load, put, ref, require
from lp_general_budget import accounting


def validate(identity):
    admission = BASE / 'fast-overhead-admission-v1.json'
    a = load(admission)
    require(a['status'] == 'passed' and a['exact_responses'] == 477, 'source admission incomplete')
    for item in a['sources']:
        name = item['path'].split('fast-overhead-admission-v1-sources/', 1)[1]
        require(ref(ROOT / name)['sha256'] == item['sha256'], 'numerical source changed')
    for k in ['image', 'binary']:
        require(ref(ROOT / a[k]['path']) == a[k], 'admitted executable changed')
    native = BASE / 'resources/fast-overhead-native-final-v1.settlement.json'
    require(load(native)['status'] == 'passed', 'final native gate')
    for p in (ROOT / 'crates').rglob('*.rs'):
        require(p.read_bytes() == (BASE / 'sources/fast-overhead-native-final-v1' / p.relative_to(ROOT)).read_bytes(), 'root source changed')
    for p in (ROOT / 'tools').glob('lp_general*.py'):
        ast.parse(p.read_text())
    receipts, failures = [], []
    for p in sorted((BASE / 'resources').glob('fast-overhead-*.reservation.json')):
        if p.name == identity + '.reservation.json':
            continue
        sp = p.with_name(p.name.replace('.reservation.json', '.settlement.json'))
        require(sp.exists(), 'unfinished reservation')
        s, r = load(sp), load(p)
        require(not s['overrun'], 'resource overrun')
        resource = ROOT / s['resource']['path']
        require(ref(resource) == s['resource'], 'resource bytes changed')
        v = load(resource)
        require(v['guardian_cleanup']['empty'] and v['result']['cleanup']['empty'], 'cleanup incomplete')
        if s['status'] != 'passed':
            require(s['cpu_ns'] >= r['cpu_ns'] and s['gpu_ns'] >= r['gpu_ns'], 'failed charge lost')
            failures.append(dict(settlement=ref(sp), cpu_ns=s['cpu_ns'], gpu_ns=s['gpu_ns'], reason=v['result']['reason']))
        receipts.append(ref(sp))
    results = ROOT / 'docs/benchmarks/lp-general-overhead-results.json'
    r = load(results)
    require(sum(c['retained'] for c in r['campaigns']) == 319, 'unexpected response coverage')
    require(r['consolidated_broad']['planned'] == 176 and r['consolidated_broad']['responses'] == 175
            and r['consolidated_broad']['timed'] == 168, 'broad missingness changed')
    require(r['consolidated_broad']['missing'] == ['m16-r0-t1-fp32'], 'interrupted endpoint must stay missing')
    require(sum(len(c['pairs']) for c in r['matched_version_comparisons']) == 48, 'matched version coverage')
    replay = BASE / 'portable/fast-overhead-delivery-v1/replay.json'
    rp = load(replay)
    require(rp['status'] == 'passed' and rp['result']['cells'] == 319 and len(rp['result']['missing']) == 41, 'portable replay missingness')
    package = load(BASE / 'portable/fast-overhead-delivery-v1/receipt.json')
    preserved = []
    for name in ['AGENTS.md', 'research/lp-general-lowbit/README.md', 'docs/specifications/SPEC-0045-general-lowbit-lp.md', 'docs/decisions/ADR-0079-general-lowbit-lp.md']:
        old = subprocess.check_output(['git', 'show', 'HEAD:' + name], cwd=ROOT)
        require(old in (ROOT / name).read_bytes(), 'historical text changed ' + name)
        preserved.append(name)
    for name in ['lp-general-fast.md', 'lp-general-fast-results.json', 'lp-general-fast-profile-results.json', 'lp-general-fast-validation.json']:
        path = 'docs/benchmarks/' + name
        require((ROOT / path).read_bytes() == subprocess.check_output(['git', 'show', 'HEAD:' + path], cwd=ROOT), 'prior report changed')
        preserved.append(path)
    cpu, gpu = accounting()
    put(BASE / (identity + '.json'), dict(status='passed', admission=ref(admission), native=ref(native), results=ref(results),
        portable=ref(replay), portable_result=rp['result'], archived_files=rp['byte_files'],
        previous_files_preserved=package['prior_scientific_files_verified'], compressed_bytes=package['compressed_bytes'],
        resources=receipts, failures=failures, failed_cpu_ns=sum(x['cpu_ns'] for x in failures), failed_gpu_ns=sum(x['gpu_ns'] for x in failures),
        historical_text=preserved, cleanup_empty=True, allocation_status='open',
        checkpoint_including_active_reservation=dict(cpu_ns=sum(cpu.values()), gpu_ns=sum(gpu.values())),
        claim='Validated implementation and descriptive development. No broad superiority, confirmation, public-default change or publication.'))


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--id', required=True)
    validate(p.parse_args().id)
