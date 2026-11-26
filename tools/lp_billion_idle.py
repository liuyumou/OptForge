"""Fail-closed NVML ownership checks; never signals an unrelated GPU process."""
import ctypes as C
import json
import os
import time
from pathlib import Path
from lp_billion_common import DEVICE, DEVICE_LIMIT, DISK_LIMIT, disk_bytes, require

# Historical idle observations are 804,978,688 bytes including driver memory.
# A fixed conservative allowance also covers short context accounting transitions;
# it must never be rebased on a device that may contain an unlisted workload.
UNATTRIBUTED_LIMIT = 2 << 30


class Process(C.Structure):
    _fields_ = [('pid', C.c_uint), ('memory', C.c_ulonglong),
                ('gpu_instance', C.c_uint), ('compute_instance', C.c_uint)]


class Memory(C.Structure):
    _fields_ = [('total', C.c_ulonglong), ('free', C.c_ulonglong), ('used', C.c_ulonglong)]


class Utilization(C.Structure):
    _fields_ = [('gpu', C.c_uint), ('memory', C.c_uint)]


class Nvml:
    def __init__(self):
        self.lib = C.CDLL('libnvidia-ml.so.1')
        self.check(self.lib.nvmlInit_v2())
        self.device = C.c_void_p()
        self.check(self.lib.nvmlDeviceGetHandleByUUID(DEVICE.encode(), C.byref(self.device)))

    @staticmethod
    def check(code):
        require(code == 0, 'NVML telemetry failure: '+str(code))

    def processes(self):
        processes = {}
        for kind in ['Compute', 'Graphics', 'MPSCompute']:
            count = C.c_uint(1024)
            items = (Process*1024)()
            self.check(getattr(self.lib, 'nvmlDeviceGet'+kind+'RunningProcesses_v3')(
                self.device, C.byref(count), items))
            require(count.value <= 1024, 'GPU process inventory bound')
            for item in items[:count.value]:
                require(item.memory != (1 << 64)-1, 'GPU memory accounting unavailable')
                processes[item.pid] = max(processes.get(item.pid, 0), item.memory)
        return processes

    def sample(self):
        start = time.monotonic_ns()
        before = self.processes()
        memory, utilization = Memory(), Utilization()
        self.check(self.lib.nvmlDeviceGetMemoryInfo(self.device, C.byref(memory)))
        self.check(self.lib.nvmlDeviceGetUtilizationRates(self.device, C.byref(utilization)))
        after = self.processes()
        # Bracket memory sampling so ordinary context creation/destruction cannot
        # falsely appear as an unowned allocation between sequential NVML calls.
        processes = {pid: max(before.get(pid, 0), after.get(pid, 0))
                     for pid in before.keys() | after.keys()}
        end = time.monotonic_ns()
        require(end-start <= 1_000_000_000, 'GPU telemetry sample exceeded one second')
        return dict(start_ns=start, end_ns=end, processes=processes,
                    processes_before=before, processes_after=after,
                    free=memory.free, used=memory.used, total=memory.total,
                    utilization=utilization.gpu)

    def close(self):
        self.check(self.lib.nvmlShutdown())


def quiet(required_bytes=0):
    sensor = Nvml()
    try:
        samples = []
        for i in range(3):
            s = sensor.sample()
            require(not s['processes'] and s['utilization'] == 0, 'Pro6000 is not idle')
            validate_gpu(s, set())
            require(s['free'] >= required_bytes+(2 << 30), 'insufficient device headroom')
            samples.append(s)
            if i != 2:
                time.sleep(.25)
        return samples
    finally:
        sensor.close()


def physical_pids(processes):
    result = set()
    for item in processes:
        result.add(item['pid'])
        try:
            for line in Path(f'/proc/{item["pid"]}/status').read_text().splitlines():
                if line.startswith('NSpid:'):
                    result.update(map(int, line.split()[1:]))
        except FileNotFoundError:
            pass
    return result


def validate_gpu(sample, owned):
    foreign = set(sample['processes']) - owned
    require(not foreign, 'foreign GPU process: '+str(sorted(foreign)))
    require(sum(sample['processes'].values()) <= DEVICE_LIMIT, 'owned GPU memory ceiling')
    require(sample['used']-sum(sample['processes'].values()) <= UNATTRIBUTED_LIMIT,
            'unattributed GPU memory exceeds fixed idle allowance')


def install(supervisor, request):
    """Add checks to the original supervisor; retain its cadence and cleanup."""
    original = supervisor.snapshot
    sensor = None
    last_gpu = last_disk = 0
    trace = Path(request['output']+'.capacity.jsonl')
    storage = None
    if request.get('storage_policy') is not None:
        from lp_billion_storage import DiskMonitor, POLICY
        require(request['storage_policy'] == POLICY, 'storage policy domain')
        storage = DiskMonitor(request['storage_initial'], request['output']+'.storage.jsonl')
        original_cleanup = supervisor.terminate_descendants

        def cleanup(*args, **kwargs):
            try:
                storage.close()
            finally:
                # Cleanup must still run if scanner shutdown or trace writing fails.
                result = original_cleanup(*args, **kwargs)
            return result

        supervisor.terminate_descendants = cleanup

    def snapshot(*args, **kwargs):
        nonlocal sensor, last_gpu, last_disk
        observation = original(*args, **kwargs)
        now = time.monotonic_ns()
        record = {'observed_ns': now}
        if request.get('billion_gpu') and now-last_gpu >= 250_000_000:
            sensor = sensor or Nvml()
            sample = sensor.sample()
            owned = physical_pids(observation['processes'])
            # Refresh once to include a child born between process scan and NVML.
            if set(sample['processes'])-owned:
                owned |= physical_pids(original(*args, **kwargs)['processes'])
            record['gpu'] = sample
            record['owned_physical_pids'] = sorted(owned)
            with trace.open('a') as f:
                f.write(json.dumps(record, sort_keys=True)+'\n')
            validate_gpu(sample, owned)
            last_gpu = sample['end_ns']
        if storage is not None:
            storage.tick()
        elif now-last_disk >= 1_000_000_000:
            amount = disk_bytes()
            require(amount <= DISK_LIMIT, 'owned evidence/build disk ceiling')
            last_disk = time.monotonic_ns()
        return observation

    supervisor.snapshot = snapshot
