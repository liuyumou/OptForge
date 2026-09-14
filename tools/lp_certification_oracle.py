"""Generate independent binary64 certification fixtures using exact rational arithmetic.

These are correctness fixtures, not an experiment split or a performance study.
Run with --write to regenerate; the ordinary gate verifies committed contents.
"""

import argparse
from fractions import Fraction
import json
import math
from pathlib import Path
import struct

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests/regression/lp-certification-oracle.json"


def bits(value):
    return struct.pack(">d", value).hex()


def fraction(value):
    return Fraction.from_float(value)


def directed(value, up):
    try:
        result = float(value)
    except OverflowError:
        result = math.inf if value > 0 else -math.inf
    if math.isinf(result):
        if result > 0 and not up:
            result = math.nextafter(result, -math.inf)
        elif result < 0 and up:
            result = math.nextafter(result, math.inf)
    elif (fraction(result) < value if up else fraction(result) > value):
        result = math.nextafter(result, math.inf if up else -math.inf)
    return bits(result)


def endpoints(value):
    return {"lower": directed(value, False), "upper": directed(value, True)}


def build():
    tiny = math.ulp(0.0)
    maximum = float.fromhex("0x1.fffffffffffffp+1023")
    samples = [0.0, -0.0, tiny, -tiny, 3*tiny, math.ldexp(1.0, -1022),
               math.nextafter(math.ldexp(1.0, -1022), 0), 0.1, -0.3, 0.5, 1.0,
               math.nextafter(1.0, 0), math.nextafter(1.0, math.inf), 3.0,
               -1e16, 1e16, math.ldexp(1.0, 900), -maximum, maximum]
    arithmetic = []
    for left in samples:
        for right in samples:
            for op in ["add", "subtract", "product"]:
                a, b = fraction(left), fraction(right)
                exact = {"add": lambda: a+b, "subtract": lambda: a-b,
                         "product": lambda: a*b}[op]()
                # At the extreme endpoints a deliberately widened product may
                # refuse a finite enclosure. All other finite cases must work.
                expected = endpoints(exact)
                finite = all(math.isfinite(struct.unpack(">d", bytes.fromhex(v))[0])
                             for v in expected.values())
                required = finite and abs(exact) < fraction(maximum)
                arithmetic.append({"op": op, "left": bits(left), "right": bits(right),
                                   "required": required, **expected})
    sums = []
    for values in [[], [tiny, -tiny], [1e16, 1.0, -1e16],
                   [1e16] + [1.0]*2048, [maximum, maximum, -maximum]]:
        exact = sum(map(fraction, values), Fraction())
        sums.append({"values": list(map(bits, values)), "required": len(values) != 3 or values[0] != maximum,
                     **endpoints(exact)})

    programs = []

    def program(name, c, matrix, rows, columns, y, offset=0.0, required=True):
        # Compute weak duality directly with exact Fraction operations. No
        # floating-point reduction, error estimate, or interval logic is copied.
        repaired = [v if (v >= 0 or hi is not None) and (v <= 0 or lo is not None)
                    else 0.0 for v, (lo, hi) in zip(y, rows)]
        result = fraction(offset)
        for v, (lo, hi) in zip(repaired, rows):
            if v:
                result += fraction(v)*fraction(lo if v > 0 else hi)
        for j, ((lo, hi), cost) in enumerate(zip(columns, c)):
            reduced = fraction(cost) - sum((fraction(row[j])*fraction(v)
                       for row, v in zip(matrix, repaired)), Fraction())
            if reduced:
                side = lo if reduced > 0 else hi
                if side is None:
                    result = None
                    break
                result += reduced*fraction(side)
        for sense in ["minimize", "maximize"]:
            sign = 1 if sense == "minimize" else -1
            programs.append({"name": name+"-"+sense, "sense": sense,
                "cost": [bits(sign*v) for v in c], "offset": bits(sign*offset),
                "matrix": [list(map(bits, row)) for row in matrix],
                "rows": [[bits(v) if v is not None else None for v in pair] for pair in rows],
                "columns": [[bits(v) if v is not None else None for v in pair] for pair in columns],
                "dual": list(map(bits, y)), "required": required and result is not None,
                "exact_bound": None if result is None else directed(sign*result, sense == "maximize")})

    program("cancellation", [0.1, 0.30000000000000004], [[1.,3.]], [(0.,0.)],
            [(-3e16,3e16),(-1e16,1e16)], [0.1])
    program("uncertain-free-positive", [0.30000000000000004], [[3.]], [(0.,0.)], [(None,None)], [0.1])
    program("uncertain-free-negative", [0.3], [[3.]], [(0.,0.)], [(None,None)], [0.1])
    program("exact-free-zero", [1.5], [[3.]], [(0.,0.)], [(None,None)], [0.5])
    program("one-sided-safe", [1.], [], [], [(2.,None)], [])
    program("one-sided-unbounded", [1.], [], [], [(None,2.)], [])
    program("repaired-row", [1.], [[1.]], [(None,2.)], [(-2.,3.)], [0.5])
    program("row-underflow", [tiny], [[1.]], [(-0.5,-0.5)], [(None,None)], [tiny])
    program("matrix-underflow", [0.], [[tiny]], [(0.,0.)], [(0.,1.)], [0.5])
    program("dot-cancellation", [1.], [[1e16],[1.],[-1e16]], [(0.,0.)]*3, [(-1.,1.)], [1.]*3)
    program("product-overflow", [1.], [[2.]], [(0.,0.)], [(-1.,1.)], [maximum], required=False)
    program("total-overflow", [maximum], [], [], [(1.,1.)], [], offset=maximum, required=False)
    program("offset-cancellation", [1e16,1.,-1e16], [], [], [(1.,1.)]*3, [], offset=-0.5)

    gaps = []

    def gap(name, cost, x, bound, absolute, relative, offset=0., must_close=False, required=True):
        objective = sum((fraction(c)*fraction(v) for c,v in zip(cost,x)), fraction(offset))
        distance = objective-fraction(bound)
        allowed = fraction(absolute)+fraction(relative)*max(abs(objective), abs(fraction(bound)))
        closes = -fraction(absolute) <= distance <= allowed
        for sense in ["minimize", "maximize"]:
            sign = 1 if sense == "minimize" else -1
            gaps.append({"name": name+"-"+sense, "sense": sense,
                "cost": [bits(sign*c) for c in cost], "primal": list(map(bits,x)),
                "offset": bits(sign*offset), "bound": bits(sign*bound),
                "absolute": bits(absolute), "relative": bits(relative),
                "exact_gap_upper": directed(max(Fraction(),distance), True),
                "exact_closes": closes, "must_close": must_close, "required": required})

    gap("relative", [1.], [0.95], 0.9, 0., 0.1, must_close=True)
    gap("lost-objective-term", [1e16,1.,-1e16], [1.,1.,1.], 0., 0., 0.)
    gap("lost-objective-product", [0.1,0.30000000000000004], [3e16,-1e16], 0., 0., 0., offset=0.5)
    gap("offset", [1.], [1.], 3., 0., 0., offset=2., must_close=True)
    gap("wrong-bound-direction", [1.], [1.], 2., 0.1, 0.)
    gap("underflow", [tiny], [0.5], 0., 0., 0.)
    gap("threshold-overflow", [2.], [1.], 0., maximum, maximum, required=False)
    gap("objective-overflow", [maximum], [2.], 0., 0., 0., required=False)
    gap("gap-overflow", [maximum], [1.], -maximum, 0., 0., required=False)
    return {"fixture_version": 1, "arithmetic": arithmetic, "sums": sums,
            "programs": programs, "gaps": gaps}


def render(document):
    # One case per line keeps the committed oracle inspectable without expanding
    # large integer-rational fixtures into thousands of formatting-only lines.
    fields = []
    for key, value in document.items():
        if isinstance(value, list):
            encoded = "[\n" + ",\n".join(json.dumps(case, separators=(",", ":")) for case in value) + "\n]"
        else:
            encoded = json.dumps(value)
        fields.append(json.dumps(key) + ":" + encoded)
    return "{\n" + ",\n".join(fields) + "\n}\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    text = render(build())
    if args.write:
        FIXTURE.write_text(text)
    elif FIXTURE.read_text() != text:
        raise SystemExit("certification rational fixtures differ; regenerate and review")
    print("exact rational certification fixtures: passed")


if __name__ == "__main__":
    main()
