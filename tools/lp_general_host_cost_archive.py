"""Portable local host-cost delta, using the admitted original serial replay."""
import argparse
import gzip
import tarfile

from lp_general_common import BASE, ROOT, load, put, require
from lp_general_portable import digest, archive_ref as ref
from lp_general_scale_portable import replay, verify_streams


def archive(identity, campaign):
    out = BASE/'portable'/identity
    out.mkdir(parents=True, exist_ok=False)
    active = {p.name.removesuffix('.reservation.json') for p in (BASE/'resources').glob('*.reservation.json')
              if not p.with_name(p.name.replace('.reservation.json', '.settlement.json')).exists()}
    files = []
    names = {'scale-cpu-v8', 'scale-image-v8', 'scale-cpu-v9', 'scale-image-v9', campaign}
    for p in BASE.rglob('*'):
        if not p.is_file() or p.is_symlink() or p.name.endswith('.lock'):
            continue
        rel = p.relative_to(BASE)
        if rel.parts[0] == 'portable':
            continue
        if rel.parts[0] in names or rel.parts[0].startswith('host-cost-'):
            files.append(p)
        elif rel.parts[0] in ['sources', 'resources'] and len(rel.parts) > 1:
            job = rel.parts[1].split('.')[0]
            if job not in active and (job.startswith('host-cost-') or job in names):
                files.append(p)
    f = load(BASE/campaign/'freeze.json')
    for m in f['models']:
        for key in ['model', 'construction']:
            if key in m:
                files.append(ROOT/m[key]['path'])
    for key in ['binary', 'image', 'harness', 'baseline_worker', 'evidence_worker']:
        files.append(ROOT/f[key]['path'])
    files += [ROOT/c['binary']['path'] for c in f['cells']]
    files += list((ROOT/'tools').glob('*.py'))
    files += [ROOT/p for p in ['docs/specifications/SPEC-0045-general-lowbit-lp.md',
                              'docs/benchmarks/lp-general-host-cost.md',
                              'docs/benchmarks/lp-general-host-cost-results.json',
                              'docs/benchmarks/lp-general-host-cost-pilot-results.json',
                              'docs/benchmarks/lp-general-host-cost-solve-results.json']]
    files += [BASE/'operational-readmission-v6.json']
    prior = BASE/'portable/scale-delivery-v1/EVIDENCE.json'
    preserved = 0
    for item in load(prior)['files']:
        p = ROOT/item['path']
        if p.is_relative_to(BASE):
            require(p.stat().st_size == item['bytes'] and digest(p) == item['sha256'],
                    'historical scientific bytes changed: ' + str(p))
            preserved += 1
    files.append(prior)
    files = sorted(set(files))
    streams = verify_streams(files)
    manifest, objects = [], {}
    for p in files:
        h, n = digest(p), p.stat().st_size
        require(n <= 512 << 20, 'unchanged per-file ceiling')
        manifest.append(dict(path=str(p.relative_to(ROOT)), sha256=h, bytes=n))
        objects.setdefault(h, p)
    campaigns = ['host-cost-pilot-v1', campaign, 'host-cost-solve-v1']
    for name in campaigns:
        frozen = load(BASE/name/'freeze.json')
        for key in ['binary', 'image', 'harness', 'design', 'baseline_worker', 'evidence_worker']:
            require(frozen[key]['sha256'] in objects, 'missing frozen source: ' + name + '/' + key)
        for model in frozen['models']:
            for key in ['model', 'construction']:
                if key in model:
                    require(ref(ROOT/model[key]['path']) == model[key], 'frozen input changed')
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
        path = out/f'objects-{i:03d}.tar.gz'
        with path.open('xb') as raw, gzip.GzipFile(fileobj=raw, mode='wb', mtime=0, compresslevel=1) as z, tarfile.open(fileobj=z, mode='w|') as tar:
            for h, p in group:
                info = tar.gettarinfo(str(p), arcname='objects/' + h)
                info.uid = info.gid = 0
                info.uname = info.gname = ''
                info.mtime = 0
                with p.open('rb') as source:
                    tar.addfile(info, source)
        require(path.stat().st_size < 512 << 20, 'archive part ceiling')
        parts.append(dict(archive=ref(path), bytes=path.stat().st_size))
    put(out/'EVIDENCE.json', dict(files=manifest, campaigns=campaigns,
                                admission_prefixes=['scale-', 'host-cost-'], prior=[ref(prior)],
                                preserved_scientific_files=preserved))
    put(out/'receipt.json', dict(manifest=ref(out/'EVIDENCE.json'), parts=parts,
        files=len(files), unique_objects=len(objects), prior_scientific_files_verified=preserved,
        compressed_bytes=sum(p['bytes'] for p in parts), raw_stream_validation=streams))
    print(dict(files=len(files), parts=len(parts), preserved=preserved), flush=True)


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('action', choices=['archive', 'replay'])
    p.add_argument('--id', required=True)
    p.add_argument('--campaign', default='host-cost-pilot-v2')
    a = p.parse_args()
    if a.action == 'archive':
        archive(a.id, a.campaign)
    else:
        replay(a.id)
