"""Source-bound acceptance for FP4x2 overhead candidates; never run historical drivers."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from lp_billion_common import BASE, ROOT, load, put, ref, resolve, require

SCOPE = BASE / 'fp4x2-overhead-v1'
MANIFEST = 'research/lp-billion-lowbit/Cargo.toml'
TOOLCHAIN = '/root/.rustup/toolchains/1.93.1-x86_64-unknown-linux-gnu/bin'


def preservation():
    plan = load(SCOPE / 'plan.json')
    for row in plan['protected_sources']:
        require(hashlib.sha256((ROOT / row['path']).read_bytes()).hexdigest() == row['sha256'],
                'PR30/protected source changed: ' + row['path'])
    for row in plan['baseline_sources']:
        require(hashlib.sha256((SCOPE / 'baseline' / row['path']).read_bytes()).hexdigest() == row['sha256'],
                'retained original changed: ' + row['path'])
    return dict(protected_sources=len(plan['protected_sources']), baseline_sources=len(plan['baseline_sources']))


def commands(identity, rows):
    # This entry point must itself be the child of a fresh shared-budget job.
    reservation = BASE / 'resources' / (identity + '.reservation.json')
    require(reservation.exists(), 'fresh supervised reservation required')
    out = BASE / identity
    out.mkdir(exist_ok=False)
    env = dict(os.environ, PATH=TOOLCHAIN + ':' + os.environ['PATH'],
               CARGO_HOME='/tmp/ai-optimizer-cargo', CARGO_BUILD_JOBS='4', OPENBLAS_NUM_THREADS='1', OMP_NUM_THREADS='1')
    results = []
    for name, command in rows:
        p = subprocess.run(command, cwd=ROOT, env=env, text=True, capture_output=True)
        for channel in ['stdout', 'stderr']:
            (out / (name + '.' + channel)).write_text(getattr(p, channel))
        results.append(dict(name=name, command=command, returncode=p.returncode,
                            stdout=ref(out / (name + '.stdout')), stderr=ref(out / (name + '.stderr'))))
        print(dict(command=name, returncode=p.returncode), flush=True)
        if p.returncode:
            print(p.stdout[-5000:] + p.stderr[-5000:], flush=True)
        require(p.returncode == 0, name + ' failed')
    return out, results


def check(identity):
    out, rows = commands(identity, [
        ('format', ['cargo', 'fmt', '--manifest-path', MANIFEST, '--check']),
        ('check', ['cargo', 'check', '--manifest-path', MANIFEST, '--all-targets', '--offline']),
    ])
    put(out / 'result.json', dict(status='passed', commands=rows, preservation=preservation()))


def quality(identity):
    out, rows = commands(identity, [
        ('format', ['cargo', 'fmt', '--manifest-path', MANIFEST, '--check']),
        ('tests', ['cargo', 'test', '--manifest-path', MANIFEST, '--release', '--offline']),
        ('clippy', ['cargo', 'clippy', '--manifest-path', MANIFEST, '--all-targets', '--offline', '--', '-D', 'warnings']),
        ('release', ['cargo', 'build', '--manifest-path', MANIFEST, '--release', '--bins', '--offline']),
    ])
    counts = re.findall(r'test result: ok\. (\d+) passed; (\d+) failed; (\d+) ignored;', (out/'tests.stdout').read_text())
    require(counts and all(int(f) == int(i) == 0 for _, f, i in counts), 'all tests completed')
    for item in load(BASE/'sources'/identity/'manifest.json')['sources']:
        if item['original']['path'].startswith('research/lp-billion-lowbit/'):
            resolve(item['original']); resolve(item['retained'])
    put(out / 'result.json', dict(status='passed', commands=rows, rust_tests=sum(int(n) for n,_,_ in counts),
        preservation=preservation(), executor=ref(BASE/'target/release/billion')))


if __name__ == '__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('action', choices=['check','quality']);p.add_argument('--id',required=True)
    args=p.parse_args();globals()[args.action](args.id)
