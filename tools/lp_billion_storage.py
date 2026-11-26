"""Approved asynchronous storage policy; process/GPU sampling never waits on a scan."""
import json
import subprocess
import sys
import time
from pathlib import Path

from lp_billion_common import BASE, DISK_LIMIT, NS, native_inventory, require

POLICY = 'async-v1'
SCAN_SECONDS = 60
STALE_SECONDS = 90
INTERVAL_SECONDS = 5
FINAL_RESERVE_SECONDS = 75


def observation():
    start = time.monotonic_ns()
    value = native_inventory(BASE, timeout_seconds=SCAN_SECONDS)
    return dict(started_ns=start, completed_ns=time.monotonic_ns(), value=value)


def validate(record):
    require(type(record) is dict and set(record) == {'started_ns', 'completed_ns', 'value'},
            'storage observation schema')
    start, end = record['started_ns'], record['completed_ns']
    require(type(start) is int and type(end) is int and 0 <= start <= end,
            'storage observation timestamps')
    require(end - start <= SCAN_SECONDS * NS, 'storage scan duration')
    value = record['value']
    require(type(value) is dict and set(value) == {'bytes', 'files'} and
            all(type(v) is int and 0 <= v < 2**64 for v in value.values()),
            'storage observation count')
    require(value['bytes'] <= DISK_LIMIT, 'owned evidence/build disk ceiling')


class DiskMonitor:
    def __init__(self, initial, trace, *, clock=time.monotonic_ns,
                 command=None, spawn=subprocess.Popen):
        validate(initial)
        self.last = initial
        self.trace = Path(trace)
        self.clock, self.command, self.spawn = clock, command, spawn
        self.process, self.started = None, None
        self.closed, self.failure = False, None
        self.used = False

    def record(self, event, **fields):
        with self.trace.open('a') as stream:
            stream.write(json.dumps(dict(event=event, **fields), sort_keys=True) + '\n')

    def poll(self, now):
        if self.process is None:
            return
        require(now - self.started < SCAN_SECONDS * NS, 'storage scan timeout')
        if self.process.poll() is not None:
            stdout, stderr = self.process.communicate(timeout=0.1)
            require(self.process.returncode == 0 and not stderr, 'asynchronous storage scan failed')
            result = json.loads(stdout)
            validate(result)
            require(self.started <= result['started_ns'] <= result['completed_ns'] <= now,
                    'storage scan clock domain')
            self.last = result
            self.process = None
            self.record('scan', observation=result)

    def tick(self):
        if self.closed:
            return  # No scans during cleanup; mandatory final scan gates settlement.
        self.used = True
        try:
            now = self.clock()
            self.poll(now)
            require(0 <= now - self.last['completed_ns'] < STALE_SECONDS * NS,
                    'storage observation stale')
            if self.process is None and now - self.last['completed_ns'] >= INTERVAL_SECONDS * NS:
                command = self.command or [sys.executable, '-B', __file__, 'scan']
                self.started = self.clock()
                self.process = self.spawn(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                          text=True, close_fds=True)
        except Exception as error:
            self.failure = f'{type(error).__name__}: {error}'
            raise

    def close(self):
        if self.closed:
            return
        self.closed = True
        try:
            self.poll(self.clock())  # Do not lose an already completed failed scan.
        except Exception as error:
            self.failure = self.failure or f'{type(error).__name__}: {error}'
        if self.process is not None:
            # Popen owns this unreaped child; never signal a discovered foreign PID.
            if self.process.poll() is None:
                self.process.kill()
            try:
                self.process.communicate(timeout=0.2)
                self.process = None
            except subprocess.TimeoutExpired:
                pass  # Original descendant cleanup must reap remaining owned children.
        if self.used:
            self.record('closed', error=self.failure)


def final_check(trace):
    """A passing process receipt alone never establishes storage-policy success."""
    records = [json.loads(line) for line in Path(trace).read_text().splitlines()]
    require(records and records[-1].get('event') == 'closed', 'storage monitor closure missing')
    require(all(r.get('error') is None for r in records), 'storage monitor failed')
    result = observation()
    validate(result)
    return result


if __name__ == '__main__':
    require(sys.argv[1:] == ['scan'], 'storage scanner command')
    print(json.dumps(observation()), flush=True)
