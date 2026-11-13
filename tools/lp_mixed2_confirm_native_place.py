"""Prioritize acceptance supervision without narrowing nested four-CPU contracts.

Native admission and final CPU verification use this wrapper. Scientific
numerical placement remains the admitted three-worker / fourth-control-CPU helper.
"""
import json
import os
import sys

if __name__=='__main__':
    allowed=json.loads(os.environ['LP_CPU_ALLOWED_CPUS'])
    assert len(allowed)==4 and set(allowed)==os.sched_getaffinity(0)
    for key in ('LP_CPU_COORDINATOR_PID','LP_CPU_GUARDIAN_PID'):
        os.sched_setaffinity(int(os.environ[key]),{allowed[-1]})
    os.nice(10)
    os.execvp(sys.argv[1],sys.argv[1:])
