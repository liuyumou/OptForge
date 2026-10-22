"""Bind CPU-only PR repairs to the preserved GPUP-ASSESS source cohorts."""
import hashlib

import lp_assess_review as prior
from lp_protocol import ROOT, checked_reference, file_hash, read_json

RECEIPT = ROOT / 'docs/benchmarks/data/assess/pr-review-final-source.json'
ALLOWED = {
    'crates/optimizer-lp/src/assess.rs',
    'crates/optimizer-experiment/src/lp_assess.rs',
    'tools/report_lp_assess.py',
    'tests/integration/test_lp_assess.py',
}


def section(source, start, end):
    return source[source.index(start):source.index(end)].encode()


def review():
    r = read_json(RECEIPT)
    if (r['identity'] != 'gpup-assess-pr-review-v1' or r['gpu_seconds'] != 0
            or r['new_device_acceptance'] is not False
            or r['review_tool_sha256'] != file_hash(ROOT / 'tools/lp_assess_pr_review.py')
            or r['ledger_sha256'] != 'dd5d7281a152d8fb56df373d913ac2dc7077aac9cf6ba2eb5f6e7781493ea52c'):
        raise ValueError('assessment PR review authority differs')
    if checked_reference(ROOT, r['parent_review']) != prior.RECEIPT:
        raise ValueError('assessment PR review parent differs')
    parent = read_json(prior.RECEIPT)
    if parent['review_tool_sha256'] != file_hash(ROOT / 'tools/lp_assess_review.py'):
        raise ValueError('assessment prior review tool changed')
    previous_path = checked_reference(ROOT, r['previous_pr_review'])
    if previous_path != ROOT / 'docs/benchmarks/data/assess/pr-review-source.json':
        raise ValueError('assessment previous PR review parent differs')
    previous = read_json(previous_path)
    if (previous['identity'] != 'gpup-assess-pr-review-v1'
            or len(previous['files']) != len(ALLOWED)
            or {f['path'] for f in previous['files']} != ALLOWED):
        raise ValueError('assessment previous PR review differs')
    previous_sources = {f['path']: f for f in r['previous_sources']}
    if set(previous_sources) != ALLOWED or len(previous_sources) != len(r['previous_sources']):
        raise ValueError('assessment previous PR source scope differs')
    if file_hash(checked_reference(ROOT, r['previous_tool'])) != previous['review_tool_sha256']:
        raise ValueError('assessment previous PR review tool differs')
    for f in previous['files']:
        if file_hash(checked_reference(ROOT, previous_sources[f['path']]['source'])) != f['reviewed_sha256']:
            raise ValueError('assessment previous PR reviewed source differs')
        checked_reference(ROOT, f['before'])
        checked_reference(ROOT, f['diff'])
    files = {f['path']: f for f in r['files']}
    old_files = {f['path']: f for f in parent['files']}
    if (len(files) != len(r['files']) or set(files) != ALLOWED
            or len(old_files) != len(parent['files']) or set(old_files) != prior.ALLOWED):
        raise ValueError('assessment PR review file scope differs')
    for name, f in old_files.items():
        before = files[name]['before_sha256'] if name in files else file_hash(ROOT / name)
        if before != f['reviewed_sha256']:
            raise ValueError('assessment prior reviewed source differs: ' + name)
    for name, f in files.items():
        if (file_hash(ROOT / name) != f['reviewed_sha256']
                or f['before']['sha256'] != f['before_sha256']
                or f['measured_sha256'] != old_files.get(name, {}).get('measured_sha256', f['before_sha256'])):
            raise ValueError('assessment undeclared PR source change: ' + name)
        checked_reference(ROOT, f['before'])
        checked_reference(ROOT, f['diff'])
    checked_reference(ROOT, parent['original_report'])
    checked_reference(ROOT, parent['replay_audit'])
    proofs = [
        ('crates/optimizer-lp/src/assess.rs', '/// The executor commits', '#[cfg(test)]', 'unchanged_execution_body_sha256'),
        ('crates/optimizer-experiment/src/lp_assess.rs', 'pub fn assessment(', 'fn inputs(', 'unchanged_host_authority_sha256'),
        ('crates/optimizer-experiment/src/lp_assess.rs', 'fn write_new(', '#[cfg(test)]', 'unchanged_solve_and_output_sha256'),
    ]
    for name, start, end, key in proofs:
        before = checked_reference(ROOT, files[name]['before']).read_text()
        old = section(before, start, end)
        current = section((ROOT / name).read_text(), start, end)
        if current != old or hashlib.sha256(current).hexdigest() != r[key]:
            raise ValueError('assessment measured execution/authority changed: ' + key)
    return r


def projected_sha(name):
    if name not in ALLOWED | prior.ALLOWED:
        return file_hash(ROOT / name)
    r = review()
    for f in r['files']:
        if f['path'] == name:
            return f['measured_sha256']
    parent = read_json(prior.RECEIPT)
    return next(f['measured_sha256'] for f in parent['files'] if f['path'] == name)
