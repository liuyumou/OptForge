"""Final acceptance, historical preservation and closure for GPUP-CHECKER2."""
import argparse
import gzip
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess

from lp_checker2_common import BASE, ROOT, BASELINE, CPU_CAPS, GPU_CAPS, NS, load, put, ref, require
from lp_checker2_budget import accounting, admission_open
from lp_checker2_analysis import analyze

DATA = ROOT/'docs/benchmarks/data'
REPORT = ROOT/'docs/benchmarks/lp-checker2.md'
HISTORY = DATA/'checker2-history-v1.json'
ANALYSIS = DATA/'checker2-analysis-v1.json'
ACCEPTANCE = DATA/'checker2-acceptance-v1.json'
ACCOUNTING = DATA/'checker2-accounting-v1.json'


def save_once(path, value):
    if path.exists():
        require(load(path) == value, 'retained record differs: '+str(path))
    else:
        put(path, value)


def preserve():
    revision = subprocess.check_output(['git', 'rev-parse', BASELINE], cwd=ROOT, text=True).strip()
    listing = subprocess.check_output(['git', 'ls-tree', '-rz', revision], cwd=ROOT).split(b'\0')
    navigation = ['AGENTS.md', 'state/active-task.md', 'wiki/status.md', 'docs/plans/gpu-lp-precision-roadmap.md', 'CHANGELOG.md']
    allowed = set(navigation + ['state/backlog.yaml'])
    preserved = {}
    for line in filter(None, listing):
        metadata, raw_path = line.split(b'\t', 1); mode, kind, expected = metadata.decode().split()
        path = raw_path.decode()
        require(kind == 'blob', 'unexpected historical tree entry')
        if path in allowed:
            continue
        target = ROOT/path
        size = len(os.readlink(target).encode()) if mode == '120000' else target.stat().st_size
        sha = hashlib.sha1(f'blob {size}\0'.encode())
        if mode == '120000':
            sha.update(os.readlink(target).encode())
        else:
            with target.open('rb') as stream:
                while chunk := stream.read(1 << 20):
                    sha.update(chunk)
        require(sha.hexdigest() == expected, 'historical bytes changed: '+path)
        preserved[path] = expected
    for path in navigation:
        old = subprocess.check_output(['git', 'show', revision+':'+path], cwd=ROOT)
        require(old.split(b'\n', 2)[2] in (ROOT/path).read_bytes(), 'historical navigation changed: '+path)
    old = subprocess.check_output(['git', 'show', revision+':state/backlog.yaml'], cwd=ROOT)
    require(old.split(b'tasks:\n', 1)[1] in (ROOT/'state/backlog.yaml').read_bytes(), 'old backlog entries changed')
    original = (ROOT/'research/lp-mixed2-reuse/src/main.rs').read_text()
    candidate = (ROOT/'research/lp-mixed2-checker2/src/main.rs').read_text()
    body = lambda text: text[text.index('    fn solve('):text.index('    fn command(')]
    require(body(original) == body(candidate), 'numerical solve changed')
    for name in ['device.rs', 'policy.rs', 'config.rs', 'identity.rs']:
        require((ROOT/'research/lp-mixed2-reuse/src'/name).read_bytes() == (ROOT/'research/lp-mixed2-checker2/src'/name).read_bytes(), 'device/policy source changed')
    result = dict(status='passed', baseline=revision, preserved=preserved, historical_files=len(preserved),
                  old_navigation_exact=True, old_backlog_entries_exact=True, numerical_solve_and_device_exact=True)
    save_once(HISTORY, result)
    return result


def receipts(settled_only=False):
    rows = []
    for path in sorted((BASE/'resources').glob('*.reservation.json')):
        stem = str(path).removesuffix('.reservation.json')
        if settled_only and not Path(stem+'.settlement.json').exists():
            continue
        settlement = load(stem+'.settlement.json'); resource = load(stem+'.resource.json')
        require(not settlement['overrun'] and resource['guardian_cleanup']['empty'] and resource['result']['cleanup']['empty'], 'overrun or incomplete cleanup')
        rows.append(dict(identity=path.name.removesuffix('.reservation.json'), reservation=load(path), settlement=settlement,
                         resource=ref(Path(stem+'.resource.json')), reason=resource['result']['reason']))
    return rows


def verify():
    analysis = analyze(); require(analysis == load(BASE/'analysis.json'), 'analysis replay differs')
    save_once(ANALYSIS, analysis)
    frozen = load(BASE/'freeze.json')
    for item in frozen['sources'] + list(frozen['binaries'].values()) + [frozen['image'], frozen['models']] + frozen['admissions']:
        require(ref(ROOT/item['path']) == item, 'frozen binding differs')
    require(analysis['complete_sessions'] == 512 and analysis['complete_solves'] == 16384
            and not analysis['missing'] and not analysis['partial_responses'] and not analysis['failed_blocks'], 'confirmation coverage incomplete')
    for name in ['native-optimized', 'build-v5', 'cpu-optimized', 'device-optimized', 'smoke-optimized', 'pilot-optimized',
                 'serial-optimized', 'serial-confirmation', 'analysis-final', 'diagnosis-final', 'evidence-publish', 'evidence-verify', 'portable']:
        require(load(BASE/'resources'/(name+'.settlement.json'))['status'] == 'passed', 'acceptance job failed: '+name)
    log = (BASE/'resources/native-optimized.resource.json.log').read_text()
    rust = sum(map(int, re.findall(r'test result: ok\. (\d+) passed;', log)))
    require(rust == 638 and 'Ran 785 tests' in log and 'committed run records re-executed and verified: passed' in log, 'native gate coverage')
    build = (BASE/'resources/build-v5.resource.json.log').read_text()
    require('31 passed; 0 failed' in build, 'isolated tests missing')
    serial = load(BASE/'serial-confirmation/result.json'); admission = load(BASE/'serial-optimized/result.json')
    require(serial['status'] == 'passed' and serial['responses'] == admission['responses'] + analysis['complete_solves'], 'serial coverage')
    identities = lambda value: {(r['endpoint']['sha256'], r['certificate']['sha256'], r['tier']) for r in value['records']}
    require(identities(serial) == identities(admission), 'assessed endpoints differ from admission')
    evidence = load(BASE/'evidence-check.json'); portable = load(BASE/'portable.json')
    require(evidence['status'] == 'passed' and evidence['responses'] == 16384 and evidence['sessions'] == 512, 'evidence coverage')
    require(portable['status'] == 'passed' and portable['original_artifacts_absent'] and portable['result'] == evidence, 'isolated replay differs')
    diagnosis = load(BASE/'diagnosis-final.json')
    require(diagnosis['status'] == 'passed' and diagnosis['responses'] == 16384 and diagnosis['complete_pairs'] == 256, 'cost/response diagnosis coverage')
    require(diagnosis['source'] == ref(ROOT/'tools/lp_checker2_diagnosis.py'), 'diagnosis source differs')
    history = preserve(); receipts(settled_only=True)
    value = dict(status='passed', complete_sessions=512, complete_solves=16384, scoped_passes=analysis['scoped_passes'],
                 provisional_passes=analysis['provisional_passes'], public_adoption=False,
                 rust_tests=638, python_tests=785, isolated_rust_tests=31, serial_responses=serial['responses'],
                 serial_assessments=serial['assessment_requests'], serial_unique=serial['unique_assessments'],
                 serial=ref(BASE/'serial-confirmation/result.json'), history=ref(HISTORY), historical_files=history['historical_files'],
                 analysis=ref(ANALYSIS), diagnosis=ref(DATA/'checker2-diagnosis-v1.json'), evidence=ref(DATA/'checker2-evidence-v1.json'), portable=ref(BASE/'portable.json'),
                 binary=frozen['binaries']['candidate'], image=frozen['image'], frozen=ref(BASE/'freeze.json'),
                 native=ref(BASE/'resources/native-optimized.settlement.json'), cleanup_empty=True)
    save_once(ACCEPTANCE, value)
    print({k:value[k] for k in ['status', 'complete_sessions', 'serial_responses', 'historical_files']}, flush=True)


def close():
    admission_open()
    require(load(ACCEPTANCE)['status'] == 'passed', 'acceptance missing')
    require(load(BASE/'resources/final-acceptance.settlement.json')['status'] == 'passed', 'final acceptance incomplete')
    rows = receipts(); cpu, gpu = accounting(); cpu['cleanup'] += 128 * NS
    require(all(cpu[k] <= cap*NS for k, cap in CPU_CAPS.items()) and all(gpu[k] <= cap*NS for k, cap in GPU_CAPS.items()), 'allocation exceeded')
    published = load(BASE/'published-files.json'); packaged = {r['path'] for r in published['files']}
    late = {str(p.relative_to(ROOT)):p.read_text() for p in (BASE/'sources').rglob('*')
            if p.is_file() and str(p.relative_to(ROOT)) not in packaged}
    late.update({str(p.relative_to(ROOT)):p.read_text() for p in BASE.iterdir()
                 if p.is_file() and p.suffix in ('.py', '.sh', '.json', '.md') and str(p.relative_to(ROOT)) not in packaged})
    resources = {str(p.relative_to(BASE)):p.read_text() for p in (BASE/'resources').iterdir() if p.is_file()}
    target = DATA/'checker2-resources-v1.json.gz'
    raw = json.dumps(dict(receipts=rows, resource_files=resources, late_sources_and_metadata=late), sort_keys=True, separators=(',', ':')).encode()
    with target.open('xb') as stream:
        stream.write(gzip.compress(raw, mtime=0))
    failed = [r for r in rows if r['settlement']['status'] != 'passed']
    value = dict(status='closed', cpu_caps_seconds=CPU_CAPS, gpu_caps_seconds=GPU_CAPS, cpu_ns=cpu, gpu_ns=gpu,
                 cpu_seconds=sum(cpu.values())/NS, gpu_seconds=sum(gpu.values())/NS,
                 preparation_cpu_seconds=512, closing_administration_cpu_seconds=128, failed_jobs=len(failed),
                 failed_cpu_seconds=sum(r['settlement']['cpu_ns'] for r in failed)/NS,
                 failed_gpu_seconds=sum(r['settlement']['gpu_ns'] for r in failed)/NS,
                 failed_reservations=[r['identity'] for r in failed], full_receipts=ref(target),
                 acceptance=ref(ACCEPTANCE), evidence=ref(DATA/'checker2-evidence-v1.json'),
                 historical_transfers=0, cleanup_empty=True)
    put(ACCOUNTING, value); put(BASE/'CLOSED.json', dict(accounting=ref(ACCOUNTING)))
    print(value, flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('action', choices=['preserve', 'verify', 'close'])
    args = parser.parse_args()
    {'preserve':preserve, 'verify':verify, 'close':close}[args.action]()
