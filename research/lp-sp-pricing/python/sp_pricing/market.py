"""Exact finite-pool markets for the separately labeled practical search."""
from dataclasses import dataclass
from fractions import Fraction as Q
import random
import math
from .exact import dot, Limit
from .lp import certificate, free


@dataclass
class Expert:
    # Options are (coordinate, sign, integer demand); outside utility is zero.
    options: tuple
    weight: Q = Q(1)


class Market:
    def __init__(self, n, bound, work, extra=4096, seed=20261125):
        if n < 1 or bound < 1 or not 0 <= extra <= 65536:
            raise ValueError("market dimensions")
        if 6*n+extra > 1_000_000:
            raise Limit("expert_storage_limit")
        self.n, self.bound, self.work = n, bound, work
        self.experts = [Expert(((i, h, a),)) for i in range(n)
                        for h in (-1, 1) for a in (-bound, 0, bound)]
        rng = random.Random(seed)
        demands = sorted(set([-bound, -(bound+1)//2, -1, 0, 1, (bound+1)//2, bound]))
        for _ in range(extra):
            slots = rng.sample(range(2*n), min(4, 2*n))
            self.experts.append(Expert(tuple((s//2, 1 if s%2 else -1, rng.choice(demands)) for s in slots)))
        # Identical option sets have identical gains forever. Preserve their
        # multiplicity as wealth rather than resampling or discarding experts.
        self.initial_expert_count = len(self.experts)
        grouped = {}
        for expert in self.experts:
            key = tuple(sorted(expert.options))
            grouped[key] = grouped.get(key, Q(0))+expert.weight
        self.experts = [Expert(options, weight) for options, weight in sorted(grouped.items())]
        self.cuts = 0
        self._weight_cache = None

    def scaled_weights(self):
        if self._weight_cache is None:
            denominator = 1
            for expert in self.experts:
                denominator = math.lcm(denominator, expert.weight.denominator)
            self.work.tick(denominator)
            weights = [int(expert.weight*denominator) for expert in self.experts]
            self._weight_cache = weights, denominator
        return self._weight_cache

    def evaluate(self, prices):
        price_denominator = math.lcm(*(Q(p).denominator for p in prices))
        integral_prices = [int(p*price_denominator) for p in prices]
        weights, weight_denominator = self.scaled_weights()
        value, intercept, operations = 0, 0, 0
        gradient = [0]*self.n
        for index, (expert, weight) in enumerate(zip(self.experts, weights)):
            greatest, winner = 0, None
            for i, h, a in expert.options:
                utility = a*price_denominator-h*integral_prices[i]
                if utility > greatest:
                    greatest, winner = utility, (i, h, a)
            value += weight*greatest
            if winner is not None:
                i, h, a = winner
                gradient[i] -= h*weight
                intercept += a*weight
            operations += 2*(len(expert.options)+1)
            if index%256 == 255:
                self.work.tick(value, intercept, count=operations)
                operations = 0
        self.work.tick(value, intercept, price_denominator*weight_denominator, *gradient, count=operations)
        value = Q(value, price_denominator*weight_denominator)
        intercept = Q(intercept, weight_denominator)
        gradient = [Q(g, weight_denominator) for g in gradient]
        if dot(gradient, prices, self.work)+intercept != value:
            raise ArithmeticError("market separator identity")
        return value, gradient, intercept

    def minimize(self, cut_limit=4096, backend="auto"):
        if backend not in ("auto", "flow", "cuts"):
            raise ValueError("market backend")
        if backend != "cuts":
            from .flow_market import DEFAULT_LIBRARY, minimize
            if backend == "flow" or DEFAULT_LIBRARY.exists():
                try:
                    return minimize(self)
                except Limit as error:
                    if backend == "flow" or str(error) not in ("native_market_capacity_bits", "native_market_cost_bits", "native_market_-2", "native_market_3"):
                        raise
        n = self.n
        a, b = [], []
        for i in range(n):
            row = [Q(int(j == i)) for j in range(n)]+[Q(0)]
            a += [row, [-v for v in row]]
            b += [Q(self.bound), Q(self.bound)]
        a.append([Q(0)]*n+[Q(-1)])
        b.append(Q(0))
        objective = [Q(0)]*n+[Q(-1)]
        observed = set()
        lexicographic = False
        for _ in range(cut_limit):
            candidate = (certificate(a, b, objective, self.work, lexicographic=True)
                         if lexicographic else free(a, b, objective, self.work))
            if candidate["status"] != "optimal":
                raise ArithmeticError("market epigraph must attain optimum")
            prices, height = candidate["x"][:n], candidate["x"][n]
            value, gradient, intercept = self.evaluate(prices)
            self.cuts += 1
            if height == value:
                # First locate the optimal height, then separate until the
                # lexicographically minimal point is feasible for the full
                # epigraph. Only the final result needs an explicit dual proof.
                if not lexicographic:
                    lexicographic = True
                    continue
                if any(p.denominator not in (1, 2) for p in prices):
                    raise ArithmeticError("non-half-integral market vertex")
                return prices, dict(value=value, epigraph_certificate=candidate,
                                    cuts=len(observed), exact=True, oracle="exact_cutting_plane")
            if height > value:
                raise ArithmeticError("invalid epigraph lower bound")
            cut = tuple(gradient+[Q(-1)]), -intercept
            if cut in observed:
                raise ArithmeticError("repeated violated market cut")
            observed.add(cut)
            a.append(list(cut[0])); b.append(cut[1])
        raise Limit("market_cut_limit")

    def update(self, prices, labels):
        if len(labels) != self.n or any(h not in (-1, 1) for h in labels):
            raise ValueError("complete signed labels required")
        before = sum((e.weight for e in self.experts), Q(0))
        denominator = math.lcm(*(Q(p).denominator for p in prices))
        integers = [int(p*denominator) for p in prices]
        for expert in self.experts:
            utilities = [0]+[a*denominator-h*integers[i] for i, h, a in expert.options]
            top = max(utilities)
            gains = ([0] if utilities[0] == top else [])
            gains += [h*labels[i] for (i, h, _), u in zip(expert.options, utilities[1:]) if u == top]
            expert.weight *= 1+Q(min(gains), 16)
            self.work.tick(expert.weight)
        after = sum((e.weight for e in self.experts), Q(0))
        self._weight_cache = None
        if after > before:
            raise ArithmeticError("market wealth increased: unverified minimizer or wrong tie rule")
        return dict(before=before, after=after)

    def round_bound(self):
        growth, count = Q(1), 0
        while growth <= self.initial_expert_count:
            growth *= Q(17, 16)
            count += 1
            self.work.tick(growth)
        return 2*count+1


def median(points):
    if not points or len(points)%2 != 1:
        raise ValueError("odd nonempty median")
    return [sorted(col)[len(points)//2] for col in zip(*points)]
