"""Independent exact-rational sparse-product fixtures for ADR-0021 (CPU only)."""
from fractions import Fraction as F
import math
import random
import struct
from pathlib import Path
from analyze_lp_rounding import components
from lp_protocol import ROOT,read_json,write_json


def bits(x):return struct.pack('>d',x).hex()
def number(s):return struct.unpack('>d',bytes.fromhex(s))[0]
def represented(x,k):
    m,e=math.frexp(x)
    return sum(map(F,components(m)[:k]))*F(2)**e


def generate():
    rng=random.Random(17002);cases=[]
    for count in [3,31,32,33,64,65,97,128]:
        a=[math.ldexp(rng.uniform(-1,1),rng.randrange(-12,12)) for _ in range(count)]
        x=[math.ldexp(rng.uniform(-1,1),rng.randrange(-12,12)) for _ in range(count)]
        # Cancellation, including a small term between large opposing products.
        a[:3]=[1.0,2**-40,-1.0];x[:3]=[2**20,1.0,2**20]
        expected=[]
        for k in [2,3]:
            terms=[represented(v,k)*represented(w,k) for v,w in zip(a,x)]
            exact=sum(terms);mass=sum(map(abs,terms))
            # Wide independent forward-error allowance, not an identical algorithm.
            allowance=max(float(mass*F(2)**-46),math.ulp(float(exact)))
            transpose=[represented(v,k)*represented(.75,k) for v in a]
            expected.append(dict(components=k,exact=str(exact),nearest=bits(float(exact)),absolute_allowance=allowance,
                                 transpose_nearest=[bits(float(v)) for v in transpose]))
        cases.append(dict(a=list(map(bits,a)),x=list(map(bits,x)),expected=expected))
    return dict(schema_version=1,seed=17002,oracle='Fraction of represented binary inputs; independently rounded exact dot products',cases=cases)


def pair(x):
    """Exact rational value of the ADR-0022 FP32 pair representation of x."""
    hi=struct.unpack('>f',struct.pack('>f',x))[0]
    lo=struct.unpack('>f',struct.pack('>f',x-hi))[0]
    return F(hi)+F(lo)


def generate_doublefloat():
    rng=random.Random(17003);cases=[]
    for count in [3,31,32,33,64,65,97,128]:
        a=[math.ldexp(rng.uniform(-1,1),rng.randrange(-12,12)) for _ in range(count)]
        x=[math.ldexp(rng.uniform(-1,1),rng.randrange(-12,12)) for _ in range(count)]
        a[:3]=[1.0,2**-30,-1.0];x[:3]=[2**10,1.0,2**10]
        terms=[pair(v)*pair(w) for v,w in zip(a,x)]
        exact=sum(terms);mass=sum(map(abs,terms))
        # The dropped lo*lo term and each FP32 pair operation lose about 2^-44 relative
        # to the mass; the allowance is a wide independent forward-error bound.
        allowance=max(float(mass*F(2)**-40),math.ulp(float(exact)))
        transpose=[pair(v)*pair(.75) for v in a]
        cases.append(dict(a=list(map(bits,a)),x=list(map(bits,x)),expected=dict(exact=str(exact),nearest=bits(float(exact)),absolute_allowance=allowance,
                          transpose_nearest=[bits(float(v)) for v in transpose],transpose_allowance=[max(float(abs(v)*F(2)**-44),math.ulp(float(v))) for v in transpose])))
    return dict(schema_version=1,seed=17003,oracle='Fraction of FP32 pair inputs; independently rounded exact dot products',cases=cases)


def verify_products():
    value=read_json(ROOT/'crates/optimizer-lp/tests/fixtures/research-products.json')
    for row in value['products']:
        exact=F(number(row['a']))*F(number(row['b']))
        assert str(exact)==row['exact'] and bits(float(exact))==row['nearest']
    return len(value['products'])


def main():
    path=ROOT/'crates/optimizer-lp/tests/fixtures/research-sparse.json';value=generate()
    if path.exists():
        if read_json(path)!=value:raise ValueError('sparse rational fixture changed')
    else:write_json(path,value)
    path=ROOT/'crates/optimizer-lp/tests/fixtures/research-doublefloat.json';df=generate_doublefloat()
    if path.exists():
        if read_json(path)!=df:raise ValueError('double-float rational fixture changed')
    else:write_json(path,df)
    print('CPU exact rational fixtures:',verify_products(),'scalar products;',len(value['cases']),'sparse rows with two/three-component and transpose references')
if __name__=='__main__':main()
