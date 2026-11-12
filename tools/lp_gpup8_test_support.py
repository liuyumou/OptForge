"""Portable CPU test fixtures; never install or modify live campaign evidence."""
import contextlib
import gzip
import hashlib
import json
from pathlib import Path
import shutil
import tempfile
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / 'tests/fixtures/lp-gpup8-portable-v1'


def historical_path(name):
    """Admit the exact archived metadata bytes before a test uses them."""
    manifest = json.loads((FIXTURE / 'manifest.json').read_text())
    row = next(row for row in manifest['exact_metadata'] if row['path'] == name)
    path = FIXTURE / name
    if hashlib.sha256(path.read_bytes()).hexdigest() != row['sha256']:
        raise ValueError('historical test fixture differs: ' + name)
    return path


def copy_source(root, name):
    target = root / name
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(ROOT / name, target)
    return target


@contextlib.contextmanager
def authority_tree():
    """Real authority/journal/prefix plus an explicitly synthetic preservation tree.

    The small source tree tests preserved-source and hash refusal behavior. It is
    not a replacement for the original whole-campaign preservation receipt.
    """
    import lp_tensor_expanded_authority as a
    with tempfile.TemporaryDirectory() as temp, contextlib.ExitStack() as stack:
        root = Path(temp)
        base = root / 'artifacts/gpup-tensor-expanded-v1'
        data = root / 'docs/benchmarks/data/tensor-expanded'
        journal = base / 'cpu-journal-v1.json'
        ledger = root / 'ledger.jsonl'
        for name, value in [('ROOT', root), ('BASE', base), ('DATA', data), ('JOURNAL', journal), ('LEDGER', ledger)]:
            stack.enter_context(patch.object(a, name, value))
        auth_path = 'docs/benchmarks/data/tensor-expanded/authorization-v1.json'
        auth = json.loads(copy_source(root, auth_path).read_text())
        copy_source(root, auth['prior_accounting']['path'])
        for name in [auth['prior_journal']['path'], 'artifacts/gpup-tensor-expanded-v1/cpu-journal-v1.json']:
            target = root / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(historical_path(name), target)
        for name in ['benchmarks/configs/lp-tensor-warp32-v1.json', 'tools/lp_expansion_oracle.py', 'tools/lp_cpu_admission.py']:
            copy_source(root, name)
        compressed = (FIXTURE / 'ledger-prefix.jsonl.gz').read_bytes()
        manifest = json.loads((FIXTURE / 'manifest.json').read_text())['ledger']
        if hashlib.sha256(compressed).hexdigest() != manifest['sha256']:
            raise ValueError('ledger test fixture differs')
        ledger.write_bytes(gzip.decompress(compressed))
        original_reader = a.ledger_events
        stack.enter_context(patch.object(a, 'ledger_events', side_effect=lambda: original_reader(ledger)))
        preserved = root / 'synthetic-prior-source.txt'
        preserved.write_text('synthetic archived source\n')
        current = root / 'synthetic-current-source.txt'
        current.write_text('synthetic changed source\n')
        prior_ref = dict(a.ref(preserved), path=current.name)
        worktree = base / 'synthetic-worktree.json'
        a.put(worktree, dict(files=[prior_ref]))
        a.put(base / 'source-bridge-v1.json', dict(
            supervisor=a.ref(root / 'tools/lp_cpu_admission.py'),
            prior_worktree=a.ref(worktree),
            prior_mutable=[dict(current=current.name, preserved=a.ref(preserved))],
            retained_arithmetic=[a.ref(root / 'tools/lp_expansion_oracle.py')]))
        a.put(root / 'artifacts/gpup-tensor-warp32-v1/receipt-recovery-v1/pins.json',
              dict(historical_refs=[a.ref(preserved)]))
        yield root


@contextlib.contextmanager
def warp32_preservation_tree():
    """Check actual source contracts with a synthetic image for the hash guard."""
    import lp_tensor_warp32_build as build
    with tempfile.TemporaryDirectory() as temp, contextlib.ExitStack() as stack:
        from lp_resident2_test_support import historical_registration
        stack.enter_context(historical_registration())
        root = Path(temp)
        base = root / 'artifacts/gpup-tensor-warp32-v1'
        base.mkdir(parents=True)
        for name in ['historical-numerical-sources.json', 'historical-bindings.json']:
            shutil.copyfile(historical_path('artifacts/gpup-tensor-warp32-v1/' + name), base / name)
        for directory in ['cuda/lp_pdhg_tensor_warp32', 'cuda/lp_pdhg_tensor_cost']:
            shutil.copytree(ROOT / directory, root / directory)
        copy_source(root, 'tools/lp_cpu_admission.py')
        image = root / 'artifacts/gpup-tensor-cost-v1/study-v1/lp_pdhg_tensor_cost.cubin'
        image.parent.mkdir(parents=True)
        image.write_bytes(b'synthetic image bytes for CPU hash-guard regression test')
        bindings = json.loads((base / 'historical-bindings.json').read_text())
        bindings['old_image_sha256'] = hashlib.sha256(image.read_bytes()).hexdigest()
        (base / 'historical-bindings.json').write_text(json.dumps(bindings))
        for name, value in [('ROOT', root), ('BASE', base), ('SOURCE', root / 'cuda/lp_pdhg_tensor_warp32')]:
            stack.enter_context(patch.object(build, name, value))
        yield image
