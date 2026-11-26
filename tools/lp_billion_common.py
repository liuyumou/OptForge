"""Approved, independent billion-nonzero development allocation (SPEC-0046)."""
import hashlib
import json
import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = Path('/storage/ai-optimizer-billion-v1')
DEVICE = 'GPU-6721b13a-30f9-83ec-dace-ba2d9738556f'
NS = 1_000_000_000
CPU_CAPS = dict(implementation=10000, native=26000, admission=72000,
                development=260000, reporting=200000, cleanup=2000)
GPU_CAPS = dict(admission=12000, development=56000)
HOST_LIMIT = 128 << 30
DEVICE_LIMIT = 80 << 30
DISK_LIMIT = 400 << 30
MAX_GAP_NS = NS


def require(condition, message):
    if not condition:
        raise ValueError(message)


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        while b := f.read(1 << 20):
            h.update(b)
    return h.hexdigest()


def ref(path):
    p = Path(path).resolve()
    for namespace, root in [('evidence', BASE), ('repo', ROOT)]:
        if p.is_relative_to(root):
            return dict(namespace=namespace, path=str(p.relative_to(root)),
                        bytes=p.stat().st_size, sha256=digest(p))
    raise ValueError('reference outside admitted roots')


def resolve(item):
    root = {'evidence': BASE, 'repo': ROOT}[item['namespace']]
    p = (root/item['path']).resolve()
    require(p.is_relative_to(root) and ref(p) == item, 'source binding differs')
    return p


def load(path):
    return json.loads(Path(path).read_text())


def put(path, value):
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open('x') as f:
        json.dump(value, f, sort_keys=True, indent=2, allow_nan=False)
        f.write('\n')
        f.flush()
        os.fsync(f.fileno())
    return ref(p)


def legacy_disk_bytes(root=None):
    total, seen = 0, set()
    pending = [BASE if root is None else Path(root)]
    while pending:
        directory = pending.pop()
        try:
            with os.scandir(directory) as entries:
                for entry in entries:
                    try:
                        if entry.is_symlink():
                            continue
                        if entry.is_dir(follow_symlinks=False):
                            pending.append(entry.path)
                            continue
                        s = entry.stat(follow_symlinks=False)
                    except FileNotFoundError:
                        continue
                    key = s.st_dev, s.st_ino
                    if key not in seen:
                        seen.add(key)
                        total += s.st_size
        except FileNotFoundError:
            continue
    return total


INVENTORY_ROOT = Path('/storage/ai-optimizer-billion-v1')
INVENTORY_BINDING = INVENTORY_ROOT/'disk-inventory-binding-v1.json'
INVENTORY_BINDING_SHA = '723e48c78c80936af78e4f8f35eec11edff4213f52ea6115efb24fff9b9a5795'


def inventory_command(root):
    require(digest(INVENTORY_BINDING)==INVENTORY_BINDING_SHA,'storage inventory binding integrity')
    binding=load(INVENTORY_BINDING)
    require(binding['status']=='retained_for_cpu_bootstrap','storage inventory binding status')
    executable=INVENTORY_ROOT/binding['executable']['path']
    source=ROOT/binding['source']['path']
    require(digest(executable)==binding['executable']['sha256'] and digest(source)==binding['source']['sha256'],'storage inventory executable/source integrity')
    return [str(executable), str(root)]


def inventory_result(result):
    require(result.returncode==0 and not result.stderr,'exact storage inventory failed')
    value=json.loads(result.stdout)
    require(set(value)=={'bytes','files'} and all(type(value[k]) is int and 0<=value[k]<2**64 for k in value),'storage inventory integer domain')
    return value


def native_inventory(root, timeout_seconds=.9):
    require(type(timeout_seconds) in (int, float) and 0 < timeout_seconds <= 60,
            'bounded storage inventory timeout')
    result=subprocess.run(inventory_command(root),capture_output=True,text=True,timeout=timeout_seconds)
    return inventory_result(result)


def disk_bytes():
    return native_inventory(BASE)['bytes']


def preflight_disk_bytes():
    """Allow cold storage latency before launch; runtime sampling stays unchanged."""
    return native_inventory(BASE, timeout_seconds=60)['bytes']
