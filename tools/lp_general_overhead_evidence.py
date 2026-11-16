"""Portable delta archive for FP4 surrounding-work development; prior bytes stay exact."""
import argparse
import gzip
import tarfile
from pathlib import Path

from lp_general_common import BASE, ROOT, load, put, ref, require
from lp_general_portable import digest, archive_ref
from lp_general_fast_portable import replay


def archive(identity):
    out = BASE / 'portable' / identity
    out.mkdir(parents=True, exist_ok=False)
    prior = BASE / 'portable/fast-delivery-v1/EVIDENCE.json'
    preserved = 0
    for item in load(prior)['files']:
        path = ROOT / item['path']
        if path.is_relative_to(BASE):
            require(path.stat().st_size == item['bytes'] and digest(path) == item['sha256'], 'historical bytes changed ' + str(path))
            preserved += 1
    files = [prior, BASE / "operational-readmission-v1.json", BASE / "operational-readmission-v2.json"]
    active = {p.name.removesuffix('.reservation.json') for p in (BASE / 'resources').glob('*.reservation.json')
              if not p.with_name(p.name.replace('.reservation.json', '.settlement.json')).exists()}
    for path in BASE.glob('fast-overhead-*'):
        files.extend([path] if path.is_file() else [p for p in path.rglob('*') if p.is_file()])
    files.extend(p for p in (BASE / 'fast-image-v10').rglob('*') if p.is_file())
    for path in (BASE / 'sources').glob('fast-overhead-*'):
        if path.name not in active:
            files.extend(p for p in path.rglob('*') if p.is_file())
    files.extend(p for p in (BASE / 'resources').glob('fast-overhead-*') if not any(p.name.startswith(a + '.') for a in active))
    campaigns = []
    for p in BASE.glob('fast-overhead-*/freeze.json'):
        f = load(p)
        if f.get('kind') != 'fast-proposal-development':
            continue
        campaigns.append(p.parent.name)
        files += [ROOT / m['model']['path'] for m in f['models']]
        files += [ROOT / c[k]['path'] for c in f['cells'] for k in ['binary', 'image']]
    admission = load(BASE / 'fast-overhead-admission-v1.json')
    files += [ROOT / c[k]['path'] for c in admission['comparisons'] for k in ['before', 'after']]
    files += list((ROOT / 'tools').glob('*.py'))
    files += [ROOT / 'artifacts/gpup-checker2-v1/build-v5/executor']
    public = BASE / 'public-development-v1/manifest.json'
    pub = load(public)
    files += [public, ROOT / pub['distribution_license']['path']]
    files += [ROOT / m[k]['path'] for m in pub['models'] for k in ['source', 'model']]
    files += [ROOT / p for p in ['docs/benchmarks/lp-general-overhead.md', 'docs/benchmarks/lp-general-overhead-results.json', 'docs/benchmarks/lp-general-overhead-profile-results.json',
        'docs/specifications/SPEC-0045-general-lowbit-lp.md', 'research/lp-general-lowbit/README.md']]
    objects, manifest = {}, []
    for p in sorted(set(files)):
        h, n = digest(p), p.stat().st_size
        manifest.append(dict(path=str(p.relative_to(ROOT)), sha256=h, bytes=n))
        objects.setdefault(h, p)
    groups, group, size = [], [], 0
    for h, p in sorted(objects.items()):
        n = p.stat().st_size
        if group and size + n > 128 << 20:
            groups.append(group)
            group, size = [], 0
        group.append((h, p))
        size += n
    if group:
        groups.append(group)
    parts = []
    for i, group in enumerate(groups):
        path = out / f'objects-{i:03d}.tar.gz'
        with path.open('xb') as raw, gzip.GzipFile(fileobj=raw, mode='wb', mtime=0, compresslevel=4) as z, tarfile.open(fileobj=z, mode='w|') as tar:
            for h, p in group:
                info = tar.gettarinfo(str(p), arcname='objects/' + h)
                info.uid = info.gid = 0
                info.uname = info.gname = ''
                info.mtime = 0
                with p.open('rb') as source:
                    tar.addfile(info, source)
        parts.append(dict(archive=archive_ref(path), bytes=path.stat().st_size))
    mp = out / 'EVIDENCE.json'
    put(mp, dict(files=manifest, campaigns=campaigns, prior=[ref(prior)], preserved_scientific_files=preserved,
        unique_objects=len(objects), unique_bytes=sum(p.stat().st_size for p in objects.values())))
    put(out / 'receipt.json', dict(manifest=ref(mp), parts=parts, files=len(manifest), logical_bytes=sum(r['bytes'] for r in manifest),
        unique_objects=len(objects), unique_bytes=sum(p.stat().st_size for p in objects.values()),
        compressed_bytes=sum(p['bytes'] for p in parts), prior_scientific_files_verified=preserved))
    print(dict(files=len(manifest), preserved=preserved, compressed_bytes=sum(p['bytes'] for p in parts)), flush=True)


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('action', choices=['archive', 'replay'])
    p.add_argument('--id', required=True)
    a = p.parse_args()
    (archive if a.action == 'archive' else replay)(a.id)
