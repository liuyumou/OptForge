"""EOF-driven complete delivery with durable partial transcripts on failure."""
import os
from pathlib import Path
import subprocess
import time


def durable(path,payload):
    path=Path(path)
    with path.open('xb') as stream:
        stream.write(payload);stream.flush();os.fsync(stream.fileno())


def deliver(command,dest,log,timeout):
    started=time.monotonic_ns()
    try:
        result=subprocess.run(command,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=timeout)
    except subprocess.TimeoutExpired as error:
        # An incomplete frame is evidence of the failed attempt, never a result.
        durable(str(dest)+'.partial',error.stdout or b'')
        durable(log,error.stderr or b'')
        raise
    durable(dest,result.stdout);durable(log,result.stderr)
    elapsed=time.monotonic_ns()-started
    result.check_returncode()
    return elapsed
