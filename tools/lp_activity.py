"""Bounded admission checks; utilization is evidence, never attributed to our PID."""
import re
import subprocess
import time


class ActivityPause(ValueError):
    def __init__(self, report):
        self.report = report
        super().__init__('GPU admission paused: ' + report['reason'])


def sample(device, timeout):
    deadline = time.monotonic() + timeout
    def query(fields, selected):
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise ValueError('GPU telemetry deadline')
        args = ['nvidia-smi'] + (['--id=' + device] if selected else [])
        run = subprocess.run(args + [fields, '--format=csv,noheader,nounits'],
                             capture_output=True, text=True, timeout=remaining, check=True)
        return run.stdout.strip()
    utilization = query('--query-gpu=utilization.gpu', True)
    if not utilization.isdigit() or not 0 <= int(utilization) <= 100:
        raise ValueError('GPU utilization telemetry unavailable or malformed')
    applications = query('--query-compute-apps=gpu_uuid,pid', False)
    pids = []
    for line in applications.splitlines():
        fields = [field.strip() for field in line.split(',')]
        if len(fields) != 2 or not re.fullmatch(r'GPU-[0-9a-fA-F-]+', fields[0]) or not fields[1].isdigit() or int(fields[1]) <= 0:
            raise ValueError('GPU process telemetry unavailable or malformed')
        if fields[0] == device:
            pids.append(int(fields[1]))
    return {'utilization': int(utilization), 'pids': pids}


def wait_quiet(device, seconds=300, cancelled=lambda: False, *, probe=None,
               clock=None, sleep=None):
    probe = probe or sample
    clock = clock or time.monotonic_ns
    sleep = sleep or time.sleep
    start = clock()
    deadline = start + round(seconds * 1_000_000_000)
    report = {'schema_version': 1, 'device': device, 'elapsed_ns': 0,
              'samples': 0, 'last_sample': None, 'reason': None}
    try:
        while True:
            now = clock()
            if cancelled():
                report['reason'] = 'cancelled'
                break
            if now >= deadline:
                report['reason'] = 'activity_timeout'
                break
            try:
                report['last_sample'] = probe(device, min(1.0, (deadline-now)/1e9))
                report['samples'] += 1
            except (OSError, ValueError, subprocess.SubprocessError) as error:
                report['reason'] = 'telemetry_unavailable: ' + str(error)[:500]
                break
            if clock() >= deadline:
                report['reason'] = 'activity_timeout'
                break
            current = report['last_sample']
            if current['utilization'] == 0 and not current['pids']:
                report['reason'] = 'quiet'
                break
            sleep(min(.25, max(0, (deadline-clock())/1e9)))
    except KeyboardInterrupt:
        report['reason'] = 'cancelled'
    report['elapsed_ns'] = max(0, clock()-start)
    if report['reason'] != 'quiet':
        raise ActivityPause(report)
    return report
