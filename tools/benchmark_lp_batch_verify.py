"""CPU-only paired timing of research verify-batch on retained evidence.

No solves, device discovery, ledger admission or archive writes. The two supplied
executables run only their verify-batch action; every invocation must accept the
same evidence. Results describe verification time, never GPU solve throughput.
"""
import argparse
import hashlib
import json
from pathlib import Path
import statistics
import subprocess
import time

ROOT = Path(__file__).resolve().parents[1]
CASES = (
    ('batch-repeat', 'gpup-development-irregular-2048'),
    ('batch-repeat-short', 'gpup-extension-irregular-32768'),
    ('batch-variant-short', 'gpup-extension-irregular-32768'),
)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline', type=Path, required=True)
    parser.add_argument('--candidate', type=Path, required=True)
    parser.add_argument('--archive', type=Path, default=ROOT / 'artifacts/gpup-throughput-v1')
    parser.add_argument('--repetitions', type=int, default=3)
    args = parser.parse_args()
    if not 1 <= args.repetitions <= 5:
        parser.error('repetitions must be in 1..5')
    binaries = {'baseline': args.baseline.resolve(), 'candidate': args.candidate.resolve()}
    archive = args.archive.resolve()
    frozen = json.loads((archive / 'protocol.json').read_text())
    results = []
    for kind, instance in CASES:
        job = next(j for j in frozen['jobs'] if j['kind'] == kind and j['instance']['id'] == instance
                   and j['config']['id'] == 'research-fused-fp64' and j['repeat'] == 0 and j['size'] == 8)
        key = f'{kind}-{instance}-0-research-fused-fp64-1e-9-n8'
        model = ROOT / job['instance']['model']['path']
        request = archive / (key + '.research.json')
        evidence = archive / (key + '.batch')
        paths = [model, request, *sorted(evidence.glob('*.json'))]
        hashes = {str(p.relative_to(ROOT)): digest(p) for p in paths}
        samples = {name: [] for name in binaries}
        # Alternate which executable goes first; retain every timing and exit.
        for repeat in range(args.repetitions):
            order = list(binaries) if repeat % 2 == 0 else list(reversed(binaries))
            for name in order:
                started = time.perf_counter_ns()
                run = subprocess.run([str(binaries[name]), 'verify-batch', str(model), str(request), str(evidence)],
                                     capture_output=True, text=True, timeout=180)
                elapsed = time.perf_counter_ns() - started
                if run.returncode or run.stdout.strip() != 'verified':
                    raise RuntimeError(f'{name}: {key}: {run.returncode}: {run.stderr}')
                samples[name].append(elapsed)
        if hashes != {str(p.relative_to(ROOT)): digest(p) for p in paths}:
            raise RuntimeError('retained evidence changed during verification')
        medians = {name: statistics.median(values) for name, values in samples.items()}
        results.append(dict(case=key, samples_ns=samples, median_ns=medians,
                            ratio=medians['baseline'] / medians['candidate'], sha256=hashes))
    print(json.dumps(dict(endpoint='CPU-only batch evidence verification; not solve throughput',
                          binaries={name: dict(path=str(path), sha256=digest(path)) for name, path in binaries.items()},
                          repetitions=args.repetitions, results=results), indent=2))


if __name__ == '__main__':
    main()
