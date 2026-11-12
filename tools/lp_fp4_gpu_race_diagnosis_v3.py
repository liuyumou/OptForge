"""CPU-only audit of the retained v2 race failure and one-barrier v3 candidate."""
import hashlib
import re
from lp_fp4_gpu_common import ROOT, BASE, checked, load, put, ref, require
from lp_fp4_gpu_budget import accounting


def functions(sass):
    chunks = re.split(r'Function : (\w+)', sass)
    return {chunks[i]: chunks[i+1].strip() for i in range(1, len(chunks), 2)}


def main():
    old = ROOT / 'research/lp-fp4-gpu-pilot/cuda/pilot_v2.cu'
    new = ROOT / 'research/lp-fp4-gpu-pilot/cuda/pilot_v3.cu'
    header = '// CPU-prepared v3 shared-state synchronization correction; v2 stays frozen.\n'
    barrier = '    __syncwarp(); // Finish all reads of aliased shared state before re-encoding.\n'
    require(new.read_text().count(barrier) == 1, 'one barrier required')
    require(new.read_text().removeprefix(header).replace(barrier, '') == old.read_text(), 'unrelated source delta')
    prior = functions((BASE / 'build-v2/pilot.sass').read_text())
    candidate = functions((BASE / 'build-v3/pilot.sass').read_text())
    require(prior['pilot_64_1'] == candidate['pilot_64_1'], 'native SASS changed')
    require(len(prior) == len(candidate) == 6, 'kernel coverage')
    cases = []
    for p in sorted((ROOT / 'artifacts/gpup-fp4-gpu-pilot-v2/racecheck').glob('*.attempt.json')):
        row = load(p)
        for key in ('input', 'output', 'stdout', 'stderr'):
            checked(row[key])
        log = checked(row['stdout']).read_text() + checked(row['stderr']).read_text()
        summary = re.search(r'RACECHECK SUMMARY: (\d+) hazards displayed \((\d+) errors, (\d+) warnings\)', log)
        require(summary is not None, 'racecheck summary missing')
        cases.append(dict(row, summary=list(map(int, summary.groups()))))
    require(len(cases) == 5, 'attempt coverage')
    failed = [r for r in cases if r['returncode'] != 0]
    require(len(failed) == 1 and failed[0]['id'] == '8-4-split' and failed[0]['summary'] == [100, 0, 128], 'unexpected refusal')
    cpu, gpu = accounting()
    put(ROOT / 'docs/benchmarks/data/fp4-gpu-pilot-race-diagnosis-v2.json', dict(
        status='v2_safety_refused', complete_pilot=False, executed_profiles=0, unexecuted_profiles=216,
        primitives=dict(new_fp4_passed=30, retained_controls_passed=30), device_cases_passed=90,
        memcheck_cases_passed=24, racecheck_cases=cases, racecheck_cases_unexecuted=19,
        initcheck_cases_unexecuted=24, synccheck_cases_unexecuted=24,
        failure_charge_cpu_ns=960000000000, failure_charge_gpu_ns=240000000000,
        candidate=ref(new), previous=ref(old), candidate_build=ref(BASE / 'build-v3/receipt.json'),
        candidate_device_validated=False, candidate_native_sass_unchanged=True,
        source_delta='One full-warp barrier at encode entry, after all calling-lane shared-state reads and before any overwrite.',
        semantics='The barrier orders aliasing shared-state accesses. Vote/shuffle synchronization alone does not supply shared-memory ordering.',
        total_cpu_ns=sum(cpu.values()), total_gpu_ns=sum(gpu.values()),
        documentation='https://docs.nvidia.com/compute-sanitizer/ComputeSanitizer/index.html'))
    print('Retained four native racecheck passes and one 128-warning refusal; exact one-barrier delta and unchanged native SASS verified. No GPU execution.')


if __name__ == '__main__':
    main()
