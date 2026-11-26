"""Section 6.4 investment controller, independent of market representation.

`market.propose(history, wealth)` returns an exact market minimizer;
`market.gains(history, prices, feedback)` returns the worst tied gain per expert.
The production grouped-market/ellipsoid adapter remains a separate requirement.
Small injected markets test this controller without changing paper constants.
"""
from fractions import Fraction as Q
from .exact import Limit
from .market import median


def depth(n):
    if n < 1:
        raise ValueError("positive coordinate count")
    d = 1
    while 5**d <= 2*n*4**d:
        d += 2
    return d


def parameters(n, bound):
    if bound < 1:
        raise ValueError("positive demand bound")
    d = depth(n)
    choices = 2*n*(2*bound+1)
    experts = choices**4*(1+d*choices)
    root = 524289+3072*experts.bit_length()  # ceil(log2(|E|+1))
    return dict(depth=d, branching=524289, root_branching=root,
                experts=experts, leaf_probes=root*524289**(d-1))


def investment_search(n, bound, market, labels, work, *, query_limit=1024, component_parameters=None):
    settings = parameters(n, bound)
    component = component_parameters is not None
    if component:
        settings = dict(settings, **component_parameters)
        if any(settings[k] < 1 or settings[k]%2 != 1 for k in ("depth", "branching", "root_branching")):
            raise ValueError("odd positive component dimensions")
    calls = 0
    def node(history, wealth):
        nonlocal calls
        if len(history) == settings["depth"]:
            return median(history), wealth
        probes = settings["branching"] if history else settings["root_branching"]
        children, start_total = [], sum(wealth, Q(0))
        for _ in range(probes):
            work.tick()
            local = [w*Q(16383, 16384) for w in wealth]
            prices = market.propose(history, local)
            child_prices, returned = node(history+[prices], [w/Q(16384) for w in wealth])
            if calls >= query_limit:
                raise Limit("literal_recursive_query_limit")
            signs = labels(child_prices)
            calls += 1
            feedback = [signs[i] if child_prices[i] == prices[i] else
                        (1 if child_prices[i] > prices[i] else -1) for i in range(n)]
            gains = market.gains(history, prices, feedback)
            if len(gains) != len(wealth) or len(returned) != len(wealth) or any(g not in (-1, 0, 1) for g in gains):
                raise ArithmeticError("market gain domain")
            wealth = [w*(1+Q(g, 16))+r for w, g, r in zip(local, gains, returned)]
            if any(w <= 0 for w in wealth) or sum(wealth, Q(0)) > start_total:
                raise ArithmeticError("recursive wealth invariant")
            work.tick(*wealth)
            children.append(child_prices)
        return median(children), wealth
    if not component and settings["leaf_probes"] > query_limit:
        raise Limit("literal_tree_query_admission")
    prices, wealth = node([], [Q(1)]*market.expert_count)
    return dict(prices=prices, wealth=wealth, queries=calls, component_test=component,
                paper_constants=not component)
