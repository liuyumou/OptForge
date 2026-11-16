"""Independent completion reservations; source-bound supervisor selection."""
import argparse
import fcntl
import os
from pathlib import Path
import subprocess
import sys
import time

from lp_general_common import (BASE, CPU_CAPS, DEVICE, GPU_CAPS, NS, ROOT,
                                load, put, ref, require, SUPERVISOR_MODULE, MAX_GAP_NS)


def accounting(base=BASE):
    cpu = {k: 0 for k in CPU_CAPS}
    gpu = {k: 0 for k in GPU_CAPS}
    # Separate continuation allocation; prior charges remain in their closed ledgers.
    cpu['implementation'] = 512 * NS
    cpu['cleanup'] = 128 * NS
    for p in sorted((base / 'resources').glob('*.reservation.json')):
        r = load(p)
        result = p.with_name(p.name.replace('.reservation.json', '.settlement.json'))
        s = load(result) if result.exists() else r
        cpu[r['phase']] += s['cpu_ns']
        if r['gpu']:
            gpu[r['phase']] += s['gpu_ns']
    # A harness can preserve child errors yet exit zero. Subsequent diagnosis may
    # conservatively charge the full failed reservation without editing receipts.
    seen=set()
    for p in sorted((base/'charge-adjustments').glob('*.json')):
        a=load(p);identity=a['original_job'];require(identity not in seen,'duplicate charge adjustment');seen.add(identity)
        rp=base/'resources'/(identity+'.reservation.json');sp=base/'resources'/(identity+'.settlement.json')
        require(ref(rp)==a['reservation'] and ref(sp)==a['settlement'],'adjustment source differs')
        r,s=load(rp),load(sp)
        dc=max(0,r['cpu_ns']-s['cpu_ns']);dg=max(0,r['gpu_ns']-s['gpu_ns'])
        require(a['cpu_ns']==dc and a['gpu_ns']==dg and a['phase']==r['phase'],'invalid full-charge adjustment')
        cpu[r['phase']]+=dc
        if r['gpu']:gpu[r['phase']]+=dg
    return cpu, gpu


def admission_open(base=BASE, phase=None, gpu=False):
    require(not (base/"CLOSED.json").exists(), "allocation is closed")
    for p in (base/'resources').glob('*.settlement.json'):
        s = load(p)
        if s.get('interruption_disposition'):
            item=s['interruption_disposition'];path=ROOT/item['path']
            require(ref(path)==item,'interruption disposition differs')
            d=load(path)
            reservation=p.with_name(p.name.replace('.settlement.json','.reservation.json'))
            require(d['kind']=='missing-supervisor-receipt-disposition' and d['reservation']==ref(reservation),
                    'invalid interruption disposition')
            require(d['cleanup_observed_empty'] and d['campaign_stopped'] and not d['historical_supervision_established'],
                    'interruption cannot establish historical supervision')
            require(s['status']=='refused' and s['resource'] is None and
                    s['cpu_ns']==d['charged_cpu_ns'] and s['gpu_ns']==d['charged_gpu_ns'],
                    'interruption charge differs')
            r=load(reservation)
            require(s['cpu_ns']>=r['cpu_ns'] and s['gpu_ns']>=r['gpu_ns'],'interruption undercharged')
            require(not gpu and phase not in ('development','confirmation'),
                    'missing supervision receipt: new GPU/scientific execution needs operational readmission')
            continue
        require(not s['overrun'], 'prior resource overrun closes execution')
        if s.get('resource'):
            r = load(ROOT/s['resource']['path'])
            require(r['guardian_cleanup']['empty'] and r['result']['cleanup']['empty'], 'prior cleanup incomplete')
            reason=r['result']['reason'] or ''
            require(not any(x in reason for x in ('sample_gap', 'sample_stale', 'sample_duration', 'scan_work', 'heartbeat', 'coordinator_lost')), 'supervision loss closes execution')
    for p in (base/'resources').glob('*.reservation.json'):
        require(p.with_name(p.name.replace('.reservation.json','.settlement.json')).exists(),
                'unsettled reservation closes execution')


def run(identity, phase, seconds, gpu, command, base=BASE):
    require(identity and Path(identity).name == identity, 'invalid job identity')
    require(phase in CPU_CAPS and type(seconds) is int and seconds >= 3, 'invalid reservation')
    require(not gpu or phase in GPU_CAPS, 'GPU phase invalid')
    require(not gpu or os.environ.get('MIXED2_CONFIRM2_TRACE')!='1','CPU-only phase tracing')
    require(not os.environ.get('MIXED2_CONFIRM2_SCAN_DELAY_MS') or os.environ.get('MIXED2_CONFIRM2_TRACE')=='1','injection requires trace admission')
    directory = base / 'resources'
    directory.mkdir(parents=True, exist_ok=True)
    # Serialize reservations as well as numerical jobs; no lost-update allowance.
    with (base / 'budget.lock').open('a+b') as budget_lock:
        fcntl.flock(budget_lock, fcntl.LOCK_EX)
        admission_open(base, phase, gpu)
        cpu, used_gpu = accounting(base)
        require(cpu[phase] + 4 * seconds * NS <= CPU_CAPS[phase] * NS, 'CPU phase exhausted')
        require(not gpu or used_gpu[phase] + seconds * NS <= GPU_CAPS[phase] * NS, 'GPU phase exhausted')
        prefix = directory / identity
        # Every development attempt has immutable source bytes, including failures.
        frozen = base / 'sources' / identity
        frozen.mkdir(parents=True, exist_ok=False)
        paths = list((ROOT/'research/lp-general-lowbit/src').rglob('*.rs'))
        paths += list((ROOT/'research/lp-general-lowbit/tests').rglob('*.rs'))
        paths += list((ROOT/'research/lp-general-lowbit').glob('Cargo.*'))
        paths += list((ROOT/'research/lp-general-lowbit').glob('*.toml'))
        paths += list((ROOT/'research/lp-general-lowbit/upstream').glob('*'))
        paths += list((ROOT/'research/lp-general-lowbit').glob('cuda/*'))
        paths += list((ROOT/'crates').rglob('*.rs'))
        paths += list((ROOT/'crates').glob('*/Cargo.toml'))
        paths += list((ROOT/'research/lp-tensor-expanded-device/cuda-sys').rglob('*.rs'))
        paths += list((ROOT/'research/lp-tensor-expanded-device/cuda-sys').glob('Cargo.*'))
        paths += list((ROOT/'tools').glob('lp_general*'))
        paths += list((ROOT/'tests/integration').glob('*lp_general*'))
        paths += [ROOT/'tools'/n for n in [
            'lp_confirmation2_supervisor.py','lp_confirmation_supervisor.py',
            'lp_cpu_admission.py','lp_baseline_common.py','lp_baseline_contract.py',
            'lp_mixed2_reuse_place.py','lp_mixed2_confirm_native_place.py']]
        paths += [ROOT/'docs/specifications/SPEC-0045-general-lowbit-lp.md',
                  ROOT/'docs/decisions/ADR-0079-general-lowbit-lp.md',
                  ROOT/'Cargo.toml', ROOT/'Cargo.lock', ROOT/'rust-toolchain.toml']
        paths = sorted(set(paths))
        refs = []
        for path in sorted(paths):
            dest = frozen / path.relative_to(ROOT)
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(path.read_bytes())
            refs.append(ref(dest))
        put(frozen/'manifest.json', dict(sources=refs))
        put(str(prefix) + '.reservation.json', dict(phase=phase, gpu=gpu,
            cpu_ns=4 * seconds * NS, gpu_ns=seconds * NS if gpu else 0, command=command,
            device=DEVICE if gpu else None, supervisor=ref(ROOT/'tools'/(SUPERVISOR_MODULE+'.py')),diagnostic_trace=os.environ.get('MIXED2_CONFIRM2_TRACE')=='1',diagnostic_scan_delay_ms=int(os.environ.get('MIXED2_CONFIRM2_SCAN_DELAY_MS','0')),max_gap_ns=MAX_GAP_NS))
        put(str(prefix) + '.cpu-journal.json', dict(identity='gpup-mixed2_reuse-job-v1',
            prior_cpu_ns=0, ceiling_cpu_ns=4 * seconds * NS, active=None, failed=False, runs=[],
            stages={phase: dict(cap_cpu_ns=4 * seconds * NS, charged_cpu_ns=0)}))
        env = {**os.environ, 'CUDA_VISIBLE_DEVICES': DEVICE if gpu else '',
               'COPT_HOME':'/root/copt80', 'COPT_LICENSE_DIR':'/root/copt80'}
        queued = time.monotonic_ns()
        lock = None
        try:
            if gpu:
                lock = open(os.environ.get('AI_OPTIMIZER_GPU_LOCK', '/tmp/ai-optimizer-gpu.lock'), 'a+b')
                while True:
                    try:
                        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
                        break
                    except BlockingIOError:
                        require(time.monotonic_ns() - queued < 300 * NS, 'GPU lease wait expired')
                        time.sleep(.1)
                env['AI_OPTIMIZER_GPU_LEASE'] = 'inherited'
            acquired = time.monotonic_ns()
            # Invoke run() through a small entrypoint so new stage names do not
            # change the retained supervisor's historical argparse choices.
            request = dict(stage=phase, reserve_cpu_seconds=4 * seconds,
                output=str(prefix) + '.resource.json', log=str(prefix) + '.resource.json.log',
                journal=str(prefix) + '.cpu-journal.json', lock=str(base / 'cpu.lock'),
                slots=4, declared_memory_bytes=15 << 30, rss_stop_bytes=16 << 30,
                address_space_bytes=0, sources=[], bootstrap=False, show_log=False,
                max_gap_ns=MAX_GAP_NS, command=command)
            request_path = str(prefix) + '.request.json'
            put(request_path, request)
            args = [sys.executable, '-B', str(ROOT / 'tools/lp_general_budget.py'),
                    '_supervise', request_path]
            child = subprocess.run(args, env=env, pass_fds=() if lock is None else (lock.fileno(),))
            elapsed = time.monotonic_ns() - acquired
            receipt = Path(request['output'])
            report = load(receipt) if receipt.exists() else None
            success = child.returncode == 0 and report and report['status'] == 'passed'
            charged_cpu = max(report['charged_cpu_ns'] if report else 4 * seconds * NS,
                              4 * elapsed)
            charged_gpu = (elapsed if success else max(elapsed, seconds * NS)) if gpu else 0
            overrun = charged_cpu > 4 * seconds * NS or charged_gpu > seconds * NS
            settlement = dict(phase=phase, gpu=gpu, cpu_ns=charged_cpu, gpu_ns=charged_gpu,
                status='passed' if success and not overrun else 'refused', overrun=overrun,
                queue_ns=acquired-queued, resource=ref(receipt) if report else None)
            put(str(prefix) + '.settlement.json', settlement)
            return settlement
        finally:
            if lock:
                lock.close()


def main():
    if len(sys.argv) == 3 and sys.argv[1] == '_supervise':
        import importlib
        lp_cpu_admission=importlib.import_module(SUPERVISOR_MODULE)
        request = load(sys.argv[2])
        if os.environ.get('MIXED2_CONFIRM2_TRACE')=='1':
            require(request['stage']=='diagnosis','phase trace is diagnostic only')
            from lp_mixed2_confirm2_trace import install
            install(lp_cpu_admission,request['output'])
        report = lp_cpu_admission.run(request)
        return 0 if report['status'] == 'passed' else 2
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--id', required=True)
    p.add_argument('--phase', choices=CPU_CAPS, required=True)
    p.add_argument('--seconds', type=int, required=True)
    p.add_argument('--gpu', action='store_true')
    p.add_argument('command', nargs=argparse.REMAINDER)
    a = p.parse_args()
    command = a.command[1:] if a.command[:1] == ['--'] else a.command
    result = run(a.id, a.phase, a.seconds, a.gpu, command)
    print(result, flush=True)
    return 0 if result['status'] == 'passed' else 2


if __name__ == '__main__':
    raise SystemExit(main())
