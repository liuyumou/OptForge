"""Read-only ADR-0044 containment preflight. Never launches admitted work.

A readable or writable control file alone is not resource admission. A complete
capability snapshot still needs the coordinator's independent failure tests.
"""
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import resource
import subprocess
import time

ROOT = Path(__file__).resolve().parents[1]
CGROUP = Path('/sys/fs/cgroup')
READ_CONTROLS = (
    'cgroup.controllers', 'cgroup.subtree_control', 'cgroup.type', 'cgroup.procs',
    'cpu.max', 'cpu.stat', 'cpuset.cpus.effective', 'memory.max',
    'memory.swap.max', 'memory.peak', 'memory.events', 'cgroup.freeze',
)
REQUIRED_CONTROLS = READ_CONTROLS + ('cgroup.kill',)
PREFIX_SHA = 'e1766490f8de2affa14f4f950afed18be7f69531c3c28eedfd74539fcc0d9db5'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def reference(path):
    return dict(path=str(path.relative_to(ROOT)), sha256=sha(path))


def control_snapshot(root):
    result = {}
    for name in REQUIRED_CONTROLS:
        path = root / name
        item = dict(exists=path.exists(), writable=os.access(path, os.W_OK))
        # cgroup.kill is write-only: reading it returns EINVAL, not evidence of
        # missing containment. Record presence/access without issuing a read.
        if name in READ_CONTROLS and item['exists']:
            try:
                item['value'] = path.read_text().strip()
            except OSError as error:
                item['read_error_errno'] = error.errno
        result[name] = item
    return result


def cpu_set_count(value):
    cpus = set()
    for chunk in value.split(','):
        parts = chunk.split('-')
        if len(parts) == 1:
            lo = hi = int(parts[0])
        elif len(parts) == 2:
            lo, hi = map(int, parts)
        else:
            raise ValueError('invalid cpuset')
        if lo < 0 or hi < lo or hi > 1048575:
            raise ValueError('invalid cpuset range')
        cpus.update(range(lo, hi + 1))
    return len(cpus)


def assess(controls, mount_read_only, explicit_task_subtree):
    reasons = []
    if mount_read_only:
        reasons.append('cgroup_mount_read_only')
    if not explicit_task_subtree:
        reasons.append('no_delegated_task_subtree')
    for name in REQUIRED_CONTROLS:
        item = controls.get(name, {})
        if not item.get('exists'):
            reasons.append('missing_control:' + name)
        elif name in READ_CONTROLS and 'value' not in item:
            reasons.append('unreadable_control:' + name)
    for name in ('cgroup.procs', 'cgroup.freeze', 'cgroup.kill', 'cpu.max',
                 'memory.max', 'memory.swap.max'):
        if not controls.get(name, {}).get('writable'):
            reasons.append('control_not_delegated:' + name)
    def value(name):
        return controls.get(name, {}).get('value', '')
    try:
        quota, period = map(int, value('cpu.max').split())
        if quota <= 0 or period <= 0 or quota > 4 * period:
            raise ValueError('CPU quota exceeds contract')
    except (ValueError, TypeError):
        reasons.append('cpu_quota_not_bounded_to_four_cores')
    try:
        count = cpu_set_count(value('cpuset.cpus.effective'))
        if not 1 <= count <= 4:
            raise ValueError('cpuset exceeds contract')
    except (ValueError, TypeError):
        reasons.append('cpuset_not_bounded_to_four_cpus')
    try:
        if not 0 < int(value('memory.max')) <= 8 << 30:
            raise ValueError('memory exceeds contract')
    except (ValueError, TypeError):
        reasons.append('memory_not_bounded_to_eight_gib')
    if value('memory.swap.max') != '0':
        reasons.append('swap_not_disabled')
    try:
        counters = dict(line.split() for line in value('cpu.stat').splitlines())
        if int(counters['usage_usec']) < 0:
            raise ValueError('negative CPU usage')
        if int(value('memory.peak')) < 0:
            raise ValueError('negative memory peak')
        events = dict(line.split() for line in value('memory.events').splitlines())
        if any(int(events[key]) != 0 for key in ('max', 'oom', 'oom_kill')):
            raise ValueError('memory event in fresh task enclosure')
    except (KeyError, ValueError, TypeError):
        reasons.append('aggregate_cpu_memory_accounting_not_ready')
    return dict(
        status='cpu_admission_refusal' if reasons else 'capability_ready_not_admitted',
        reasons=reasons, preparation_admitted=False, device_admitted=False,
        cpu_coordinator_failure_tests_passed=False,
    )


def manager_probe(user=False):
    command = ['systemctl'] + (['--user'] if user else [])
    command += ['show', '--property=ControlGroup', '--property=Delegate']
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=5)
        return dict(command=command, returncode=result.returncode,
                    stdout=result.stdout[:4096], stderr=result.stderr[:4096])
    except (FileNotFoundError, subprocess.TimeoutExpired) as error:
        return dict(command=command, error=type(error).__name__)


def create_receipt(path, result):
    # Refusals are immutable observations too. Never replace an earlier receipt.
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x') as stream:
        json.dump(result, stream, indent=2, sort_keys=True)
        stream.write('\n')


def probe():
    started = time.monotonic_ns()
    before = resource.getrusage(resource.RUSAGE_SELF)
    mount_lines = [line for line in Path('/proc/self/mountinfo').read_text().splitlines()
                   if ' - cgroup2 ' in line]
    matching = [line for line in mount_lines if line.split()[4] == str(CGROUP)]
    read_only = len(matching) != 1 or 'ro' in matching[0].split()[5].split(',')
    controls = control_snapshot(CGROUP)
    # A namespace root shared with unrelated processes is never an explicitly
    # delegated task subtree, even if its mount permissions later change.
    result = assess(controls, read_only, explicit_task_subtree=False)
    result.update(identity='gpup-tensor-cost-cpu-preflight-v1', mode='read-only',
                  gpu_seconds=0, workload_launches=0, gpu_reservations=0,
                  cgroup_membership=Path('/proc/self/cgroup').read_text().strip(),
                  cgroup_mounts=mount_lines, controls=controls,
                  delegated_children=[p.name for p in CGROUP.iterdir() if p.is_dir()],
                  managers=dict(system=manager_probe(), user=manager_probe(True)),
                  host_interfaces={path: Path(path).exists() for path in (
                      '/run/systemd/private', '/run/user/0/systemd/private',
                      '/run/dbus/system_bus_socket', '/run/user/0/bus',
                      '/var/run/docker.sock', '/run/containerd/containerd.sock', '/run/host')},
                  process_capabilities=[line for line in Path('/proc/self/status').read_text().splitlines()
                                        if line.startswith(('CapEff:', 'CapBnd:', 'Seccomp:'))],
                  bootstrap_accounting='Capability probe is outside an admitted enclosure; charge its full stage reservation, never claim aggregate compliance.',
                  admission_stage_cpu_reservation_seconds=250,
                  supervisor_margin_reserved_seconds=50,
                  mandatory_remaining_stage_reservations_seconds=dict(proofs_admission=550, native_acceptance=550, leased_cpu_verification=550, reporting=100),
                  initial_probe_limitation='Earlier interactive capability read stopped at write-only cgroup.kill with EINVAL; no workload launched. This probe avoids reading write-only controls.')
    ledger = ROOT / 'artifacts/gpup-tensor-residual-v1/study-v1/ledger.jsonl'
    raw = ledger.read_bytes()
    if len(raw.splitlines()) != 17362 or hashlib.sha256(raw).hexdigest() != PREFIX_SHA:
        raise ValueError('historical GPU ledger differs')
    result.update(ledger_events=17362, ledger_sha256=PREFIX_SHA,
                  authority=reference(ROOT / 'docs/decisions/ADR-0044-tensor-cost-continuation.md'),
                  tool=reference(Path(__file__).resolve()))
    after = resource.getrusage(resource.RUSAGE_SELF)
    child_usage = resource.getrusage(resource.RUSAGE_CHILDREN)
    result.update(elapsed_ns=time.monotonic_ns() - started,
                  observed_probe_cpu_seconds=(after.ru_utime + after.ru_stime - before.ru_utime - before.ru_stime + child_usage.ru_utime + child_usage.ru_stime),
                  process_peak_rss_bytes=after.ru_maxrss * 1024)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    allowed = ROOT / 'docs/benchmarks/data/tensor-cost'
    if args.output.resolve().parent != allowed.resolve() or args.output.exists():
        raise ValueError('use a new separate admission receipt')
    lock_path = ROOT / 'artifacts/lp-cpu-admission.lock'
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        result = probe()
        create_receipt(args.output, result)
    print(json.dumps({key: result[key] for key in ('status', 'reasons', 'gpu_seconds', 'workload_launches')}))
    return 2  # Capability observations never grant workload admission.


if __name__ == '__main__':
    raise SystemExit(main())
