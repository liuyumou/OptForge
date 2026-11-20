"""Keep a read-only NVML client alive across an admitted observation handoff."""
import argparse
import os
import time
from pathlib import Path
from lp_billion_common import BASE, load, put, ref, require
from lp_billion_idle import Nvml
from lp_confirmation2_supervisor import identity as process_identity


def main(identity, observation, seconds):
    for value in [identity, observation]:
        require(value and Path(value).name == value and value not in ['.', '..'], 'handoff identity')
    require(5 <= seconds <= 660, 'bounded observation wait')
    reservation = BASE/'resources'/(observation+'.reservation.json')
    spec = load(reservation)
    require(spec['phase']=='reporting' and not spec['gpu'], 'existing CPU observation reservation')
    require('tools/lp_billion_diagnose.py' in spec['command'], 'existing observation command')
    out = BASE/identity
    out.mkdir(exist_ok=False)
    sensor = Nvml()
    status = 'interrupted'
    try:
        put(out/'start.json',dict(source=ref(__file__),observation=ref(reservation),
            process=process_identity(os.getpid()),started_ns=time.monotonic_ns(),
            sample=sensor.sample(),read_only_nvml=True,cuda_context=False,
            device_configuration_changed=False,
            purpose='Keep the monitoring client alive; the original five-minute, immediate preflight and continuous supervision checks remain mandatory.'))
        deadline = time.monotonic()+seconds
        settlement = reservation.with_name(observation+'.settlement.json')
        while not settlement.exists():
            if time.monotonic() >= deadline:
                status = 'observation_wait_expired'
                return 75
            time.sleep(1)
        result = load(settlement)
        require(result['status']=='passed' and result['cleanup_empty'] and not result['overrun'], 'observation supervision')
        if load(BASE/observation/'result.json')['status'] != 'observed_idle':
            status = 'idle_gate_not_met'
            return 75
        # This performs a fresh observation and retains all unchanged GPU gates.
        from lp_billion_prepare_continue import main as resume
        code = resume()
        status = 'continuation_completed' if code == 0 else 'continuation_waiting'
        return code
    finally:
        sensor.close()
        put(out/'result.json',dict(status=status,finished_ns=time.monotonic_ns(),
            read_only_monitor_closed=True,device_configuration_changed=False,
            source=ref(__file__),observation=ref(reservation)))


if __name__ == '__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--id',required=True)
    parser.add_argument('--observation',required=True)
    parser.add_argument('--seconds',type=int,default=360)
    args=parser.parse_args()
    raise SystemExit(main(args.id,args.observation,args.seconds))
