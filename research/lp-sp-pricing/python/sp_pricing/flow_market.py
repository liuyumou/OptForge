"""Exact flat markets via a signed-network double cover and checked flow duality.

Costs are integer demands. Expert weights are scaled to integer capacities.
Opposite-cover arc flows average to expert allocations whose signed coordinate
balances vanish. Their objective is a lower bound for every price vector.
Equality with the directly evaluated market proves global optimality. The native
controller minimizes prices lexicographically on the residual potential face.
"""
import ctypes as C
from fractions import Fraction as Q
import hashlib
from pathlib import Path
import time
from .exact import Limit

DEFAULT_LIBRARY = Path(__file__).resolve().parents[2]/"target/cpu/libsp_market.so"


def minimize(market, library=DEFAULT_LIBRARY):
    weights, denominator = market.scaled_weights()
    if any(w.bit_length()>121 for w in weights) or sum(weights).bit_length()>125:
        raise Limit("native_market_capacity_bits")
    options = [((-1, 0, 0), *e.options) for e in market.experts]
    offsets = [0]
    flat = []
    for expert in options:
        flat.extend(expert);offsets.append(len(flat))
    if any(abs(a)>2**55 for _, _, a in flat):
        raise Limit("native_market_cost_bits")
    lib = C.CDLL(str(library))
    pi, pu, pl = C.POINTER(C.c_int), C.POINTER(C.c_uint64), C.POINTER(C.c_int64)
    lib.sp_market.argtypes = [C.c_int]*3+[pi, pi, pi, pl, pu, pu, C.c_uint64, C.c_uint64, pl, pu, pu, pu]
    lib.sp_market.restype = C.c_int
    low = (C.c_uint64*len(weights))(*(w&((1<<64)-1) for w in weights))
    high = (C.c_uint64*len(weights))(*(w>>64 for w in weights))
    price = (C.c_int64*market.n)()
    flow_low, flow_high = (C.c_uint64*(2*len(flat)))(), (C.c_uint64*(2*len(flat)))()
    metrics = (C.c_uint64*3)()
    remaining = market.work.seconds-(time.monotonic()-market.work.started)
    if remaining<=0:
        raise Limit("deadline")
    start = time.perf_counter_ns()
    code = lib.sp_market(market.n, len(weights), len(flat),
        (C.c_int*len(offsets))(*offsets),
        (C.c_int*len(flat))(*(i for i, _, _ in flat)),
        (C.c_int*len(flat))(*(h for _, h, _ in flat)),
        (C.c_int64*len(flat))(*(a for _, _, a in flat)), low, high,
        int(remaining*1e9), max(1, market.work.max_operations-market.work.operations),
        price, flow_low, flow_high, metrics)
    if code:
        if code in (1, 2, 3, 6, 9, -2):
            raise Limit("native_market_"+str(code))
        raise ArithmeticError("native flow market failure "+str(code))
    native_ns = time.perf_counter_ns()-start
    market.work.tick(count=int(metrics[0]))
    prices = [Q(v, 2) for v in price]
    allocations = []
    balance = [0]*market.n
    total_value = 0
    for j, (i, h, a) in enumerate(flat):
        mass = sum(int(flow_low[2*j+k])+(int(flow_high[2*j+k])<<64) for k in (0, 1))
        allocations.append(mass)
        if i >= 0:
            balance[i] += h*mass
        total_value += a*mass
    if any(balance) or any(sum(allocations[offsets[e]:offsets[e+1]]) != 2*w for e, w in enumerate(weights)):
        raise ArithmeticError("market allocation certificate balance")
    value, _, _ = market.evaluate(prices)
    if value != Q(total_value, 2*denominator):
        raise ArithmeticError("market flow duality gap")
    if any(abs(p)>market.bound for p in prices):
        raise ArithmeticError("market price bound")
    return prices, dict(value=value, exact=True, oracle="signed_network_flow",
        native_ns=native_ns, scans=int(metrics[0]), augmentations=int(metrics[1]),
        distance_phases=int(metrics[2]), allocation_denominator=2*denominator,
        allocations=allocations, offsets=offsets,
        native_sha256=hashlib.sha256(Path(library).read_bytes()).hexdigest())
