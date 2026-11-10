"""Bound logs independently of model/certificate files (ADR-0050)."""
import os
from pathlib import Path
import selectors
import signal
import subprocess
import time


def launch(command, environment, prefix, output_limit=16 << 20):
    prefix=Path(prefix)
    prefix.parent.mkdir(parents=True,exist_ok=True)
    files={name:Path(str(prefix)+'.'+name).open('xb') for name in ('stdout','stderr')}
    counts=dict.fromkeys(files,0)
    exceeded=None
    started=time.monotonic_ns()
    child=None
    try:
        child=subprocess.Popen(command,env=environment,stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE,start_new_session=True)
        with selectors.DefaultSelector() as selector:
            for name in files:
                selector.register(getattr(child,name),selectors.EVENT_READ,name)
            while selector.get_map():
                for key,_ in selector.select(.1):
                    data=os.read(key.fd,65536)
                    if not data:
                        selector.unregister(key.fileobj)
                        key.fileobj.close()
                        continue
                    name=key.data
                    remaining=max(0,output_limit-counts[name])
                    files[name].write(data[:remaining])
                    counts[name]+=len(data)
                    if counts[name]>output_limit and exceeded is None:
                        exceeded=name
                        try: os.killpg(child.pid,signal.SIGKILL)
                        except ProcessLookupError: pass
        code=child.wait()
        return dict(elapsed_ns=time.monotonic_ns()-started,
                    returncode=86 if exceeded else code, native_returncode=code,
                    output_limit_bytes=output_limit, observed_stream_bytes=counts,
                    exceeded_stream=exceeded,
                    definition='immediately before fresh worker launch through exit and bounded stream drain after durable endpoint/checker output')
    finally:
        if child is not None and child.poll() is None:
            try: os.killpg(child.pid,signal.SIGKILL)
            except ProcessLookupError: pass
            child.wait()
        for stream in files.values():
            stream.flush()
            os.fsync(stream.fileno())
            stream.close()
