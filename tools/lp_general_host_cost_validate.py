"""Validate host-cost source, resource, transcript and portable delivery bindings."""
import argparse
import subprocess

from lp_general_common import BASE, ROOT, load, put, ref, require, CPU_CAPS, GPU_CAPS, NS
from lp_general_budget import accounting
from lp_general_scale_imports import validate as validate_imports


def validate(identity):
    out = BASE/identity
    out.mkdir(exist_ok=False)
    sources = []
    for p in sorted((ROOT/'research/lp-general-lowbit/src').glob('*.rs')):
        retained = BASE/'sources/scale-cpu-v9'/p.relative_to(ROOT)
        require(p.read_bytes() == retained.read_bytes(), 'CPU-admitted source differs')
        sources.append(ref(p))
    for name in ['crates', 'research/lp-fp4-checker', 'research/lp-mixed2-checker2',
                 'research/lp-general-lowbit/cuda']:
        require(not subprocess.check_output(['git', 'diff', 'HEAD', '--', name], cwd=ROOT),
                'historical/public source changed: ' + name)
    for name in ['AGENTS.md', 'state/active-task.md', 'research/lp-general-lowbit/README.md',
                 'docs/specifications/SPEC-0045-general-lowbit-lp.md']:
        original = subprocess.check_output(['git', 'show', 'HEAD:' + name], cwd=ROOT)
        current = (ROOT/name).read_bytes()
        require(original.split(b'\n', 1)[1] in current, 'historical document text changed: ' + name)
    require(ref(BASE/'scale-image-v9/tensor.cubin')['sha256'] ==
            ref(BASE/'scale-image-v6/tensor.cubin')['sha256'], 'CUDA image differs')
    require(ref(ROOT/'research/lp-general-lowbit/target/release/lp-general-lowbit')['sha256'] ==
            ref(BASE/'scale-image-v9/executor')['sha256'], 'built executable differs')
    proofs, failures = [], []
    for p in sorted((BASE/'resources').glob('*.settlement.json')):
        if not (p.name.startswith('host-cost-') or p.name.startswith(('scale-cpu-v8.', 'scale-cpu-v9.'))):
            continue
        s = load(p)
        require(not s['overrun'], 'resource overrun')
        r = load(ROOT/s['resource']['path'])
        require(r['guardian_cleanup']['empty'] and r['result']['cleanup']['empty'], 'cleanup incomplete')
        proofs.append(ref(p))
        if s['status'] != 'passed':
            failures.append(ref(p))
    results = ROOT/'docs/benchmarks/lp-general-host-cost-results.json'
    data = load(results)
    require(data['responses'] == data['planned'] == 96 and not data['missing'], 'incomplete pilot')
    require(len(data['matched']) == 48 and all(p['supervised'] and
            (p['exact'] or not p['equal_work']) for p in data['matched']),
            'incomplete supervised comparisons or changed equal-work arithmetic')
    solve_results = ROOT/'docs/benchmarks/lp-general-host-cost-solve-results.json'
    full = load(solve_results)
    require(full['planned'] == full['responses'] == 48 and not full['missing'], 'incomplete single solves')
    require(len(full['matched']) == 24 and all(p['supervised'] and
            (p['exact'] or p['deadline_pair']) for p in full['matched']), 'single-solve comparison failed')
    portable = BASE/'portable/host-cost-delivery-v1/replay.json'
    replay = load(portable)
    require(replay['status'] == 'passed' and replay['result']['cells'] == 240 and
            replay['result']['admission_responses'] == 280 and not replay['result']['missing'] and
            not replay['result']['partial_responses'] and replay['result']['raw_only'] == 0,
            'portable replay incomplete')
    cpu, gpu = accounting()
    require(all(cpu[k] <= CPU_CAPS[k]*NS for k in cpu), 'CPU ceiling')
    require(all(gpu[k] <= GPU_CAPS[k]*NS for k in gpu), 'GPU ceiling')
    put(out/'result.json', dict(status='passed', source=sources, settlements=proofs, failures=failures,
        image=ref(BASE/'scale-image-v9/executor'), device=ref(BASE/'scale-image-v9/tensor.cubin'),
        imports=validate_imports('scale-cpu-v9'), results=ref(results), solve_results=ref(solve_results), portable=ref(portable),
        cpu_seconds={k: v/NS for k, v in cpu.items()}, gpu_seconds={k: v/NS for k, v in gpu.items()},
        scope='Strict unchanged arithmetic and certificates; fresh-process development only. Current reporting reservation remains active.'))
    print(dict(status='passed', settlements=len(proofs), failures=len(failures)), flush=True)


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--id', required=True)
    validate(p.parse_args().id)
