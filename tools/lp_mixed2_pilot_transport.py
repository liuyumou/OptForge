"""Bounded fresh-session delivery; complete time ends after durable response."""
import json
import os
from pathlib import Path
import select
import subprocess
import time
from lp_delivery2_transport import durable
from lp_mixed2_pilot_common import BINARY, require
from lp_mixed2_pilot_cpu import environment

class Service:
    def __init__(self, image, model, log, equilibrate=True, variant=None, profile=None):
        self.log_path = Path(log)
        self.log = self.log_path.open('xb')
        self.buffer = bytearray()
        self.solve_id = self.generation = 0
        variant = variant or os.environ.get('GPUP_MIXED2_PILOT_VARIANT','control')
        profile = False if profile is None else profile
        self.profile = profile
        self.last_delivery = None
        try:
            prefix=[]
            if os.environ.get('AI_OPTIMIZER_SANITIZER'):
                prefix=['/usr/local/cuda/bin/compute-sanitizer','--tool',os.environ['AI_OPTIMIZER_SANITIZER'],'--error-exitcode','86','--log-file',str(log)+'.sanitizer']
            self.proc = subprocess.Popen(prefix+[str(BINARY),'serve',str(image),str(model)]+([] if equilibrate else ['unscaled']),
                stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=self.log,env=environment(variant,profile),bufsize=0)
            self.ready = self.read()
            require(self.ready['ready'] and self.ready['delivery_variant'] == 'candidate', 'readiness/configuration binding')
        except BaseException:
            if hasattr(self,'proc'):
                self.proc.kill(); self.proc.wait()
            self.log.close()
            raise

    def line(self, timeout=35):
        deadline=time.monotonic()+timeout
        while b'\n' not in self.buffer:
            remaining=deadline-time.monotonic()
            if remaining <= 0 or not select.select([self.proc.stdout],[],[],max(0,remaining))[0]:
                durable(str(self.log_path)+'.stdout.partial',bytes(self.buffer))
                raise TimeoutError('service response deadline')
            data=os.read(self.proc.stdout.fileno(),min(65536,(8<<20)+1-len(self.buffer)))
            if not data:
                if self.buffer: durable(str(self.log_path)+'.stdout.partial',bytes(self.buffer))
                raise RuntimeError(f'GPU service ended: {self.proc.poll()}')
            self.buffer.extend(data)
            if len(self.buffer) > 8<<20:
                durable(str(self.log_path)+'.stdout.partial',bytes(self.buffer))
                raise RuntimeError('response frame limit')
        end=self.buffer.index(b'\n')+1
        value=bytes(self.buffer[:end]); del self.buffer[:end]
        return value

    def read(self):
        return json.loads(self.line())

    def write(self, command):
        payload=(json.dumps(command,separators=(',',':'),allow_nan=False)+'\n').encode()
        # FileIO.write may short-write large frames; write until all bytes arrive.
        view=memoryview(payload)
        while view:
            n=self.proc.stdin.write(view)
            if not n: raise BrokenPipeError('command write stopped')
            view=view[n:]
        self.proc.stdin.flush()

    def call(self, op, **fields):
        self.write(dict(op=op,solve_id=self.solve_id,generation=self.generation,**fields))
        result=self.read()
        if op=='solve': self.solve_id+=1; self.generation=0
        elif op=='debug_finish': self.solve_id=result['solve_id']; self.generation=0
        else: self.generation=result.get('generation',self.generation)
        return result

    def solve_to_file(self, path, **fields):
        started=time.monotonic_ns()
        self.write(dict(op='solve',solve_id=self.solve_id,generation=0,**fields))
        sent=time.monotonic_ns() if self.profile else None
        line=self.line()
        received=time.monotonic_ns() if self.profile else None
        durable(path,line)
        elapsed=time.monotonic_ns()-started
        self.last_delivery=dict(send_ns=sent-started,receive_end_ns=received-started,durable_end_ns=elapsed) if self.profile else None
        result=json.loads(line); self.solve_id+=1; self.generation=0
        return result,elapsed

    def close(self, expected=0):
        if self.log.closed: return
        if not self.proc.stdin.closed: self.proc.stdin.close()
        try:
            try: code=self.proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self.proc.kill(); self.proc.wait(); raise
            require(code==expected,f'service exit {code}')
        finally:
            self.log.flush(); os.fsync(self.log.fileno()); self.log.close()
            self.proc.stdout.close()


def deliver(command,dest,log,timeout,profile=False):
    started=time.monotonic_ns()
    try:
        result=subprocess.run(command,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=timeout)
    except subprocess.TimeoutExpired as error:
        durable(str(dest)+'.partial',error.stdout or b'');durable(log,error.stderr or b'');raise
    reaped=time.monotonic_ns() if profile else None
    durable(dest,result.stdout);durable(log,result.stderr)
    elapsed=time.monotonic_ns()-started
    result.check_returncode()
    spans=dict(process_exit_ns=reaped-started,durable_end_ns=elapsed) if profile else None
    return elapsed,spans
