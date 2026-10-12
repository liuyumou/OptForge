"""Independent ADR-0035 Fraction dot fixtures; no candidate arithmetic imports."""
import json
import random
import struct
from fractions import Fraction
from pathlib import Path
from lp_expansion_oracle import round_fraction, power2

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / 'tests/regression/lp-exec-oracle.json'

def bits(v): return struct.unpack('>Q',struct.pack('>d',v))[0]
def value(b): return Fraction.from_float(struct.unpack('>d',int(b).to_bytes(8,'big'))[0])
def base(v):
    v=abs(v)
    if not v:return None
    n,d=v.numerator,v.denominator
    return n.bit_length()-d.bit_length()-52

def expected(left,right,repeat=1):
    if len(left)!=len(right) or len(left)*repeat>65536:return {'error':'dot_dimensions'}
    try: a,b=list(map(value,left)),list(map(value,right))
    except (ValueError,OverflowError):return {'error':'nonfinite_operand'}
    exponents=[base(x)+base(y) for x,y in zip(a,b) if x and y]
    if exponents and max(exponents)-min(exponents)>128:return {'error':'product_exponent_window'}
    result=round_fraction(sum((x*y for x,y in zip(a,b)),Fraction())*repeat,(53,-1022,1023))
    if result['infinity_sign']:return {'error':'output_overflow'}
    exact=Fraction(result['coefficient'])*power2(result['exponent'])
    output=bits(float(exact)) if exact else result['zero_sign']<<63
    flags=int('inexact' in result['flags'])+4*int('underflow' in result['flags'])
    if 0<(output&((1<<63)-1))<(1<<52):flags|=2
    return {'bits':output,'flags':flags,'error_exponent':result['error_exponent']}

def generate():
    cases=[]
    def add(a,b,repeat=1):cases.append(dict(left=a,right=b,repeat=repeat,expected=expected(a,b,repeat)))
    add([],[])
    for b in [0,1<<63,1,2,(1<<52)-1,1<<52,0x7fefffffffffffff,0x7ff0000000000000,0x7ff8000000000001]:
        for c in [bits(1.0),bits(.5),bits(-1.0),bits(2.0),0]:add([b],[c])
    add([bits(2**53-1),bits(-(2**53-2))],[bits(2**53-1),bits(2**53)])
    add([bits(1.0)],[0x7ff0000000000000])
    for k in range(52):
        for sign in [0,1<<63]:add([(1<<k)|sign],[bits(.5)])
    for e in range(1,2047):
        a=(e<<52)|0xfffffffffffff
        add([a,a^(1<<63),a],[bits(1.0),bits(1.0),bits(2**-52)])
    for gap in [127,128,129]:add([bits(1.0),bits(2.0**-gap)],[bits(1.0)]*2)
    add([bits(1.0),bits(2**-53)],[bits(1.0)]*2)
    add([bits(1.0),bits(3*2**-53)],[bits(1.0)]*2)
    add([bits(float.fromhex('0x1.fffffffffffffp+0')),bits(2**-53)],[bits(1.0)]*2)
    add([0x7fefffffffffffff,0xffefffffffffffff],[bits(2.0)]*2)
    add([bits(1.0)],[bits(1.0)],65536)
    add([bits(1.0)],[bits(1.0)],65537)
    rng=random.Random(17004)
    for n in [1,2,31,32,33,127,256]:
        for _ in range(20):
            es=rng.randrange(10,2000)
            a=[(rng.randrange(2)<<63)|((es+rng.randrange(-9,10))<<52)|rng.getrandbits(52) for _ in range(n)]
            b=[(rng.randrange(2)<<63)|((1023+rng.randrange(-9,10))<<52)|rng.getrandbits(52) for _ in range(n)]
            add(a,b)
    return dict(identity='lp-exec-oracle-v1',seed=17004,cases=cases)

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--check',action='store_true');args=p.parse_args()
    data=json.dumps(generate(),sort_keys=True,separators=(',',':'))+'\n'
    if args.check:
        assert FIXTURE.read_text()==data
        print('exact executor oracle reproduced')
    else:FIXTURE.write_text(data)
