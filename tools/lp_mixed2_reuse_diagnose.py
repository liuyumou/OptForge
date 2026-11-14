"""Fresh bounded reliability probes, separate from frozen scientific samples."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import time
from lp_mixed2_reuse_common import BASE, OLD, ROOT, IMAGE, load, put, ref, require


def cpu(out):
    out.mkdir(exist_ok=False)
    binary = OLD/'build-v10/executor'
    models = load(OLD/'models/manifest-v2.json')['models']
    family = 'dense-coupled-2048'
    rows = []
    # Process/model/checker preparation exercises the same large host path that
    # surrounds GPU work, while keeping this first diagnosis CPU-only.
    for i in range(8):
        start = time.monotonic_ns()
        p = subprocess.run([str(binary), 'check-service', str(ROOT/models[family]['path'])],
                           input=b'', capture_output=True, timeout=90)
        (out/f'{i}.stdout').write_bytes(p.stdout); (out/f'{i}.stderr').write_bytes(p.stderr)
        rows.append(dict(index=i, code=p.returncode, elapsed_ns=time.monotonic_ns()-start))
        require(p.returncode == 0 and json.loads(p.stdout)['ready'], 'CPU preparation probe')
    put(out/'result.json', dict(status='passed', rows=rows, binary=ref(binary), model=models[family]))


def race(out, scope):
    out.mkdir(exist_ok=False)
    binary = OLD/'build-v10/executor'
    model = ROOT/load(OLD/'models/manifest.json')['models']['irregular-tail-33']['path']
    order = [('build-v7','native'),('build-v10','fp4x2'),('build-v7','fp4x2'),('build-v10','native')]
    put(out/'manifest.json', dict(binary=ref(binary), image=ref(IMAGE), model=ref(model),
                                 scope=scope, order=order, binaries={v:ref(OLD/v/'executor') for v,_ in order}, historical_retry=False))
    rows = []
    for i, (version,lane) in enumerate(order):
        binary=OLD/version/'executor'
        request = dict(op='solve', solve_id=0, lane=lane, tier='certified-1e-9',
                       window_max=32 if lane=='native' else 16)
        req = out/f'{i}.request.json'; put(req, request)
        cmd = ['/usr/local/cuda/bin/compute-sanitizer', '--tool', 'racecheck',
               '--target-processes', scope, '--error-exitcode', '86',
               '--log-file', str(out/f'{i}.sanitizer'), str(binary), 'once',
               str(IMAGE), str(model), str(req)]
        p = subprocess.run(cmd, capture_output=True, timeout=90)
        (out/f'{i}.stdout').write_bytes(p.stdout); (out/f'{i}.stderr').write_bytes(p.stderr)
        row = dict(index=i, version=version, lane=lane, returncode=p.returncode,
                   certified=json.loads(p.stdout)['certified'] if p.returncode==0 else None)
        rows.append(row); put(out/f'{i}.outcome.json', row)
        # All predeclared probes remain visible, including an exit without a
        # certificate; success of another probe is never a replacement.
    put(out/'result.json', dict(status='diagnostic-complete', rows=rows))


if __name__ == '__main__':
    p=argparse.ArgumentParser(); p.add_argument('kind', choices=['cpu','race'])
    p.add_argument('out', type=Path); p.add_argument('--scope', default='application-only')
    a=p.parse_args(); cpu(a.out) if a.kind=='cpu' else race(a.out,a.scope)
