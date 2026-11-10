"""Exact source bridge for the approved CUDA availability test-only correction."""
from lp_protocol import ROOT, read_json, file_hash

SOURCE = 'crates/optimizer-cuda-sys/src/lib.rs'
BRIDGE = ROOT / 'docs/benchmarks/data/tensor-warp32/prerequisite-source-bridge.json'
MARKER = b'\n#[cfg(test)]\nmod tests {'


def verify_test_only_change(before, after):
    if before.count(MARKER) != 1 or after.count(MARKER) != 1:
        raise ValueError('availability test-module boundary differs')
    if before.split(MARKER)[0] != after.split(MARKER)[0]:
        raise ValueError('production driver bytes changed')


def verify_source_mapping(expected):
    rows = {r['path']: r for r in read_json(BRIDGE)['files']}
    row = rows[SOURCE]
    for path, previous in expected.items():
        current = file_hash(ROOT / path)
        if current == previous:
            continue
        if path != SOURCE or previous != row['before_sha256'] or current != row['after_sha256']:
            raise ValueError('historical numerical source changed: ' + path)
        archive = ROOT / row['frozen_path']
        if file_hash(archive) != previous:
            raise ValueError('availability prior source differs')
        verify_test_only_change(archive.read_bytes(), (ROOT / path).read_bytes())


def verify_cpu_sources(cpu):
    from lp_tensor_warp32_common import numeric_sources
    if set(cpu['numerical_sources']) != set(numeric_sources()):
        raise ValueError('CPU numerical source roster differs')
    verify_source_mapping(cpu['numerical_sources'])
