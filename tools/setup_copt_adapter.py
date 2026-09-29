"""Provision an isolated SPEC-0019 environment, never modifying historic COPT data."""
import argparse
import importlib.metadata
from pathlib import Path
import shutil
import subprocess
import sys
from lp_protocol import ROOT, file_hash, read_json, write_json

DEST = ROOT / 'artifacts/gpup-copt-adapter-env'


def identity(directory=DEST):
    site = directory / 'venv/lib/python3.11/site-packages'
    result = dict(python_version=sys.version.split()[0], python_sha256=file_hash(Path(sys.executable).resolve()), files={})
    for name, version in [('numpy', '2.3.4'), ('scipy', '1.16.3')]:
        found = importlib.metadata.version(name)
        if found != version: raise ValueError('dependency version differs: ' + name)
        result[name] = found
        root = site / name
        for p in sorted(root.rglob('*')):
            if p.is_file() and '__pycache__' not in p.parts and p.suffix != '.pyc':
                result['files'][str(p.relative_to(site))] = file_hash(p)
        # Include native dependencies shipped alongside the package and metadata.
        for root in [site / (name + '.libs'), site / (name + '-' + version + '.dist-info')]:
            for p in sorted(root.rglob('*')):
                if p.is_file(): result['files'][str(p.relative_to(site))] = file_hash(p)
    for p in sorted((site / 'coptpy').iterdir()):
        if p.is_file(): result['files'][str(p.relative_to(site))] = file_hash(p)
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('--identity', action='store_true'); a = p.parse_args()
    if sys.version_info[:2] != (3, 11): raise ValueError('Python 3.11 required')
    if a.identity:
        current = identity()
        path = DEST / 'identity.json'
        if path.exists() and read_json(path) != current: raise ValueError('optional environment identity changed')
        if not path.exists(): write_json(path, current)
        print('optional environment identity verified'); return
    if (DEST / 'identity.json').exists():
        subprocess.run([str(DEST / 'venv/bin/python'), '-B', __file__, '--identity'], check=True); return
    DEST.mkdir(parents=True, exist_ok=True)
    subprocess.run([sys.executable, '-m', 'venv', '--system-site-packages', str(DEST / 'venv')], check=True)
    python = DEST / 'venv/bin/python'; site = DEST / 'venv/lib/python3.11/site-packages'
    subprocess.run([str(python), '-m', 'pip', 'download', '--only-binary=:all:', '--no-deps', '--dest', str(DEST / 'wheels'), 'numpy==2.3.4', 'scipy==1.16.3'], check=True)
    wheels = sorted((DEST / 'wheels').glob('*.whl'))
    write_json(DEST / 'wheels.json', {p.name: file_hash(p) for p in wheels})
    subprocess.run([str(python), '-m', 'pip', 'install', '--no-deps', '--ignore-installed', *map(str, wheels)], check=True)
    original = ROOT / 'artifacts/gpup5-copt/venv/lib/python3.11/site-packages/coptpy'
    shutil.copytree(original, site / 'coptpy', ignore=shutil.ignore_patterns('__pycache__'), dirs_exist_ok=True)
    expected = read_json(ROOT / 'benchmarks/configs/lp-precision-v4.json')
    for filename, field in [('libcopt_python.so', 'copt_library_sha256'), ('coptcore.so', 'copt_binding_sha256')]:
        if file_hash(site / 'coptpy' / filename) != expected[field]: raise ValueError('pinned COPT bytes differ')
    subprocess.run([str(python), '-B', __file__, '--identity'], check=True)


if __name__ == '__main__': main()
