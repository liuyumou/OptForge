"""Compact control/evidence transport. Numerical solve orchestration lives in Rust."""
import json
import os
from pathlib import Path
import subprocess
import time
from lp_fp4_accel_common import ROOT, require

BINARY=ROOT/'research/lp-fp4-accel/target/release/lp-fp4-accel'


def compact(path, value):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    raw=(json.dumps(value,separators=(',',':'),allow_nan=False)+'\n').encode()
    with path.open('xb') as stream:
        stream.write(raw);stream.flush();os.fsync(stream.fileno())


class Service:
    def __init__(self, image, model, log, equilibrate=True):
        self.log=Path(log).open('xb');prefix=[]
        if os.environ.get('AI_OPTIMIZER_SANITIZER'):
            tool=os.environ['AI_OPTIMIZER_SANITIZER']
            require(tool in ('memcheck','racecheck','initcheck','synccheck'),'sanitizer')
            prefix=['/usr/local/cuda/bin/compute-sanitizer','--tool',tool,'--error-exitcode','86','--log-file',str(log)+'.sanitizer']
        args=prefix+[str(BINARY),'serve',str(image),str(model)]+([] if equilibrate else ['unscaled'])
        self.proc=subprocess.Popen(args,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=self.log,text=True,bufsize=1)
        self.solve_id=0;self.generation=0;self.ready=self.read()
    def read(self):
        line=self.proc.stdout.readline()
        if not line:raise RuntimeError(f'GPU service ended: {self.proc.poll()}')
        return json.loads(line)
    def call(self,op,**fields):
        command=dict(op=op,solve_id=self.solve_id,generation=self.generation,**fields)
        self.proc.stdin.write(json.dumps(command,separators=(',',':'),allow_nan=False)+'\n');self.proc.stdin.flush()
        result=self.read()
        if op=='solve':self.solve_id+=1;self.generation=0
        elif op=='debug_finish':self.solve_id=result['solve_id'];self.generation=0
        else:self.generation=result.get('generation',self.generation)
        return result
    def solve_to_file(self,path,**fields):
        """Time through durable native response delivery; parse analysis afterwards."""
        start=time.monotonic_ns()
        command=dict(op='solve',solve_id=self.solve_id,generation=0,**fields)
        self.proc.stdin.write(json.dumps(command,separators=(',',':'),allow_nan=False)+'\n');self.proc.stdin.flush()
        line=self.proc.stdout.readline()
        if not line:raise RuntimeError(f'GPU service ended: {self.proc.poll()}')
        with Path(path).open('xb') as stream:
            stream.write(line.encode());stream.flush();os.fsync(stream.fileno())
        elapsed=time.monotonic_ns()-start
        result=json.loads(line);self.solve_id+=1;self.generation=0
        return result,elapsed
    def close(self,expected=0):
        if not self.proc.stdin.closed:self.proc.stdin.close()
        try:code=self.proc.wait(timeout=10)
        except subprocess.TimeoutExpired:self.proc.kill();self.proc.wait();raise
        self.log.close();require(code==expected,f'service exit {code}')
