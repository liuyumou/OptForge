"""Validate preparation/control sources, complete results and retained charges."""
import argparse
import re
import subprocess

from lp_general_common import BASE, ROOT, CPU_CAPS, GPU_CAPS, NS, load, put, ref, require
from lp_general_budget import accounting
from lp_general_scale_imports import validate as imports


def validate(identity):
    out = BASE/identity
    out.mkdir(exist_ok=False)
    sources = []
    paths = list((ROOT/'research/lp-general-lowbit/src').rglob('*.rs'))
    paths += list((ROOT/'research/lp-general-lowbit/tests').glob('*.rs'))
    paths += [ROOT/'research/lp-general-lowbit/Cargo.toml', ROOT/'research/lp-general-lowbit/Cargo.lock']
    for p in sorted(paths):
        retained = BASE/'sources/scale-cpu-v14'/p.relative_to(ROOT)
        require(p.read_bytes() == retained.read_bytes(), 'admitted Rust source differs')
        sources.append(ref(p))
    for name in ['crates', 'research/lp-fp4-checker', 'research/lp-mixed2-checker2',
                 'research/lp-general-lowbit/cuda']:
        require(not subprocess.check_output(['git', 'diff', 'HEAD', '--', name], cwd=ROOT),
                'public or historical source changed: '+name)
    problem = ROOT/'research/lp-general-lowbit/src/host-lp/problem.rs'
    current = problem.read_bytes()
    original = (ROOT/'crates/optimizer-lp/src/problem.rs').read_bytes()
    start = current.index(b'\n    /// Opt-in research construction')
    end = current.index(b'\n    /// This program with its variable bounds', start)
    require(current[:start] + current[end:] == original, 'original public code changed')
    require(current == (BASE/'sources/scale-cpu-v14'/problem.relative_to(ROOT)).read_bytes(), 'admitted constructor differs')
    wrapper = (ROOT/'research/lp-general-lowbit/src/host-lp/lib.rs').read_bytes()
    require(re.sub(rb'^#\[path = "[^\"]+"\]\n', b'', wrapper, flags=re.M) ==
            (ROOT/'crates/optimizer-lp/src/lib.rs').read_bytes(), 'host module wrapper differs')
    for name in ['AGENTS.md', 'state/active-task.md', 'research/lp-general-lowbit/README.md',
                 'docs/specifications/SPEC-0045-general-lowbit-lp.md']:
        original = subprocess.check_output(['git', 'show', 'HEAD:'+name], cwd=ROOT)
        require(original.split(b'\n', 1)[1] in (ROOT/name).read_bytes(), 'historical text changed')
    require(ref(BASE/'scale-image-v14/tensor.cubin')['sha256'] ==
            ref(BASE/'scale-image-v9/tensor.cubin')['sha256'], 'CUDA changed')
    require(ref(ROOT/'research/lp-general-lowbit/target/release/lp-general-lowbit')['sha256'] ==
            ref(BASE/'scale-image-v14/executor')['sha256'], 'current binary differs')
    proofs, failures = [], []
    for p in sorted((BASE/'resources').glob('*.settlement.json')):
        if not (p.name.startswith('prep-control-') or
                p.name.startswith(('scale-cpu-v10.', 'scale-cpu-v11.', 'scale-cpu-v12.', 'scale-cpu-v13.', 'scale-cpu-v14.'))):
            continue
        s = load(p)
        require(not s['overrun'], 'resource overrun')
        r = load(ROOT/s['resource']['path'])
        require(r['guardian_cleanup']['empty'] and r['result']['cleanup']['empty'], 'incomplete cleanup')
        proofs.append(ref(p))
        if s['status'] != 'passed':
            failures.append(dict(receipt=ref(p), cpu_ns=s['cpu_ns'], gpu_ns=s['gpu_ns']))
    require(len(failures) == 4 and sum(f['cpu_ns'] for f in failures) == 8200*NS
            and not any(f['gpu_ns'] for f in failures), 'retained failed charges differ')
    first = ROOT/'docs/benchmarks/lp-general-prep-control-results.json'
    d = load(first)
    require(d['planned'] == d['responses'] == 48 and not d['missing'], 'implementation cohort incomplete')
    require(len(d['matched']) == 24 and all(p['supervised'] and
            (p['exact'] or p['deadline_pair']) for p in d['matched']), 'exact transcript comparison')
    second = ROOT/'docs/benchmarks/lp-general-prep-control-control-results.json'
    d = load(second)
    require(d['planned'] == d['responses'] == 24 and not d['missing'], 'control cohort incomplete')
    require(len(d['control_comparisons']) == 24 and all(p['supervised'] for p in d['control_comparisons']),
            'control comparison supervision')
    require(load(BASE/'prep-control-cadence-admission-v1/result.json')['exact_pairs'] == 11,
            '500-update continuation admission')
    large = ROOT/'docs/benchmarks/lp-general-prep-control-large-results.json'
    d = load(large)
    require(d['planned'] == d['responses'] == 18 and not d['missing'], 'large cohort incomplete')
    require(len(d['matched']) == 6 and all(p['supervised'] and
            (p['exact'] or p['deadline_pair']) for p in d['matched']), 'large exact source comparison')
    large_control = ROOT/'docs/benchmarks/lp-general-prep-control-large-control-results.json'
    d = load(large_control)
    require(len(d['control_comparisons']) == 6 and all(p['supervised'] for p in d['control_comparisons']),
            'large control comparison supervision')
    final = ROOT/'docs/benchmarks/lp-general-prep-control-indexed-results.json'
    d = load(final)
    require(d['planned'] == d['responses'] == 48 and not d['missing'], 'final cohort incomplete')
    require(len(d['matched']) == 24 and all(p['supervised'] and
            (p['exact'] or p['deadline_pair']) for p in d['matched']), 'final exact source comparison')
    final_large = ROOT/'docs/benchmarks/lp-general-prep-control-indexed-large-results.json'
    has_final_large = (BASE/'prep-control-indexed-large-v1/freeze.json').exists()
    if has_final_large:
        d = load(final_large)
        require(d['planned'] == d['responses'] == 12 and not d['missing'], 'final large cohort incomplete')
        require(len(d['matched']) == 6 and all(p['supervised'] and p['exact'] and
                p['jointly_certified'] for p in d['matched']), 'final large exact comparison')
    portable = BASE/'portable/prep-control-delivery-v2/replay.json'
    replay = load(portable)
    require(replay['status'] == 'passed' and replay['result']['cells'] == 138 + 12*has_final_large and
            replay['result']['admission_responses'] == 302 and not replay['result']['missing'] and
            not replay['result']['partial_responses'] and replay['result']['raw_only'] == 0,
            'portable replay incomplete')
    cpu, gpu = accounting()
    require(all(cpu[k] <= CPU_CAPS[k]*NS for k in cpu), 'CPU ceiling')
    require(all(gpu[k] <= GPU_CAPS[k]*NS for k in gpu), 'GPU ceiling')
    put(out/'result.json', dict(status='passed', sources=sources, settlements=proofs, failures=failures,
        imports=imports('scale-cpu-v14'), implementation_results=ref(first), control_results=ref(second),
        large_results=ref(large), large_control_results=ref(large_control),
        final_results=ref(final), portable=ref(portable), image=ref(BASE/'scale-image-v14/executor'),
        final_large_results=ref(final_large) if has_final_large else None,
        native_gate=ref(BASE/'resources/prep-control-native-v2.settlement.json'),
        cpu_seconds={k:v/NS for k,v in cpu.items()}, gpu_seconds={k:v/NS for k,v in gpu.items()},
        scope='Development only; configuration comparisons may change work. Current reporting reservation is active.'))
    print(dict(status='passed', settlements=len(proofs), retained_failures=len(failures)), flush=True)


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--id', required=True)
    validate(p.parse_args().id)
