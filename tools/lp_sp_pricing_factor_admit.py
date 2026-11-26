"""Build, CPU proof tests, CPU/GPU differential checks and full sanitizers."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
import time
import numpy as np
from scipy import sparse
from lp_sp_pricing_budget import ROOT, BASE, binding, put
from lp_sp_pricing_gpu_opt_compare import read, verify
from lp_sp_pricing_scale_admit import validate as previous
sys.path.insert(0, str(ROOT/'research/lp-sp-pricing/python'))
from sp_pricing.factor_projection import CpuProjection, GpuProjection, inverse_proposal, projection
from sp_pricing.implicit_certificate import inverse_bound
from lp_sp_pricing_factor_proof import build, verify_arrays

CRATE = ROOT/'research/lp-sp-pricing'


def sources():
    paths = [CRATE/'native/factor_projection.cu', CRATE/'target/release/libsp_factor_projection.so',
             CRATE/'python/sp_pricing/factor_projection.py', CRATE/'python/sp_pricing/implicit_certificate.py',
             ROOT/'tools/lp_sp_pricing_factor_proof.py', Path(__file__).resolve(),
             ROOT/'tests/integration/test_lp_sp_pricing_factor.py']
    return [binding(p) for p in paths]


def fixture(n, seed):
    rng = np.random.default_rng(seed); m = 4*n+3
    a = rng.integers(-7, 8, size=(m, n)).astype(float)/16
    a[:n] += np.eye(n)*2
    x = rng.integers(-8, 9, size=n)/8
    y = rng.integers(1, 8, size=m).astype(float)/(1 << (m-1).bit_length())
    inactive = np.arange(m) % 5 == 0; y[inactive] = 0.
    b = a@x+np.where(inactive, .25, 0.); c = a.T@y
    return sparse.csr_matrix(a), b, c, x, y


def compile_native(identity):
    previous(); out = BASE/identity; out.mkdir(exist_ok=False)
    cmd = ['/usr/local/cuda/bin/nvcc', '-std=c++17', '-O3', '-lineinfo', '-Xcompiler', '-fPIC', '-shared',
           '-gencode', 'arch=compute_120,code=sm_120', '--cudart', 'shared',
           '-Xlinker', '-rpath=/usr/local/cuda/lib64', str(CRATE/'native/factor_projection.cu'),
           '-lcublas', '-lcusolver', '-o', str(CRATE/'target/release/libsp_factor_projection.so')]
    subprocess.run(cmd, check=True)
    put(out/'result.json', dict(status='built', command=cmd, binary=binding(CRATE/'target/release/libsp_factor_projection.so')))


def cpu(identity):
    previous(); out = BASE/identity; out.mkdir(exist_ok=False)
    subprocess.run([sys.executable, '-B', '-m', 'unittest', 'discover', '-s', 'tests/integration',
                    '-p', 'test_lp_sp_pricing_factor.py', '-v'], cwd=ROOT, check=True)
    records = []
    for n in (32, 64, 128):
        a, b, c, xp, yp = fixture(n, 123101+n)
        x, y, detail = projection(a, b, c, seconds=15, gpu=False, max_steps=3000)
        certificate, metadata = build(a, b, c, x, y, gpu=False)
        proof = verify_arrays(a.indptr, a.indices, a.data, b, c, certificate['x'], certificate['y0'],
            certificate['basis'], certificate['inverse']) if certificate else dict(accepted=False)
        row = dict(n=n, proposal=detail, construction=metadata, proof=proof,
                   primal_error=float(np.max(np.abs(x-xp))))
        records.append(row); print(json.dumps(row), flush=True)
        if not proof['accepted']: raise ArithmeticError('CPU factor proposal did not certify')
    put(out/'result.json', dict(status='passed', sources=sources(), records=records))


def quality(output, smoke=False):
    records = []
    for n in ([7, 17] if smoke else [1, 7, 17, 33, 65]):
        a, b, c, xp, yp = fixture(n, 123301+n)
        rho = .01; cpu = CpuProjection(a, b, c, rho); gpu = GpuProjection(a, b, c, rho)
        try:
            for steps in ([3, 7] if smoke else [1, 7, 32]):
                xc, yc = cpu.advance(steps); xg, yg = gpu.advance(steps)
                if not np.allclose(xc, xg, atol=2e-10, rtol=2e-10) or not np.allclose(yc, yg, atol=2e-10, rtol=2e-10):
                    raise ArithmeticError('CPU/GPU projection disagreement')
                records.append(dict(n=n, steps=steps, x_error=float(np.max(np.abs(xc-xg))), y_error=float(np.max(np.abs(yc-yg)))))
        finally:
            cpu.close(); gpu.close()
        matrix = a[:n].toarray().T
        inverse = inverse_proposal(matrix, gpu=True)
        bound = inverse_bound(matrix, inverse)
        if not bound['accepted']: raise ArithmeticError('GPU inverse proposal did not validate')
        records.append(dict(n=n, inverse_proof=bound))
    put(output, dict(status='passed', records=records, sources=sources()))


def gpu(identity, cpu_identity):
    prior = BASE/cpu_identity/'result.json'; d = read(prior)
    if d['status'] != 'passed' or d['sources'] != sources(): raise RuntimeError('CPU source admission')
    if read(BASE/'resources'/f'{cpu_identity}.settlement.json')['status'] != 'passed': raise RuntimeError('CPU supervision')
    out = BASE/identity; out.mkdir(exist_ok=False); quality(out/'quality.json')
    evidence = [binding(prior), binding(out/'quality.json')]
    for name in ('memcheck', 'racecheck', 'initcheck', 'synccheck'):
        with (out/(name+'.log')).open('x') as stream:
            subprocess.run(['/usr/local/cuda/bin/compute-sanitizer', '--tool', name, '--target-processes', 'all',
                '--error-exitcode', '91', sys.executable, '-B', __file__, 'quality', str(out/(name+'.json')), '--smoke'],
                stdout=stream, stderr=subprocess.STDOUT, check=True)
        evidence.extend([binding(out/(name+'.log')), binding(out/(name+'.json'))])
    put(out/'admission.json', dict(status='passed', sources=sources(), evidence=evidence))


def validate():
    previous(); path = BASE/'factor-gpu-admit-v2/admission.json'; d = read(path)
    if d['status'] != 'passed' or d['sources'] != sources(): raise RuntimeError('factor source admission changed')
    for item in d['evidence']: verify(item)
    if read(BASE/'resources/factor-gpu-admit-v2.settlement.json')['status'] != 'passed': raise RuntimeError('factor GPU admission supervision')
    return binding(path)


if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('action', choices=['build', 'cpu', 'gpu', 'quality'])
    p.add_argument('identity'); p.add_argument('--cpu-identity'); p.add_argument('--smoke', action='store_true'); args = p.parse_args()
    if args.action == 'build': compile_native(args.identity)
    elif args.action == 'cpu': cpu(args.identity)
    elif args.action == 'gpu': gpu(args.identity, args.cpu_identity)
    else: quality(Path(args.identity), args.smoke)
