"""Read-only GPU ownership diagnostics; no CUDA context or device mutations."""
import argparse
import ctypes as C
import os
import subprocess
import time
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from lp_billion_common import BASE, DEVICE, load, put, ref, require
from lp_billion_idle import Nvml, Process, Memory
from lp_billion_availability import idle, stable


class LegacyProcess(C.Structure):
    _fields_ = [('pid', C.c_uint), ('memory', C.c_ulonglong)]


class MemoryV2(C.Structure):
    _fields_ = [('version', C.c_uint), ('total', C.c_ulonglong),
                ('reserved', C.c_ulonglong), ('free', C.c_ulonglong),
                ('used', C.c_ulonglong)]


def command(args):
    try:
        p = subprocess.run(args, capture_output=True, text=True, timeout=15)
        return dict(command=args, returncode=p.returncode, stdout=p.stdout, stderr=p.stderr)
    except (OSError, subprocess.TimeoutExpired) as error:
        return dict(command=args, error=str(error))


def visible_handles():
    holders = []
    seen = denied = vanished = 0
    for p in Path('/proc').iterdir():
        if not p.name.isdecimal():
            continue
        seen += 1
        try:
            fds = []
            for fd in (p/'fd').iterdir():
                try:
                    target = os.readlink(fd)
                    if target.startswith(('/dev/nvidia', '/dev/dri/')):
                        fds.append(dict(fd=fd.name, target=target))
                except FileNotFoundError:
                    pass
            if fds:
                fields = dict(line.split(':', 1) for line in (p/'status').read_text().splitlines()
                              if line.startswith(('Name:', 'PPid:', 'Uid:', 'NSpid:')))
                holders.append(dict(pid=int(p.name), fields=fields, fds=fds))
        except PermissionError:
            denied += 1
        except FileNotFoundError:
            vanished += 1
    return dict(visible_processes=seen, permission_denied=denied,
                vanished=vanished, holders=holders,
                scope='Visible procfs only; no command lines, environments or process memory read.')


def api_snapshot():
    sensor = Nvml()
    try:
        result = dict(process_abi_bytes=dict(legacy=C.sizeof(LegacyProcess), current=C.sizeof(Process)))
        memory = MemoryV2()
        memory.version = C.sizeof(memory) | (2 << 24)
        code = sensor.lib.nvmlDeviceGetMemoryInfo_v2(sensor.device, C.byref(memory))
        result['memory_v2'] = dict(returncode=code, **{name:getattr(memory,name) for name,_ in memory._fields_})
        result['process_apis'] = []
        for kind in ['Compute', 'Graphics', 'MPSCompute']:
            for suffix, structure in [('', LegacyProcess), ('_v2', Process), ('_v3', Process)]:
                name = 'nvmlDeviceGet'+kind+'RunningProcesses'+suffix
                count = C.c_uint(1024)
                items = (structure*1024)()
                code = getattr(sensor.lib, name)(sensor.device, C.byref(count), items)
                processes = [dict(pid=p.pid, memory=p.memory) for p in items[:count.value]] if code == 0 and count.value <= 1024 else None
                result['process_apis'].append(dict(api=name, returncode=code, count=count.value, processes=processes))
        mode = C.c_uint()
        result['accounting_mode'] = dict(returncode=sensor.lib.nvmlDeviceGetAccountingMode(sensor.device, C.byref(mode)), value=mode.value)
        memory_v1 = Memory()
        code = sensor.lib.nvmlDeviceGetMemoryInfo(sensor.device, C.byref(memory_v1))
        result['memory_v1'] = dict(returncode=code, total=memory_v1.total, free=memory_v1.free, used=memory_v1.used)
        result['loaded_nvml_paths'] = sorted({line.split()[-1] for line in Path('/proc/self/maps').read_text().splitlines() if 'libnvidia-ml' in line})
        return result
    finally:
        sensor.close()


def main(identity, seconds):
    require(identity and Path(identity).name == identity and identity not in ['.', '..'], 'diagnostic identity')
    require(300 <= seconds <= 600, 'bounded observation window')
    out = BASE/identity
    out.mkdir(exist_ok=False)
    put(out/'initial.json', dict(timestamp=datetime.now(ZoneInfo('Asia/Shanghai')).isoformat(),
        device=DEVICE, api=api_snapshot(), handles=visible_handles(),
        pid_namespace=os.readlink('/proc/self/ns/pid'), init_name=Path('/proc/1/comm').read_text().strip(),
        container_marker=Path('/.dockerenv').exists(),
        gpu_information=Path('/proc/driver/nvidia/gpus/0000:1f:00.0/information').read_text(),
        nvidia_smi=command(['nvidia-smi', '-i', DEVICE, '-q']),
        process_monitor=command(['nvidia-smi', 'pmon', '-i', '2', '-c', '3']),
        kernel_log=command(['dmesg', '--level=err,warn']),
        driver_clients_exposed=Path('/proc/driver/nvidia/clients').exists()))
    samples = []
    started = time.monotonic()
    next_observation = started
    ready = False
    while time.monotonic()-started <= seconds:
        now = time.monotonic()
        if now < next_observation:
            time.sleep(min(1, next_observation-now))
            continue
        sensor = Nvml()
        try:
            sample = sensor.sample()
        finally:
            sensor.close()
        path = BASE/'availability/operational-gpu-v9'/(str(sample['start_ns'])+'.json')
        put(path, sample)
        samples.append(ref(path))
        observed = [load(p) for p in sorted(path.parent.glob('*.json'), key=lambda p:int(p.stem))]
        ready = stable(observed, time.monotonic_ns())
        print(dict(elapsed_seconds=round(now-started), idle=idle(sample), used_gib=sample['used']/2**30,
                   utilization=sample['utilization'], processes=sample['processes'], stable_five_minutes=ready), flush=True)
        if ready:
            break
        next_observation = now+60
    put(out/'result.json', dict(status='observed_idle' if ready else 'idle_gate_not_met',
        initial=ref(out/'initial.json'), samples=samples, final_api=api_snapshot(), final_handles=visible_handles(),
        device_mutations=False, cuda_contexts_created=False, other_processes_signalled=False,
        limitation='No host PID namespace or host process attribution is supplied by this container. Empty inventories do not establish device idleness.'))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--id', required=True)
    parser.add_argument('--seconds', type=int, default=360)
    args = parser.parse_args()
    main(args.id, args.seconds)
