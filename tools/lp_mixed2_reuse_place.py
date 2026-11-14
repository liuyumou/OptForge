"""Separate this job's numerical and control placement within four admitted CPUs."""
import json
import os
import sys

if __name__ == '__main__':
    allowed = json.loads(os.environ['LP_CPU_ALLOWED_CPUS'])
    assert len(allowed) == 4 and set(allowed) == os.sched_getaffinity(0)
    for key in ('LP_CPU_COORDINATOR_PID', 'LP_CPU_GUARDIAN_PID'):
        os.sched_setaffinity(int(os.environ[key]), {allowed[-1]})
    os.sched_setaffinity(0, set(allowed[:3]))
    os.execvp(sys.argv[1], sys.argv[1:])
