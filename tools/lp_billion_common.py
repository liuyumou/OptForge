"""Approved, independent billion-nonzero development allocation (SPEC-0046)."""
import hashlib
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = Path('/storage/ai-optimizer-billion-v1')
DEVICE = 'GPU-6721b13a-30f9-83ec-dace-ba2d9738556f'
NS = 1_000_000_000
CPU_CAPS = dict(implementation=6000, native=20000, admission=28000,
                development=118000, reporting=62000, cleanup=6000)
GPU_CAPS = dict(admission=5500, development=24500)
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


def disk_bytes():
    total, seen = 0, set()
    pending = [BASE]
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
