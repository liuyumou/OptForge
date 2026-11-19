"""Separate approved reservations, preserving all prior scientific ledgers."""
import argparse
import fcntl
import os
from pathlib import Path
import subprocess
import sys
import time
from lp_billion_common import (BASE, ROOT, CPU_CAPS, GPU_CAPS, HOST_LIMIT, DEVICE,
    DEVICE_LIMIT, DISK_LIMIT, MAX_GAP_NS, NS, load, put, ref, resolve, require, disk_bytes)


def accounting():
    cpu = {k: 0 for k in CPU_CAPS}
    gpu = {k: 0 for k in GPU_CAPS}
    cpu['implementation'], cpu['cleanup'] = 512*NS, 128*NS
    for p in sorted((BASE/'resources').glob('*.reservation.json')):
        r = load(p)
        settled = p.with_name(p.name.replace('.reservation.json', '.settlement.json'))
        s = load(settled) if settled.exists() else r
        cpu[r['phase']] += s['cpu_ns']
        if r['gpu']:
            gpu[r['phase']] += s['gpu_ns']
    return cpu, gpu


def sources():
    paths = list((ROOT/'research/lp-billion-lowbit').rglob('*.rs'))
    paths += list((ROOT/'research/lp-billion-lowbit').rglob('*.cu'))
    paths += list((ROOT/'research/lp-billion-lowbit').rglob('Cargo.*'))
    paths += list((ROOT/'research/lp-billion-lowbit/upstream').glob('*.json'))
    paths += list((ROOT/'tools').glob('lp_billion*.py'))
    paths += list((ROOT/'tests/integration').glob('test_lp_billion*.py'))
    paths += list((ROOT/'crates').rglob('*.rs'))
    paths += list((ROOT/'crates').glob('*/Cargo.toml'))
    paths += list((ROOT/'research/lp-tensor-expanded-device/cuda-sys').glob('Cargo.*'))
    paths += list((ROOT/'research/lp-tensor-expanded-device/cuda-sys/src').glob('*.rs'))
    for root in ['research/lp-general-lowbit/src', 'research/lp-mixed2-checker2/src']:
        paths += list((ROOT/root).rglob('*.rs'))
    paths += [ROOT/'tools'/p for p in ['lp_confirmation2_supervisor.py',
        'lp_confirmation_supervisor.py', 'lp_cpu_admission.py', 'lp_mixed2_reuse_place.py']]
    paths += list((ROOT/'docs/specifications').glob('SPEC-0046*.md'))
    paths += [ROOT/'Cargo.toml',
              ROOT/'Cargo.lock', ROOT/'rust-toolchain.toml']
    return sorted(set(p for p in paths if p.is_file()))


def cleared(settlement_path, gpu, phase, identity):
    """Later cleanup/readmission never rewrites a failed historical receipt."""
    d=load(settlement_path)
    require(not d['overrun'], 'resource admission closed by overrun')
    if d['cleanup_empty']:
        return
    from lp_confirmation2_supervisor import same_process
    disposition_path=settlement_path.with_name(settlement_path.name.replace('.settlement.json','.cleanup-disposition.json'))
    disposition=load(disposition_path)
    require(disposition['status']=='cleanup_verified' and disposition['settlement']==ref(settlement_path), 'cleanup disposition binding')
    require(disposition['identities'] and not any(same_process(p) for p in disposition['identities']), 'owned process identity still live')
    for path in sorted((BASE/'operational-readmissions').glob('*.json')):
        plan=load(path)
        if plan['cleanup_disposition']==ref(disposition_path):
            require(plan['status']=='prospective', 'operational readmission plan')
            resolve(plan['protocol'])
            disposition=dict(disposition,admission_job=plan['admission_job'],cpu_admission_job=plan['cpu_admission_job'],
                             cpu_only_jobs=plan.get('cpu_only_jobs',[]),cpu_only_sources=plan.get('cpu_only_sources',[]))
    if not gpu and phase in ['admission','cleanup','reporting']:
        return
    if not gpu and phase=='development' and identity in disposition.get('cpu_only_jobs',[]):
        cpu=load(BASE/'resources'/(disposition['cpu_admission_job']+'.settlement.json'))
        require(cpu['status']=='passed' and cpu['cleanup_empty'] and not cpu['overrun'], 'CPU construction operational readmission')
        require(disposition.get('cpu_only_sources'), 'CPU construction source bindings')
        for item in disposition['cpu_only_sources']:
            resolve(item)
        return
    if phase=='admission' and identity==disposition['admission_job']:
        cpu=load(BASE/'resources'/(disposition['cpu_admission_job']+'.settlement.json'))
        require(cpu['status']=='passed' and cpu['cleanup_empty'] and not cpu['overrun'], 'CPU operational readmission')
        return
    admission=BASE/'resources'/(disposition['admission_job']+'.settlement.json')
    gate=load(admission)
    require(gate['status']=='passed' and gate['cleanup_empty'] and not gate['overrun'], 'fresh GPU operational readmission')
    for item in load(resolve(load(admission.with_name(admission.name.replace('.settlement.json','.reservation.json')))['source_manifest']))['sources']:
        if item['original']['path'] in ['tools/lp_billion_common.py','tools/lp_billion_budget.py','tools/lp_billion_idle.py']:
            resolve(item['original'])


def run(identity, phase, seconds, gpu, command, host_gib=16, device_gib=0, disk_gib=1):
    require(identity and Path(identity).name == identity, 'job identity')
    require(phase in CPU_CAPS and isinstance(seconds, int) and seconds >= 5, 'reservation domain')
    require(not gpu or phase in GPU_CAPS, 'GPU phase domain')
    require(1 <= host_gib <= 128 and 0 <= device_gib <= 80 and 0 <= disk_gib <= 400, 'approved capacity domain')
    require(load(BASE/'OPEN.json')['status'] == 'open', 'allocation not open')
    require(not (BASE/'CLOSED.json').exists(), 'allocation already closed')
    directory = BASE/'resources'
    directory.mkdir(exist_ok=True)
    with (BASE/'budget.lock').open('a+b') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        for p in directory.glob('*.reservation.json'):
            s = p.with_name(p.name.replace('.reservation.json', '.settlement.json'))
            require(s.exists(), 'unsettled reservation')
            cleared(s, gpu, phase, identity)
        cpu, used_gpu = accounting()
        require(cpu[phase]+4*seconds*NS <= CPU_CAPS[phase]*NS, 'CPU phase exhausted')
        require(not gpu or used_gpu[phase]+seconds*NS <= GPU_CAPS[phase]*NS, 'GPU phase exhausted')
        require(disk_bytes()+(disk_gib << 30) <= DISK_LIMIT, 'complete disk reservation exceeds ceiling')
        stat = os.statvfs(BASE)
        require(stat.f_bavail*stat.f_frsize >= (disk_gib+8) << 30, 'physical disk headroom')
        available = int(next(l for l in Path('/proc/meminfo').read_text().splitlines()
                             if l.startswith('MemAvailable:')).split()[1])*1024
        require(available >= (host_gib+4) << 30, 'physical host headroom')
        lease = None
        idle = None
        try:
            if gpu:
                lease = open('/tmp/ai-optimizer-gpu.lock', 'a+b')
                fcntl.flock(lease, fcntl.LOCK_EX | fcntl.LOCK_NB)
                from lp_billion_idle import quiet
                idle = quiet(device_gib << 30)
            prefix = directory/identity
            frozen = BASE/'sources'/identity
            frozen.mkdir(parents=True, exist_ok=False)
            bindings = []
            for p in sources():
                dest = frozen/p.relative_to(ROOT)
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(p.read_bytes())
                bindings.append(dict(original=ref(p), retained=ref(dest)))
            put(frozen/'manifest.json', dict(sources=bindings))
            put(str(prefix)+'.reservation.json', dict(phase=phase, gpu=gpu,
                cpu_ns=4*seconds*NS, gpu_ns=seconds*NS if gpu else 0, command=command,
                source_manifest=ref(frozen/'manifest.json'), idle=idle, device=DEVICE,
                host_bytes=host_gib << 30, device_bytes=device_gib << 30, disk_bytes=disk_gib << 30))
            put(str(prefix)+'.cpu-journal.json', dict(identity='billion-lp-job-v1',
                prior_cpu_ns=0, ceiling_cpu_ns=4*seconds*NS, active=None, failed=False, runs=[],
                stages={phase: dict(cap_cpu_ns=4*seconds*NS, charged_cpu_ns=0)}))
            request = dict(stage=phase, reserve_cpu_seconds=4*seconds,
                output=str(prefix)+'.resource.json', log=str(prefix)+'.resource.json.log',
                journal=str(prefix)+'.cpu-journal.json', lock=str(BASE/'cpu.lock'),
                slots=4, declared_memory_bytes=(host_gib << 30)-(256 << 20),
                rss_stop_bytes=host_gib << 30, address_space_bytes=0, sources=[],
                bootstrap=False, show_log=False, max_gap_ns=MAX_GAP_NS, billion_gpu=gpu,
                command=([sys.executable, '-B', str(ROOT/'tools/lp_mixed2_reuse_place.py'), *command]
                         if gpu or host_gib > 16 else command))
            request_path = str(prefix)+'.request.json'
            put(request_path, request)
            env = {**os.environ, 'CUDA_VISIBLE_DEVICES': DEVICE if gpu else '',
                'CARGO_TARGET_DIR': str(BASE/'target'), 'COPT_HOME': '/root/copt80',
                'COPT_LICENSE_DIR': '/root/copt80'}
            if gpu:
                env['AI_OPTIMIZER_GPU_LEASE'] = 'inherited'
            started = time.monotonic_ns()
            child = subprocess.run([sys.executable, '-B', __file__, '_supervise', request_path],
                env=env, pass_fds=() if lease is None else (lease.fileno(),))
            elapsed = time.monotonic_ns()-started
            receipt = Path(request['output'])
            report = load(receipt) if receipt.exists() else None
            success = child.returncode == 0 and report and report['status'] == 'passed'
            charged_cpu = max(report['charged_cpu_ns'] if report else 4*seconds*NS, 4*elapsed)
            if not success:
                charged_cpu = max(charged_cpu, 4*seconds*NS)
            charged_gpu = (elapsed if success else max(elapsed, seconds*NS)) if gpu else 0
            overrun = charged_cpu > 4*seconds*NS or charged_gpu > seconds*NS
            cleanup = bool(report and report['guardian_cleanup']['empty'] and report['result']['cleanup']['empty'])
            result = dict(phase=phase, gpu=gpu, cpu_ns=charged_cpu, gpu_ns=charged_gpu,
                status='passed' if success and not overrun else 'refused', overrun=overrun,
                cleanup_empty=cleanup, resource=ref(receipt) if report else None)
            put(str(prefix)+'.settlement.json', result)
            return result
        finally:
            if lease:
                lease.close()


def main():
    if len(sys.argv) == 3 and sys.argv[1] == '_supervise':
        import lp_confirmation2_supervisor as supervisor
        from lp_billion_idle import install
        request = load(sys.argv[2])
        install(supervisor, request)
        return 0 if supervisor.run(request)['status'] == 'passed' else 2
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--id', required=True)
    p.add_argument('--phase', choices=CPU_CAPS, required=True)
    p.add_argument('--seconds', type=int, required=True)
    p.add_argument('--gpu', action='store_true')
    p.add_argument('--host-gib', type=int, default=16)
    p.add_argument('--device-gib', type=int, default=0)
    p.add_argument('--disk-gib', type=int, default=1)
    p.add_argument('command', nargs=argparse.REMAINDER)
    a = p.parse_args()
    result = run(a.id, a.phase, a.seconds, a.gpu,
        a.command[1:] if a.command[:1] == ['--'] else a.command, a.host_gib, a.device_gib, a.disk_gib)
    print(result, flush=True)
    return 0 if result['status'] == 'passed' else 2


if __name__ == '__main__':
    raise SystemExit(main())
