"""Independent rational ADR-0037 correction/merit admission oracle.

No candidate arithmetic imports. The fixture contains exact-real results and
minimal binary64 enclosures, computed with Fraction, not a solver approximation.
"""
import argparse
from fractions import Fraction as F
import hashlib
import json
import math
from pathlib import Path
import random
import struct

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / 'tests/regression/lp-refine-oracle.json'


def enclosure(x):
    v = float(x)
    if not math.isfinite(v):
        raise ValueError('oracle range')
    f = F(v)
    return dict(lower=v if f <= x else math.nextafter(v, -math.inf),
                upper=v if f >= x else math.nextafter(v, math.inf))


def bound(x, lower):
    if x is None:
        return dict(kind='negative_infinity' if lower else 'positive_infinity')
    return dict(kind='finite', value=float(x))


def dot(a, b):
    return sum((x*y for x, y in zip(a, b)), F())


def exact(case):
    doc = case['model']
    n = len(doc['variables']); m = len(doc['constraints'])
    a = [[F() for _ in range(n)] for _ in range(m)]
    for i, row in enumerate(doc['constraints']):
        for term in row['terms']:
            a[i][term['variable_id']] = F(term['coefficient'])
    b = [r + [F(-1 if j == i else 0) for j in range(m)] for i, r in enumerate(a)]
    g = [F() for _ in range(n+m)]
    for term in doc['objective']['terms']:
        g[term['variable_id']] = F(term['coefficient'])
    sense = 1 if doc['objective']['sense'] == 'minimize' else -1
    g = [sense*x for x in g]
    box = []
    for item in doc['variables']+doc['constraints']:
        box.append(tuple(F(item[k]['value']) if item[k]['kind'] == 'finite' else None for k in ('lower', 'upper')))
    v = list(map(F, case['v'])); y = list(map(F, case['y']))
    rp = [-dot(r, v) for r in b]
    rd = [g[j] - sum((b[i][j]*y[i] for i in range(m)), F()) for j in range(n+m)]
    sv = [max([F(1)] + [abs(x) for x in limits if x is not None]) for limits in box]
    sg = [max(F(1), abs(x)) for x in g]
    sp = [max(F(1), dot(list(map(abs, r)), sv)) for r in b]
    def project(x, limits):
        lo, hi = limits
        return min(x, hi) if lo is None and hi is not None else max(x, lo) if hi is None and lo is not None else x if lo is None else min(max(x, lo), hi)
    projected = [abs(x-project(x-s/t*r, limits))/s for x, s, t, r, limits in zip(v, sv, sg, rd, box)]
    violations = [abs(x-project(x, limits))/s for x, s, limits in zip(v, sv, box)]
    merit = max([F()] + [abs(r)/s for r, s in zip(rp, sp)] + projected + violations)
    # Independent box-stationarity condition, including deterministic fixed bounds.
    stationary = True
    for x, r, (lo, hi) in zip(v, rd, box):
        stationary &= (lo is None or x >= lo) and (hi is None or x <= hi)
        if lo is not None and hi is not None and lo == hi:
            continue
        stationary &= r == 0 or (lo is not None and x == lo and r >= 0) or (hi is not None and x == hi and r <= 0)
    assert (max(projected+violations, default=F()) == 0) == stationary
    maps = 0
    # Exhaust exact dyadic target/correction maps, independently of scale selection.
    for ep, ed in [(-10, 10), (-1, 0), (0, -1), (1, 1), (10, -10)]:
        dp = F(2)**ep; dd = F(2)**ed
        target_x = [F(k-2) for k in range(n)]
        target = target_x + [dot(row,target_x) for row in a]
        d = [dp*(x-x0) for x, x0 in zip(target, v)]
        w = [F(i+1) for i in range(m)]
        yn = [x+z/dd for x, z in zip(y, w)]
        for (lo, hi), x, x0, change in zip(box, target, v, d):
            if lo is not None: assert (x >= lo) == (change >= dp*(lo-x0))
            if hi is not None: assert (x <= hi) == (change <= dp*(hi-x0))
        for j in range(n+m):
            assert dd*rd[j] - sum((b[i][j]*w[i] for i in range(m)), F()) == dd*(g[j]-sum((b[i][j]*yn[i] for i in range(m)), F()))
        assert all(dot(row,d)==dp*residual for row,residual in zip(b,rp))
        offset=sense*F(doc['objective']['offset'])
        assert dot(g,target)+offset == dot(g,v)+offset+dot(y,rp)+dot([dd*x for x in rd],d)/(dp*dd)
        # Perturbed-operator identity and both anchor orientations.
        e = [[F((i+j)%3-1, 1024) if j<n else F() for j in range(n+m)] for i in range(m)]
        bhat = [[x+z for x, z in zip(r, er)] for r, er in zip(b, e)]
        eta = [dot(r,d)-dp*p for r,p in zip(bhat,rp)]
        updated = [x+z/dp for x,z in zip(v,d)]
        assert [-dot(r,updated) for r in b] == [(dot(er,d)-z)/dp for er,z in zip(e,eta)]
        for matrix in (b, list(map(list, zip(*b)))):
            if not matrix: continue
            anchor = [F(j) for j in range(len(matrix[0]))]
            delta = [F(j%3-1,8) for j in range(len(anchor))]
            for row in matrix:
                error = [x/F(1024) for x in row]
                assert dot(row,anchor)+dot([x+z for x,z in zip(row,error)],delta)-dot(row,[x+z for x,z in zip(anchor,delta)]) == dot(error,delta)
                assert abs(dot(error,delta)) <= sum(map(abs,error))*max(map(abs,delta),default=F())
        maps += 1
    return dict(primal=[enclosure(x) for x in rp],dual=[enclosure(x) for x in rd],
                merit=enclosure(merit),stationary=bool(stationary),maps=maps)


def generate():
    rng = random.Random(17021)
    shapes = [(None,None),(0,None),(None,2),(-1,3),(1,1)]
    cases = []
    for index in range(240):
        n = 1+index%3; m = index%4
        variables=[]; rows=[]
        for j in range(n):
            lo,hi=shapes[(index+j)%len(shapes)]
            variables.append(dict(id=j,domain='continuous',lower=bound(lo,True),upper=bound(hi,False)))
        for i in range(m):
            lo,hi=shapes[(index+2*i+1)%len(shapes)]
            rows.append(dict(id=i,lower=bound(lo,True),upper=bound(hi,False),terms=[dict(variable_id=j,coefficient=rng.randrange(-4,5)/4) for j in range(n)]))
        model=dict(schema_version=1,model_id=f'gpup-refine-oracle-{index}',variables=variables,constraints=rows,
                   objective=dict(sense='minimize' if index%2==0 else 'maximize',offset=7.,terms=[dict(variable_id=j,coefficient=rng.randrange(-4,5)/4) for j in range(n)]))
        c=dict(model=model,v=[rng.randrange(-8,9)/4 for _ in range(n+m)],y=[rng.randrange(-8,9)/4 for _ in range(m)])
        c['expected']=exact(c); cases.append(c)
    return dict(identity='lp-refine-oracle-v1',seed=17021,cases=cases)


def main():
    p=argparse.ArgumentParser();p.add_argument('--check',action='store_true');args=p.parse_args()
    raw=(json.dumps(generate(),sort_keys=True,separators=(',',':'),allow_nan=False)+'\n').encode()
    if args.check:
        if FIXTURE.read_bytes()!=raw:raise ValueError('refinement oracle fixture differs')
    else:FIXTURE.write_bytes(raw)
    print(json.dumps(dict(cases=240,correction_maps=1200,sha256=hashlib.sha256(raw).hexdigest())))

if __name__=='__main__':main()
