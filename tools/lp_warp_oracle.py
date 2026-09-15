"""Independent exact-rational operation/error fixtures for ADR-0017 warp32.

Correctness fixtures only: no experiment seeds or numerical solve targets change.
"""
from fractions import Fraction as Q
from pathlib import Path
import argparse,json,math,struct
ROOT=Path(__file__).resolve().parents[1]
FIXTURE=ROOT/'tests/regression/lp-warp32-oracle.json'
def bits(x):return struct.pack('>d',x).hex()
def rounded(q):
    try:return float(q)
    except OverflowError:return math.copysign(math.inf,q.numerator)
def add(a,b):
    exact=Q(a[0])+Q(b[0]); value=rounded(exact)
    return value,a[1]+b[1]+abs(Q(value)-exact)
def build():
    cases=[]
    for n in [0,1,2,3,7,31,32,33,63,64,65,255,256,257,1023,1024,1025,2049]:
        a=[math.ldexp((-1.0 if i%3==0 else 1.0)*(1+(i%7)/8), (i%9)-4) for i in range(n)]
        b=[(1+(i%11)/16) for i in range(n)]
        if n==65:
            a=[0.0]*n;b=[1.0]*n;a[0]=1e16;a[32]=1.0;a[64]=-1e16
        if n==3:a=[-0.0,math.ulp(0.0),-math.ulp(0.0)];b=[1.0,0.5,0.5]
        lanes=[(0.0,Q(0)) for _ in range(32)]
        exact=sum((Q(x)*Q(y) for x,y in zip(a,b)),Q(0))
        for lane in range(32):
            for i in range(lane,n,32):
                product=Q(a[i])*Q(b[i]);value=rounded(product)
                lanes[lane]=add(lanes[lane],(value,abs(Q(value)-product)))
        for offset in [16,8,4,2,1]:
            for lane in range(offset):lanes[lane]=add(lanes[lane],lanes[lane+offset])
        result,error=lanes[0]
        assert abs(Q(result)-exact)<=error
        cases.append({'count':n,'a':[bits(x) for x in a],'b':[bits(x) for x in b],
                      'result':bits(result),'exact':str(exact),'error_bound':str(error)})
    return {'schema_version':1,'arithmetic':'warp32-v1','cases':cases}
if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--write',action='store_true');args=parser.parse_args()
    value=build()
    if args.write:FIXTURE.write_text(json.dumps(value,separators=(',',':'))+'\n')
    elif json.loads(FIXTURE.read_text())!=value:raise SystemExit('warp32 rational fixture differs')
    print(f'warp32 exact-rational fixtures: {len(value["cases"])} passed')
