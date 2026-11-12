"""Independent exact-rational validation of the CPU reference, never a solver run."""
import argparse
from fractions import Fraction as Q
import json
import math
import random
import struct
import subprocess
from lp_mixed2_common import ROOT, BASE, BINARY, put, ref, require


def float32(x):
    return struct.unpack('!f', struct.pack('!f', x))[0]


def check(request, result):
    require(result['status'] == 'enclosed', 'unexpected numerical refusal')
    a = request['matrix']; transpose = request['transpose']; p = result['product']
    size = a['cols'] if transpose else a['rows']
    require(all(len(p[k]) == size for k in ('values','error_bounds','representation_bounds','rounding_bounds')), 'product shape')
    exact = [Q(0) for _ in range(size)]; represented = exact.copy()
    for row in range(a['rows']):
        for k in range(a['offsets'][row], a['offsets'][row+1]):
            col = a['columns'][k]; i = col if transpose else row
            x = Q(request['x'][row if transpose else col]); coefficient = a['values'][k]
            exact[i] += Q(coefficient) * x
            represented[i] += Q(float32(coefficient)) * x
    for i in range(size):
        v = p['values'][i]; bound = p['error_bounds'][i]
        require(math.isfinite(v) and math.isfinite(bound) and bound >= 0, 'invalid enclosure')
        require(abs(Q(v)-exact[i]) <= Q(bound), 'original dot escapes enclosure')
        require(abs(Q(v)-represented[i]) <= Q(p['rounding_bounds'][i]), 'rounding escapes enclosure')
        require(abs(exact[i]-represented[i]) <= Q(p['representation_bounds'][i]), 'representation escapes enclosure')
    return size


def cases():
    rng = random.Random(360069)
    matrices = []
    for _ in range(256):
        rows=rng.randrange(1,9);cols=rng.randrange(1,10);offsets=[0];columns=[];values=[]
        for row in range(rows):
            for col in range(cols):
                if rng.random() < .6:
                    columns.append(col)
                    # Include cancellation and generic significands across the FP32 range.
                    value=math.ldexp(rng.uniform(-1,1),rng.randrange(-120,121))
                    values.append(value)
            offsets.append(len(values))
        matrices.append(dict(rows=rows,cols=cols,offsets=offsets,columns=columns,values=values))
    special=[
        [1.0,1.0,-1.0], [0.1,-0.1,1.00000001], [-0.0,0.0,1.0],
        [2.0**-149, -2.0**-149, 2.0**-126],
        [float32(3.4028234663852886e38), -float32(3.4028234663852886e38),1.0],
        [1+2.0**-24, 1+3*2.0**-24, -1-2.0**-24],
    ]
    for values in special:
        matrices.append(dict(rows=1,cols=3,offsets=[0,3],columns=[0,1,2],values=values))
    requests=[]
    for a in matrices:
        for transpose in (False,True):
            n=a['rows'] if transpose else a['cols']
            for regime in ('normal','tiny'):
                x=[math.ldexp(rng.uniform(-1,1),rng.randrange(-400,401) if regime=='normal' else -1000) for _ in range(n)]
                requests.append(dict(matrix=a,x=x,transpose=transpose))
    # Explicit cancellation where the last small term can be lost in accumulation.
    requests.append(dict(matrix=matrices[-6],x=[2.0**53,1.0,2.0**53],transpose=False))
    return requests


def run(binary=BINARY):
    requests=cases()
    command=[str(binary)]
    process=subprocess.run(command,input=''.join(json.dumps(r,allow_nan=False)+'\n' for r in requests),text=True,capture_output=True,check=True,timeout=60)
    results=[json.loads(line) for line in process.stdout.splitlines()]
    require(len(results)==len(requests),'differential response count')
    outputs=sum(check(a,b) for a,b in zip(requests,results))
    return dict(status='passed',seed=360069,requests=len(requests),outputs=outputs,
                binary=ref(binary),source=ref(ROOT/'tools/lp_mixed2_oracle.py'),
                exact_original_and_represented_dots=True,contains_subnormal_and_cancellation=True,
                no_solver_or_certificate_claim=True)

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',default=str(BASE/'oracle-v1.json'));args=parser.parse_args()
    result=run();put(args.output,result);print(result)
