"""Publish settled scientific evidence and independently replay without artifacts.

The frozen evidence reader is unchanged. This delivery-only publisher excludes
in-flight administrative receipts, whose settled bytes are retained at closure.
"""
import argparse
import gzip
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
import tempfile

from lp_checker2_common import BASE, ROOT, PRIOR, load, put, ref, require
from lp_checker2_evidence import DATA, INDEX, digest, trajectory, PartWriter


def publish():
    pending = [p.name.removesuffix('.reservation.json') for p in (BASE/'resources').glob('*.reservation.json')
               if not p.with_name(p.name.replace('.reservation.json', '.settlement.json')).exists()]
    def stable(path):
        relative = path.relative_to(BASE)
        return (path.is_file() and not path.is_symlink() and path.suffix != '.lock'
                and not relative.parts[0].startswith('build-') and path.name != 'executor'
                and relative.parts[0] != 'vector-target' and path.name != 'evidence-check.json'
                and not (relative.parts[0] == 'resources' and any(path.name.startswith(p+'.') for p in pending)))
    paths = [p for p in BASE.rglob('*') if stable(p)]
    models = load(PRIOR/'models/manifest.json')
    paths += [ROOT/p['path'] for items in models['groups'].values() for p in items] + [PRIOR/'models/manifest.json']
    frozen = load(BASE/'freeze.json')
    for item in frozen['sources'] + list(frozen['binaries'].values()) + [frozen['image'], frozen['models']] + frozen['admissions']:
        require(ref(ROOT/item['path']) == item, 'frozen publication binding differs')
    paths += [ROOT/p['path'] for p in frozen['sources']] + sorted((ROOT/'tools').glob('lp_checker2*.py'))
    entries = []; first = {}
    for path in sorted(set(paths)):
        with path.open('rb') as stream:
            sha, size = digest(stream)
        entry = dict(path=str(path.relative_to(ROOT)), sha256=sha, bytes=size)
        if (sha, size) in first:
            entry['link'] = first[sha, size]
        else:
            first[sha, size] = entry['path']
        entries.append(entry)
    controls = {}
    for path in sorted((BASE/'pilot-optimized').glob('*-r[0-9][0-9].json')):
        response = load(path)
        key = '|'.join([response['model_sha256'], response['tier'], response['lane']])
        value = trajectory(response)
        if key in controls:
            require(controls[key] == value, 'inconsistent admitted trajectory')
        controls[key] = value
    manifest = dict(files=entries, controls=controls, protocol=frozen, freeze=ref(BASE/'freeze.json'),
                    analysis=load(BASE/'analysis.json'), publisher=ref(Path(__file__).resolve()),
                    pending_administration=pending,
                    exclusions='Executables and build caches stay local; binary digests and immutable sources are retained. In-flight administrative receipts are archived after settlement at allocation closure.')
    raw = json.dumps(manifest, separators=(',', ':')).encode()
    with PartWriter('checker2-evidence-v1') as output, gzip.GzipFile(fileobj=output, mode='wb', compresslevel=6, mtime=0) as zipped:
        with tarfile.open(fileobj=zipped, mode='w|', format=tarfile.PAX_FORMAT) as archive:
            info = tarfile.TarInfo('manifest.json'); info.size = len(raw)
            archive.addfile(info, io.BytesIO(raw))
            for entry in entries:
                info = tarfile.TarInfo(entry['path']); info.mode = 0o644
                if 'link' in entry:
                    info.type = tarfile.LNKTYPE; info.linkname = entry['link']; archive.addfile(info)
                else:
                    info.size = entry['bytes']
                    with (ROOT/entry['path']).open('rb') as stream:
                        archive.addfile(info, stream)
    put(INDEX, dict(format='tar+gzip with exact-content hardlinks', files=len(entries), unique_files=len(first),
                    **output.index(), manifest_sha256=hashlib.sha256(raw).hexdigest(), pending_administration=pending))
    put(BASE/'published-files.json', dict(files=entries, pending_administration=pending, archive=ref(INDEX)))
    print(dict(files=len(entries), bytes=output.total, pending_administration=pending), flush=True)


def portable():
    index = load(INDEX)
    with tempfile.TemporaryDirectory(prefix='checker2-portable-', dir='/tmp') as directory:
        root = Path(directory)
        (root/'tools').mkdir()
        for path in (ROOT/'tools').glob('*.py'):
            shutil.copy2(path, root/'tools'/path.name)
        for path in [INDEX] + [ROOT/p['path'] for p in index['parts']]:
            target = root/path.relative_to(ROOT); target.parent.mkdir(parents=True, exist_ok=True)
            os.link(path, target)
        require(not (root/'artifacts').exists(), 'portable original artifacts exist')
        command = [sys.executable, '-c', 'import json,sys;sys.path.insert(0,"tools");from lp_checker2_evidence import verify;print(json.dumps(verify(False)))']
        result = subprocess.run(command, cwd=root, check=True, capture_output=True, text=True,
                                env=os.environ | {'CUDA_VISIBLE_DEVICES': '', 'PYTHONDONTWRITEBYTECODE': '1'})
        value = json.loads(result.stdout)
        require(not (root/'artifacts').exists() and value['status'] == 'passed', 'portable replay differs')
    put(BASE/'portable.json', dict(status='passed', original_artifacts_absent=True, result=value,
                                 verifier=ref(ROOT/'tools/lp_checker2_evidence.py'), publisher=ref(Path(__file__).resolve()), archive=ref(INDEX)))
    print(value, flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('action', choices=['publish', 'portable'])
    args = parser.parse_args()
    publish() if args.action == 'publish' else portable()
