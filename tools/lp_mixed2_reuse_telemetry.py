"""Diagnostic-only wrappers; never installed in a scientific timing run.

The retained supervisor and all limits are unchanged. Wrappers measure snapshot
work and scheduling counters; their own disturbance limits causal inference.
"""
import json
import os
from pathlib import Path
import time


def install(supervisor, path):
    original = supervisor.snapshot
    original_send = supervisor.send
    original_receive = supervisor.receive
    original_atomic = supervisor.atomic_json

    def record(kind, begin, **fields):
        now = time.monotonic_ns()
        try:
            sched = Path('/proc/self/schedstat').read_text().strip()
            wait = Path('/proc/self/wchan').read_text().strip()
        except OSError:
            sched = wait = 'unavailable'
        raw = json.dumps(dict(kind=kind, pid=os.getpid(), begin_ns=begin,
                             end_ns=now, schedstat=sched, wchan=wait, **fields))+'\n'
        fd = os.open(path, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o600)
        try:
            os.write(fd, raw.encode())
        finally:
            os.close(fd)

    def snapshot(*args, **kwargs):
        begin = time.monotonic_ns()
        record('snapshot_begin', begin)
        result = original(*args, **kwargs)
        record('snapshot', begin, threads=result['threads'], rss=result['rss_bytes'])
        return result

    def send(channel, value):
        begin = time.monotonic_ns()
        result = original_send(channel, value)
        record(value['event'], begin)
        return result

    def receive(channel):
        begin = time.monotonic_ns()
        result = original_receive(channel)
        record('receive', begin, message=result)
        return result

    def atomic_json(*args, **kwargs):
        begin = time.monotonic_ns()
        result = original_atomic(*args, **kwargs)
        record('atomic_json', begin, path=str(args[0]))
        return result

    supervisor.snapshot = snapshot
    supervisor.send = send
    supervisor.receive = receive
    supervisor.atomic_json = atomic_json
