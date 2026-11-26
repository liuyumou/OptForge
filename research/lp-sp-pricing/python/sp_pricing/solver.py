"""Certificate-driven practical pricing; no baseline solver delegation.

The numerical search uses a restricted expert pool and data-dependent calibration.
Exact support-recovery LPs are separately counted and disclosed. They may dominate
runtime; successful recovery is not evidence that pricing improved performance.
"""
from fractions import Fraction as Q
from contextlib import contextmanager
import time
from .exact import Work, Limit, basis, nullspace, transpose, dot, rational
from .geometry import slack_space, paired_space, restrict_space, recover_slack_certificate, LabelOracle
from .calibration import DirectCalibration, paper_bounds
from .market import Market, median
from .lp import certificate


class PricingSolver:
    def __init__(self, work=None, extra_experts=4096, max_queries=1024,
                 batch_width=32, seed=20261125, gpu=None, market_backend="auto"):
        self.work = work or Work()
        if type(max_queries) is not int or max_queries<1:
            raise ValueError("query cap")
        self.extra_experts, self.max_queries = extra_experts, max_queries
        self.batch_width, self.seed = batch_width, seed
        self.events = []
        self.gpu = gpu
        self.market_backend = market_backend
        self.recovery_lps = 0
        self.queries = 0
        self.phase_ns = {}

    @contextmanager
    def phase(self, name):
        start = time.perf_counter_ns()
        try:
            yield
        finally:
            self.phase_ns[name] = self.phase_ns.get(name, 0)+time.perf_counter_ns()-start

    def recover(self, c, target, signs, minimize_support=False):
        n = len(signs)
        side = signs[target]
        selected = c if side == 1 else nullspace(c, self.work, n)
        selected = restrict_space(selected, [j for j in range(n) if signs[j] != side], self.work, n)
        if not selected:
            return None
        columns = transpose(selected)
        a = [[-v for v in col] for col in columns]
        b = [Q(-int(j == target)) for j in range(n)]
        self.recovery_lps += 1
        result = certificate(a, b, [Q(0)]*len(selected), self.work)
        if result["status"] == "infeasible":
            return None
        if result["status"] != "optimal":
            raise ArithmeticError("zero-objective recovery is bounded")
        vector = [dot(col, result["x"], self.work) for col in columns]
        if vector[target] < 1 or any(v < 0 for v in vector):
            raise ArithmeticError("recovery witness invalid")
        # An original-model witness already proves the practical result. Circuit
        # minimization is required by the literal reference reduction, but is
        # unnecessary for an independently checked practical certificate.
        if not minimize_support:
            return side, vector
        # Reduce support without inferring that separately removable coordinates
        # are jointly removable. Each accepted restriction is checked in order.
        for j in range(n):
            if j == target or vector[j] == 0:
                continue
            candidate = restrict_space(selected, [j], self.work, n)
            if not candidate:
                continue
            cols = transpose(candidate)
            self.recovery_lps += 1
            found = certificate([[-v for v in col] for col in cols], b,
                                [Q(0)]*len(candidate), self.work)
            if found["status"] == "optimal":
                selected = candidate
                vector = [dot(col, found["x"], self.work) for col in cols]
        return side, vector

    def feasibility(self, a, b, columns):
        if (len(b)+1)*(columns+1) > 100_000:
            raise Limit("explicit_reference_geometry_limit")
        if 2*(len(b)+1)**2 > 1_000_000:
            raise Limit("paired_basis_fill_limit")
        with self.phase("geometry_and_experts"):
            c = slack_space(a, b, self.work, columns)
            n = len(b)+1
            w = paired_space(c, self.work, n)
            calibration = DirectCalibration(w, self.work)
            market = Market(n, calibration.demand_bound, self.work, self.extra_experts, self.seed)
        prices_seen = []
        epochs=1;extra=self.extra_experts
        for round_index in range(self.max_queries-self.queries):
            # A failed epoch starts a larger deterministic pool from uniform
            # wealth. Its random stream contains the preceding pool as a prefix.
            # Old queries and failures remain in the trace; no theorem is
            # inferred for these bounded adaptive practical searches.
            if len(prices_seen) >= min(market.round_bound(),4 if epochs==1 else 16):
                if epochs>=3 or extra>=65536:raise Limit('practical_expert_epoch_limit')
                extra=min(65536,max(4096,4*extra));epochs+=1
                with self.phase('expert_expansion'):
                    market=Market(n,calibration.demand_bound,self.work,extra,self.seed)
                self.events.append(dict(kind='expert_expansion',epoch=epochs,extra_experts=extra,
                                        preceding_queries=len(prices_seen),wealth_reset=True))
                prices_seen=[]
            self.work.tick()
            with self.phase("market"):
                prices, market_proof = market.minimize(backend=self.market_backend)
            with self.phase("calibration"):
                calibrated = calibration.query(prices)
                oracle = LabelOracle(calibrated["basis"], calibrated["H"], calibrated["epsilon"],
                                     self.work, calibrated["epoch"],calibrated['displacement_bound'])
            if not oracle.broadcast_negative:
                raise ArithmeticError("calibration did not establish orthogonality separation")
            with self.phase("auxiliary_labels"):
                labels, proofs = oracle.labels(self.batch_width, expected_epoch=calibration.epoch, gpu=self.gpu)
            self.queries += 1
            prices_seen.append(prices)
            with self.phase("wealth_update"):
                wealth = market.update(prices, labels)
            self.events.append(dict(query=self.queries, prices=prices, labels=labels,
                calibration=calibrated, market_value=market_proof["value"],
                market_proof=market_proof, market_experts=len(market.experts),
                expert_epoch=epochs,
                auxiliary_calls=oracle.calls, recovered_labels=n, wealth=wealth,
                cpu_oracle="exact_rational_simplex_bland", gpu_work=self.gpu is not None,
                label_proofs=proofs, gpu=oracle.gpu_metadata))
            # Direct label signs are proposals for global sides. A separate
            # exact restricted-cone witness, not the proposal, establishes truth.
            with self.phase("exact_support_recovery"):
                recovered = self.recover(c, n-1, labels)
            if recovered:
                side, vector = recovered
                return recover_slack_certificate(a, b, side, vector, self.work, columns)
            if len(prices_seen)%2:
                proposal = [1 if p >= 0 else -1 for p in median(prices_seen)]
                with self.phase("exact_support_recovery"):
                    recovered = self.recover(c, n-1, proposal)
                if recovered:
                    side, vector = recovered
                    return recover_slack_certificate(a, b, side, vector, self.work, columns)
        raise Limit("practical_price_query_limit")

    def solve(self, model, mode="practical"):
        a = [list(map(rational, row)) for row in model["A"]]
        b, c = list(map(rational, model["b"])), list(map(rational, model["c"]))
        n, m = len(c), len(b)
        if len(a) != m or any(len(row) != n for row in a) or model.get("sense", "max") != "max":
            raise ValueError("canonical max Ax<=b with free variables required")
        if mode in ("paper_reference", "certified_acceleration"):
            from .reference import solve_reference
            return solve_reference(self,model,mode)
        if mode != "practical":
            raise ValueError("unknown mode")
        if self.max_queries>1024 and not getattr(self,'literal_reference',False):
            raise ValueError('practical query cap')
        start = self.feasibility(a, b, n)
        if start["status"] == "infeasible":
            return self.result(start)
        recession = self.feasibility(a+[[-v for v in c]], [Q(0)]*m+[Q(-1)], n)
        if recession["status"] == "feasible":
            return self.result(dict(status="unbounded", x=start["x"], ray=recession["x"]))
        # Section 3.3: one mixed feasibility system for primal/dual optimality
        # and strict complementarity. Homogenize strict rows with alpha >= 1.
        rows, rhs, strict = [], [], []
        def append(row, value, is_strict=False):
            rows.append(row); rhs.append(value); strict.append(is_strict)
        for i in range(m):
            append(a[i]+[Q(0)]*m, b[i])
            append([Q(0)]*n+[Q(-int(i == j)) for j in range(m)], Q(0))
            append(a[i]+[Q(-int(i == j)) for j in range(m)], b[i], True)
        for j in range(n):
            row = [Q(0)]*n+[a[i][j] for i in range(m)]
            append(row, c[j]); append([-v for v in row], -c[j])
        gap = [-v for v in c]+b
        append(gap, Q(0)); append([-v for v in gap], Q(0))
        homogenized = [row+[-value] for row, value in zip(rows, rhs)]
        limits = [Q(-int(flag)) for flag in strict]
        homogenized.append([Q(0)]*(n+m)+[Q(-1)]); limits.append(Q(-1))
        optimum = self.feasibility(homogenized, limits, n+m+1)
        if optimum["status"] != "feasible":
            raise ArithmeticError("optimality alternatives contradict exact preceding witnesses")
        alpha = optimum["x"][-1]
        if alpha < 1:
            raise ArithmeticError("invalid homogenizing coordinate")
        point = [v/alpha for v in optimum["x"][:-1]]
        return self.result(dict(status="optimal", x=point[:n], y=point[n:], value=dot(c, point[:n], self.work)))

    def result(self, proof):
        return dict(status="certificate_returned", certificate=proof,
            mode="practical", search="restricted_flat_experts",
            calibration="direct_input_height_calibration", exact_recovery_lps=self.recovery_lps,
            recovery="exact_witness_early_return_without_circuit_claim",
            phase_ns=self.phase_ns,
            queries=self.queries, events=self.events, paper_algorithm_completed=False,
            strongly_polynomial_claim=False, gpu_work=self.gpu is not None)
