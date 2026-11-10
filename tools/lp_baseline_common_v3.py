"""Immutable GPUP-BASELINE artifacts and certificate binding (ADR-0048)."""
import hashlib
import json
import math
import os
from pathlib import Path
import struct

from lp_baseline_contract import ROOT, canonicalize, read, require

BASE = ROOT / 'artifacts/gpup-external-baseline-v3'
PROPOSAL = ROOT / 'benchmarks/configs/lp-external-baseline-proposal-v2.json'
NS = 1_000_000_000
DEVICE = 'GPU-6721b13a-30f9-83ec-dace-ba2d9738556f'
CPU_CAPS = dict(implementation=2400, hardware=240, admission=2400,
                screening=8960, reporting=1200, cleanup=800)
GPU_CAPS = dict(hardware=60, admission=420, screening=3120)


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def ref(path):
    path = Path(path).resolve()
    require(path.is_relative_to(ROOT), 'reference outside repository')
    return dict(path=str(path.relative_to(ROOT)), sha256=digest(path.read_bytes()))


def checked(item):
    path = (ROOT / item['path']).resolve()
    require(not Path(item['path']).is_absolute() and path.is_relative_to(ROOT), 'reference escapes root')
    require(ref(path) == item, 'artifact binding differs: ' + item['path'])
    return path


def put(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = (json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + '\n').encode()
    with path.open('xb') as out:
        out.write(raw)
        out.flush()
        os.fsync(out.fileno())
    return ref(path)


def load(path):
    return read(path)[1]


def equal_f64(observed, expected):
    """Readback comparison never uses a numeric tolerance or coalesces zeros."""
    require(len(observed) == len(expected), 'readback length differs')
    require(all(struct.pack('!d', float(x)) == struct.pack('!d', float(y))
                for x, y in zip(observed, expected)), 'readback binary64 differs')


def vector(value):
    if value is None:
        return None
    result = [float(x) for x in value]
    return result if all(math.isfinite(x) for x in result) else None


def options(seconds):
    return dict(schema_version=1, seed=17, threads=1, node_limit=None,
                iteration_limit=50000, time_limit_ms=max(1, int(seconds * 1000)),
                tolerances=dict(absolute=1e-9, relative=1e-9, integrality=1e-9))


def verify_certificate(certificate, candidate, model, checker):
    c = load(checked(certificate))
    require(c['kind'] == 'lp-baseline-certificate' and c['schema_version'] == 1, 'certificate version')
    require(c['candidate_sha256'] == ref(checked(candidate))['sha256'], 'candidate binding')
    require(c['model_sha256'] == ref(checked(model))['sha256'], 'original binding')
    require(c['checker_binary_sha256'] == ref(checked(checker))['sha256'], 'checker binding')
    require(c['tolerances'] == dict(absolute=1e-9, relative=1e-9, integrality=1e-9), 'quality policy')
    require(type(c['accepted']) is bool, 'certificate outcome type')
    if c['accepted']:
        require(c['eligible_transport_and_status'] and c['validation']['feasible']
                and c['gap_closed'] is True and c['bound'] is not None
                and c['gap_upper'] is not None and c['gap_upper'] >= 0, 'inconsistent certificate')
    return c


def tiny_model(sense, shape):
    """Known nonzero row multipliers, nonsequential IDs and objective offsets."""
    bound = lambda v: dict(kind='finite', value=v)
    lower, upper = (1., 1.) if shape == 'equality' else (1., 2.)
    return dict(schema_version=1, model_id='baseline-' + sense + '-' + shape,
                variables=[dict(id=9, domain='continuous', lower=bound(0.), upper=bound(3.))],
                constraints=[dict(id=7, lower=bound(lower), upper=bound(upper),
                                  terms=[dict(variable_id=9, coefficient=1.)])],
                objective=dict(sense=sense, offset=3.25,
                               terms=[dict(variable_id=9, coefficient=1.)]))


def canonical_file(original, path):
    return put(path, canonicalize(Path(original).read_bytes()))
