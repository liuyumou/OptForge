"""Fresh availability admission after the user's explicit three-cell resumption."""
import argparse
import time
from lp_billion_common import BASE, load, put, ref, resolve, require
from lp_billion_prepare_continue import completed
from lp_billion_readmission import CPU, GPU
from lp_billion_availability import stable
import lp_billion_copt_fair_headroom as continuation

PLAN = BASE / 'copt-fair-headroom-resume-v1/plan.json'


def identity(value):
    prefix = 'copt-fair-headroom-idle-v'
    require(value.startswith(prefix) and value[len(prefix):].isdigit() and int(value[len(prefix):]) >= 2,
            'fresh post-pause availability identity')
    return value


def observation(value):
    continuation.IDLE = identity(value)
    continuation.observation()


def resume(value):
    value = identity(value)
    require(completed(value), 'settled fresh availability observation')
    observation_result = BASE / value / 'result.json'; observed = load(observation_result)
    require(observed['status'] == 'capacity_and_idle_passed', 'fresh capacity and sustained idle admission')
    samples = [load(resolve(item)) for item in observed['gpu_samples']]
    require(stable(samples, time.monotonic_ns()) and continuation.available() >= 124 << 30,
            'availability remains current immediately before resumption')
    frozen = load(continuation.MANIFEST); resolve(frozen['resumption_source'])
    require(not PLAN.exists(), 'never repeat this resumption driver')
    for cell in frozen['remaining_three']:
        require(not (BASE / 'resources' / (cell + '.reservation.json')).exists(), 'all three LP cells remain untouched')
    prior = load(BASE / 'gpu-control-settled-checkpoint-v1.json')
    for item in prior['numerical_bindings']: resolve(item)
    require(stable(samples, time.monotonic_ns()), 'source validation must not expire the idle proof')
    put(PLAN, dict(status='explicit_user_resumption_admitted', source=ref(__file__),
        user_request='Check whether the Pro6000 is idle and enough RAM is available now. If so, resume the three remaining LP experiments under the existing resource limits, preserving strict 1e-9 certificate checks.',
        previous_pause=ref(BASE / 'copt-fair-user-pause-v2.json'), manifest=ref(continuation.MANIFEST),
        observation=ref(observation_result), idle_proof=ref(BASE / 'availability' / (value + '.json')),
        cpu_admission=ref(BASE / 'resources' / (CPU + '.settlement.json')),
        gpu_admission=ref(BASE / 'resources' / (GPU + '.settlement.json')),
        host_available_bytes=continuation.available(), remaining=frozen['remaining_three'],
        reservation=continuation.plan(), unchanged_numerical_bindings=len(prior['numerical_bindings'])))
    continuation.IDLE = value
    continuation.execute()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('action', choices=['observation', 'resume'])
    parser.add_argument('--id', required=True); args = parser.parse_args()
    globals()[args.action](args.id)
