"""Exact additive module-registration bridge for frozen historical CPU fixtures."""
import contextlib
import hashlib
from unittest.mock import patch
from lp_protocol import ROOT, file_hash, read_json

@contextlib.contextmanager
def historical_registration():
    name='crates/optimizer-lp-cuda/src/lib.rs'
    bridge=read_json(ROOT/'docs/benchmarks/data/resident2/prerequisite-source-bridge.json')
    row=next(r for r in bridge['files'] if r['path']==name)
    before=(ROOT/row['frozen_path']).read_bytes()
    addition=b'\n/// SPEC-0024 isolated native resident execution.\n#[cfg(feature = "precision-research")]\npub mod resident2;\n'
    if hashlib.sha256(before).hexdigest()!=row['before_sha256'] or (ROOT/name).read_bytes()!=before+addition:
        raise ValueError('resident2 registration differs from exact additive bridge')
    if file_hash(ROOT/name)!=row['after_sha256']:
        raise ValueError('resident2 source bridge hash differs')
    def historical(path):
        return row['before_sha256'] if path==ROOT/name else file_hash(path)
    with patch('lp_tensor_warp32_availability_bridge.file_hash',side_effect=historical):
        yield
