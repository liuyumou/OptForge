"""Independent mathematical and resource-boundary tests for SP-LP research."""
from fractions import Fraction as Q
import importlib.util
import itertools
import json
from pathlib import Path
import random
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "research/lp-sp-pricing/python"))
from sp_pricing.exact import Work, Limit, determinant, determinant_newton, encode, vertices, dot
from sp_pricing.lp import certificate
from sp_pricing.geometry import paired_space, LabelOracle
from sp_pricing.calibration import DirectCalibration, scaled_interval, paper_bounds
from sp_pricing.market import Market
from sp_pricing.gpu import accept_proposal
from sp_pricing.cells import count_and_moments
from sp_pricing.compression import homogeneous_round, OnlineCompression, Restart
from sp_pricing.recursive import investment_search, parameters
from sp_pricing.log_oracle import LogOracle

spec = importlib.util.spec_from_file_location("independent_sp_checker", ROOT / "tools/lp_sp_pricing_verify.py")
checker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(checker)

budget_spec = importlib.util.spec_from_file_location("study_budget", ROOT/"tools/lp_sp_pricing_budget.py")
budget = importlib.util.module_from_spec(budget_spec)
budget_spec.loader.exec_module(budget)


class ExactTests(unittest.TestCase):
    def test_isotropic_displacement_bound_agrees_with_dense_label_decisions(self):
        rng=random.Random(1903)
        for _ in range(6):
            work=Work(max_operations=5_000_000)
            c=[[Q(rng.randrange(-3,4)) for _ in range(4)] for _ in range(2)]
            cal=DirectCalibration(paired_space(c,work),work).query([Q(rng.randrange(-4,5),2) for _ in range(4)])
            dense=LabelOracle(cal['basis'],cal['H'],cal['epsilon'],work)
            analytic=LabelOracle(cal['basis'],cal['H'],cal['epsilon'],work,isotropic_error=cal['displacement_bound'])
            self.assertTrue(analytic.broadcast_negative)
            self.assertEqual(dense.labels()[0],analytic.labels()[0])

    def test_native_elimination_equals_python_on_rank_deficiency_and_augmented_systems(self):
        from sp_pricing.exact import rref
        rng=random.Random(22301)
        for m,n in ((8,8),(12,9),(9,15)):
            for k in range(5):
                a=[[Q(rng.randrange(-2,3),2**rng.randrange(8)) if rng.randrange(3)==0 else Q(0)
                    for _ in range(n)] for _ in range(m)]
                if k%2:a[-1]=a[0][:]
                work=Work(max_operations=5_000_000)
                self.assertEqual(rref(a,work,n-1),rref(a,work,n-1,use_native=False))

    def test_native_auxiliary_matches_python_exact_witnesses(self):
        from sp_pricing.native_auxiliary import NativeAuxiliary,LIBRARY
        from sp_pricing.lp import check
        if not LIBRARY.exists():self.skipTest('build native auxiliary library first')
        rng=random.Random(90112)
        for n in (1,2,3,5):
            a=[];b=[]
            for j in range(n):
                row=[Q(int(j==i)) for i in range(n)]
                a += [row,[-v for v in row]];b += [Q(2),Q(3)]
            a += [[Q(rng.randrange(-4,5),2**rng.randrange(4)) for _ in range(n)] for _ in range(4)]
            b += [Q(1,2)]*4
            with NativeAuxiliary(a,b,Work(max_operations=5_000_000)) as native:
                for k in range(16):
                    c=[Q(rng.randrange(-4,5),1000 if k%2 else 1) for _ in range(n)]
                    result=native.solve(c)
                    self.assertTrue(all(dot(row,result['x'])<=rhs for row,rhs in zip(a,b)))
                    self.assertEqual(dot(c,result['x']),result['value'])
                    expected=certificate(a,b,c,Work())
                    if result['status']=='feasible_target':self.assertGreaterEqual(result['value'],Q(1,4))
                    else:
                        check(a,b,c,result);self.assertEqual(result['value'],expected['value'])

    def test_reference_circuit_recovery_uses_sequential_original_restrictions(self):
        from sp_pricing.reference import recover_circuit
        from sp_pricing.exact import transpose
        from sp_pricing.geometry import restrict_space
        rng=random.Random(79051)
        work=Work(max_operations=10_000_000)
        for _ in range(10):
            c=[[Q(rng.randrange(-2,3)) for _ in range(4)] for _ in range(2)]
            def decide(space,n):
                cols=transpose(space,n)
                return [1 if certificate([[-v for v in col] for col in cols],
                            [-int(i==j) for j in range(n)],[Q(0)]*len(space),work)['status']=='optimal' else -1
                        for i in range(n)]
            side,vector=recover_circuit(c,3,decide,work,4)
            self.assertEqual(vector[3],1);self.assertTrue(all(v>=0 for v in vector))
            from sp_pricing.exact import nullspace
            selected=c if side==1 else nullspace(c,work,4)
            self.assertEqual(len(restrict_space(selected,[j for j,v in enumerate(vector) if not v],work,4)),1)

    def test_compressed_calibration_component_and_literal_refusal(self):
        from sp_pricing.reference import CompressedCalibration,exp2_small
        w=Work(max_operations=5_000_000,max_bits=65536)
        params=dict(eta=Q(1,2**40),T=2**100,M=8,D=20,R=10**20)
        cal=CompressedCalibration([[Q(1),Q(2)]],w,component_precision=32,component_parameters=params)
        for _ in range(20):
            try:
                result=cal.query([Q(1,2)]);break
            except Restart:pass
        else:self.fail('calibration did not stabilize')
        self.assertFalse(result['paper_constants'])
        self.assertEqual(result['pivots'],[0])
        self.assertEqual(result['basis'],[[Q(1),Q(1)]])
        q=exp2_small(Q(-1,2),40,w)
        self.assertLess(abs(q*q-Q(1,2)),Q(1,2**38))
        from sp_pricing.solver import PricingSolver
        result=PricingSolver(Work()).solve(dict(A=[[1]],b=[1],c=[1]),'paper_reference')
        self.assertEqual(result['reason'],'literal_parameter_bit_admission')
        self.assertTrue(result['implementation_complete'])
        self.assertFalse(result['paper_algorithm_completed'])

    def test_symbolic_compression_matches_explicit_rational_oracle(self):
        from sp_pricing.symbolic_compression import SymbolicCompression
        values=[Q(0),Q(1,3),Q(2)**100,Q(2)**100+Q(1,3),-Q(2)**100]
        def sign(a,coefficients):
            value=a+sum((c*values[i] for i,c in coefficients.items()),Q(0))
            return int(value>0)-int(value<0)
        symbolic=SymbolicCompression(sign,8,Q(1,256),20,Work(max_operations=5_000_000))
        explicit=OnlineCompression(lambda i:values[i],8,Q(1,256),20,Work(max_operations=5_000_000))
        for _ in range(20):
            try:
                for i in range(len(values)):
                    try:s=symbolic.request(i)
                    except Restart:
                        with self.assertRaises(Restart):explicit.request(i)
                        raise
                    e=explicit.request(i)
                    self.assertEqual(s['value'],e['value'])
                break
            except Restart:pass
        else:self.fail('compression never stabilized')
        self.assertGreater(symbolic.epoch,0)
        # The same interface also exercises real logarithms without converting
        # them to rational approximations in this deliberately small threshold.
        logs=LogOracle(lambda i:[Q(2)**80,Q(3)**60][i],Q(1,256),10,Work(max_bits=1000000))
        s=SymbolicCompression(logs.sign,2,Q(1,256),20,Work(max_bits=1000000))
        # Deliberately inconsistent tiny T cannot authorize enormous products.
        with self.assertRaises(Limit):s.request(0)

    def test_grouped_cells_match_explicit_experts_and_preserve_parent_wealth(self):
        from sp_pricing.grouped_market import Cells,Cell,Group,utilities
        work=Work(max_operations=20_000_000,seconds=60)
        counter=Cells(1,work)
        for group,history in [(Group(((0,1),(0,-1),(1,1),(1,-1))),[]),
                              (Group(((0,1),(0,-1),(1,1),(1,-1)),(0,(1,-1))),[[Q(1,2),Q(-1)]])]:
            prices=[Q(1,2),Q(-1,2)]
            refined=counter.refine(group,[Cell((),[Q(7),Q(2)])],prices,history)
            seen=set()
            for cell in refined:
                points=[x for x in itertools.product(range(-1,2),repeat=group.dimension)
                        if all((0 if i<0 else x[i])-(0 if j<0 else x[j])<=c for i,j,c in cell.constraints)]
                moment=counter.moments(group.dimension,cell.constraints)
                self.assertEqual(moment['count'],len(points))
                self.assertEqual(moment['sums'],[sum(x[j] for x in points) for j in range(group.dimension)])
                self.assertEqual(cell.wealth,[Q(7),Q(2)])
                maxima=set()
                for point in points:
                    self.assertNotIn(point,seen);seen.add(point)
                    values=utilities(group,point,prices,history)
                    maxima.add(tuple(i for i,v in enumerate(values) if v==max(values)))
                self.assertEqual(len(maxima),1)
            self.assertEqual(len(seen),3**group.dimension)

    def test_shared_tableau_objective_changes_and_target_exit(self):
        from sp_pricing.lp import free,check
        rng=random.Random(90215)
        for n in (1,2,4):
            a=[];b=[]
            for j in range(n):
                row=[Q(int(i==j)) for i in range(n)]
                a += [row,[-v for v in row]];b += [Q(2),Q(3)]
            a += [[Q(rng.randrange(-3,4)) for _ in range(n)] for _ in range(4)];b += [Q(2)]*4
            state={}
            for k in range(12):
                c=[Q(rng.randrange(-3,4)) for _ in range(n)]
                found=free(a,b,c,Work(),state=state,target=Q(1,4) if k%2 else None)
                if found['status']=='feasible_target':
                    self.assertGreaterEqual(dot(c,found['x']),Q(1,4))
                    self.assertTrue(all(dot(row,found['x'])<=rhs for row,rhs in zip(a,b)))
                else:
                    check(a,b,c,found)
                    self.assertEqual(found['value'],certificate(a,b,c,Work())['value'])

    def test_rounded_rational_ellipsoid_feasibility_and_one_dimensional_optimum(self):
        from sp_pricing.ellipsoid import explicit, feasible, lex_minimize
        work=Work(max_operations=20_000_000,max_bits=65536,seconds=90)
        box=explicit([[1,0],[-1,0],[0,1],[0,-1]],[1,-1,1,-1],2)
        self.assertTrue(feasible(box,work)["feasible"])
        empty=explicit([[1,0],[-1,0]],[0,-1],2)
        self.assertFalse(feasible(empty,work)["feasible"])
        line=explicit([[2],[-3]],[5,2],3)
        self.assertEqual(lex_minimize(line,work)["x"],[Q(-2,3)])
        triangle=explicit([[-1,0],[0,-1],[-1,-1]],[0,0,-1],2)
        self.assertEqual(lex_minimize(triangle,work)['x'],[Q(0),Q(1)])

    def test_grouped_market_exact_lexicographic_zero_guess_case(self):
        from sp_pricing.grouped_market import GroupedMarket,Group,Cell
        work=Work(max_operations=20_000_000,max_bits=1000000,seconds=60)
        market=GroupedMarket(1,0,0,work)
        # All guesses are exactly zero; this still exercises the real cell
        # separator, epigraph optimization and lexicographic face recovery.
        self.assertEqual(market.propose([]),[Q(0)])
        before=market.total();market.split_wealth()
        market.recombine([], [Q(0)], [1])
        self.assertLessEqual(market.total(),before)

    def test_sparse_quadratic_bound_and_products_match_dense_definition(self):
        rng = random.Random(9125)
        for _ in range(8):
            b = [[Q(rng.randrange(-2, 3)) if rng.randrange(3)==0 else Q(0) for _ in range(8)] for _ in range(3)]
            oracle = LabelOracle(b, Q(3), Q(1, 4096), Work())
            gram = sum((abs(sum((b[i][2*k]*b[j][2*k+1]+b[j][2*k]*b[i][2*k+1] for k in range(4)), Q(0))/2)
                        for i in range(3) for j in range(3)), Q(0))
            self.assertEqual(oracle.q_bound, 9*gram)
            x = [Q(rng.randrange(-3, 4), 2) for _ in range(3)]
            u = [Q(rng.randrange(-3, 4), 2) for _ in range(8)]
            self.assertEqual(oracle.multiply(x), [dot(col, x) for col in oracle.columns])
            self.assertEqual(oracle.residual(2, u), [row[5]-dot(row, u) for row in b])

    def test_calibration_elimination_equals_determinant_definition(self):
        rng = random.Random(62103)
        for _ in range(12):
            w = Work(max_operations=5_000_000)
            c = [[Q(rng.randrange(-4, 5)) for _ in range(4)] for _ in range(2)]
            direct = DirectCalibration(paired_space(c, w), w)
            prices = [Q(rng.randrange(-8, 9), 2) for _ in range(4)]
            fast = direct._query(prices, 64)
            reference = direct._query(prices, 64, use_elimination=False)
            self.assertEqual(fast, reference)

    def test_calibration_tiny_scaled_coefficients_do_not_allocate_huge_powers(self):
        lo, hi = scaled_interval(Q(3), Q(-10**9), 64, Work())
        self.assertLessEqual(lo, 0)
        self.assertGreater(hi, 0)
        work = Work(max_operations=5_000_000)
        direct = DirectCalibration(paired_space([[Q(1), Q(1)]], work), work)
        answer = direct.query([Q(10**6), Q(-10**6)])
        self.assertLessEqual(answer["entry_error"], Q(1, 2**64))

    def test_integer_separator_equals_fraction_definition(self):
        rng = random.Random(99319)
        market = Market(3, 7, Work(max_operations=5_000_000), extra=32)
        for expert in market.experts:
            expert.weight = Q(rng.randrange(1, 20), rng.randrange(1, 12))
        for _ in range(30):
            prices = [Q(rng.randrange(-30, 31), rng.randrange(1, 9)) for _ in range(3)]
            value, gradient, intercept = Q(0), [Q(0)]*3, Q(0)
            for expert in market.experts:
                utilities = [Q(0)]+[a-h*prices[i] for i, h, a in expert.options]
                best = max(utilities); first = utilities.index(best)
                value += expert.weight*best
                if first:
                    i, h, a = expert.options[first-1]
                    gradient[i] -= h*expert.weight; intercept += a*expert.weight
            self.assertEqual(market.evaluate(prices), (value, gradient, intercept))

    def test_native_flow_matches_exact_lexicographic_market(self):
        from sp_pricing.flow_market import DEFAULT_LIBRARY
        if not DEFAULT_LIBRARY.exists():
            self.skipTest("optional CPU market worker not built")
        rng = random.Random(731)
        for n in (1, 2, 3):
            for seed in range(4):
                market = Market(n, 2+seed, Work(max_operations=10_000_000, seconds=30), extra=4, seed=seed)
                for expert in market.experts:
                    expert.weight = Q(rng.randrange(1, 9), 16)
                flow, proof = market.minimize(backend="flow")
                oracle, reference = market.minimize(backend="cuts")
                self.assertEqual(flow, oracle)
                self.assertEqual(proof["value"], reference["value"])

    def test_failed_reservations_retain_full_charge_and_unsettled_jobs_close_admission(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            resources = base/"resources"
            resources.mkdir()
            reservation = resources/"example.reservation.json"
            reservation.write_text(json.dumps(dict(phase="admission", cpu_ns=600, gpu_ns=150)))
            with self.assertRaises(RuntimeError):
                budget.accounting(base)
            settlement = resources/"example.settlement.json"
            receipt = dict(status="refused", cpu_ns=600, gpu_ns=150, cleanup_empty=True, overrun=False)
            settlement.write_text(json.dumps(receipt))
            self.assertEqual(budget.accounting(base)["admission"], 600)
            self.assertEqual(budget.accounting(base, True)["admission"], 150)
            receipt["cleanup_empty"] = False
            settlement.write_text(json.dumps(receipt))
            with self.assertRaises(RuntimeError):
                budget.accounting(base)

    def test_market_duplicate_aggregation_retains_initial_mass(self):
        market = Market(1, 2, Work(), extra=4096, seed=91)
        self.assertLess(len(market.experts), market.initial_expert_count)
        self.assertEqual(sum(e.weight for e in market.experts), market.initial_expert_count)

    def test_practical_end_to_end_three_outcomes_are_independently_checked(self):
        from sp_pricing.solver import PricingSolver
        models = [dict(A=[[0]], b=[-1], c=[1]), dict(A=[], b=[], c=[1]), dict(A=[], b=[], c=[0])]
        for model, expected in zip(models, ("infeasible", "unbounded", "optimal")):
            result = PricingSolver(Work(max_operations=5_000_000, seconds=30), extra_experts=0).solve(model)
            audit = checker.verify(model, encode(result))
            self.assertTrue(audit["accepted"])
            self.assertEqual(audit["outcome"], expected)

    def test_sparse_input_is_not_assumed_to_have_a_sparse_nullspace(self):
        from sp_pricing.solver import PricingSolver
        with self.assertRaisesRegex(Limit, "paired_basis_fill_limit"):
            PricingSolver().feasibility([[] for _ in range(1000)], [Q(0)]*1000, 0)

    def test_log_proxy_and_exact_symbolic_cancellation(self):
        values = {"small": Q(1, 8), "large": Q(3*2**100), "square": Q(9*2**200)}
        oracle = LogOracle(values.__getitem__, Q(1, 256), 32, Work())
        self.assertEqual(oracle.proxy("small")["value"], -3)
        self.assertEqual(oracle.sign(0, {"large": 2, "square": -1}), 0)
        self.assertEqual(oracle.sign(1, {"large": 2, "square": -1}), 1)
        self.assertEqual(oracle.sign(-1, {"large": 2, "square": -1}), -1)

    def test_literal_tree_refuses_before_query_and_component_preserves_wealth(self):
        class ZeroMarket:
            expert_count = 2
            def propose(self, history, wealth):
                return [Q(0)]
            def gains(self, history, prices, feedback):
                return [0, -1]
        calls = []
        labels = lambda p: calls.append(p) or [1]
        with self.assertRaises(Limit):
            investment_search(1, 1, ZeroMarket(), labels, Work())
        self.assertFalse(calls)
        result = investment_search(1, 1, ZeroMarket(), labels, Work(),
            component_parameters=dict(depth=1, branching=3, root_branching=3))
        self.assertEqual(result["prices"], [0])
        self.assertEqual(result["queries"], 3)
        self.assertLessEqual(sum(result["wealth"]), 2)
        self.assertGreater(parameters(100, 1)["leaf_probes"], 10**140)

    def test_cell_counts_against_independent_exhaustive_enumeration(self):
        rng = random.Random(2391)
        for n in (1, 2, 3):
            for _ in range(8):
                constraints = [(rng.randrange(-1, n), rng.randrange(-1, n), rng.randrange(-3, 4)) for _ in range(4)]
                points = [p for p in itertools.product(range(-2, 3), repeat=n)
                          if all((p[i] if i >= 0 else 0)-(p[j] if j >= 0 else 0) <= c for i, j, c in constraints)]
                result = count_and_moments(n, 2, constraints, Work(max_operations=2_000_000))
                self.assertEqual(result["count"], len(points))
                self.assertEqual(result["sums"], [sum(p[i] for p in points) for i in range(n)])
        large = count_and_moments(2, 10**9, [], Work())
        self.assertEqual(large, dict(count=(2*10**9+1)**2, sums=[0, 0]))

    def test_common_scale_rounding_preserves_all_small_forms(self):
        values = [Q(1234567, 13), Q(-33221, 17), Q(9, 23)]
        rounded = homogeneous_round(values, 3, Work(max_operations=5_000_000, seconds=60))
        sign = lambda v: int(v > 0)-int(v < 0)
        for form in itertools.product(range(-3, 4), repeat=3):
            if sum(map(abs, form)) <= 3:
                self.assertEqual(sign(dot(form, values)), sign(dot(form, rounded)))

    def test_compression_restart_invalidates_previous_answers(self):
        proxies = {"small": Q(1), "large": Q(10**20), "near": Q(10**20+1)}
        compression = OnlineCompression(proxies.__getitem__, 3, Q(1, 64), 8, Work(max_operations=5_000_000))
        old = compression.request("small")
        with self.assertRaises(Restart):
            compression.request("large")
        with self.assertRaises(ValueError):
            compression.validate_epoch(old)
        a, b = compression.request("large"), compression.request("near")
        self.assertLess(a["value"], b["value"])

    def test_approximate_proposals_need_exact_witnesses(self):
        w = Work()
        oracle = LabelOracle([[Q(0), Q(1), Q(1), Q(0)]], Q(2), Q(1, 2048), w)
        positive = accept_proposal(oracle, 0, [1.0], [0.0]*4)
        self.assertEqual(positive["established"], {0: 1, 1: -1})
        negative = accept_proposal(oracle, 1, [0.0], [0.0]*4)
        self.assertEqual(negative["established"], {1: -1})
        failed = accept_proposal(oracle, 0, [float("nan")], [0.0]*4)
        self.assertFalse(failed["accepted"])
        unresolved = accept_proposal(oracle, 0, [0.0], [0.0]*4)
        self.assertFalse(unresolved["accepted"])

    def test_label_broadcast_and_exact_threshold(self):
        work = Work()
        w = paired_space([[Q(1), Q(1)]], work)
        answer = DirectCalibration(w, work).query([Q(0), Q(0)])
        oracle = LabelOracle(answer["basis"], answer["H"], answer["epsilon"], work)
        labels, proofs = oracle.labels(broadcast=True)
        self.assertEqual(labels, [1, 1])
        self.assertLessEqual(oracle.calls, 2)
        self.assertTrue(proofs)
        with self.assertRaises(ValueError):
            oracle.labels(expected_epoch=9)

    def test_reciprocal_calibration_half_integral_prices(self):
        work = Work()
        w = paired_space([[Q(1, 16), Q(1)]], work)
        direct = DirectCalibration(w, work)
        answer = direct.query([Q(-7, 2), Q(1, 2)])
        oracle = LabelOracle(answer["basis"], answer["H"], answer["epsilon"], work)
        self.assertTrue(oracle.broadcast_negative)
        self.assertEqual(oracle.labels()[0], [1, 1])
        lo, hi = scaled_interval(Q(1), Q(1, 2), 64, work)
        self.assertLessEqual(lo*lo, 2)
        self.assertGreaterEqual(hi*hi, 2)

    def test_market_minimizer_and_adversarial_ties_preserve_wealth(self):
        for z in itertools.product((-1, 1), repeat=2):
            market = Market(2, 2, Work(max_operations=2_000_000), extra=4, seed=21)
            prices, proof = market.minimize()
            self.assertTrue(proof["exact"])
            receipt = market.update(prices, list(z))
            self.assertLessEqual(receipt["after"], receipt["before"])

    def test_paper_bound_is_symbolic_before_allocation(self):
        bound = paper_bounds(100)
        self.assertEqual(bound["precision_bits"], 100000000)
        self.assertEqual(bound["tree_depth"], 25)
        self.assertGreater(bound["demand_bound_bits_upper"], bound["precision_bits"])

    def test_newton_minors_against_permutation_definition(self):
        rng = random.Random(381)
        for n in range(5):
            for _ in range(5):
                a = [[Q(rng.randrange(-3, 4), rng.randrange(1, 4)) for _ in range(n)] for _ in range(n)]
                expected = Q(0)
                for p in itertools.permutations(range(n)):
                    sign = (-1)**sum(p[i] > p[j] for i in range(n) for j in range(i+1, n))
                    value = Q(sign)
                    for i in range(n):
                        value *= a[i][p[i]]
                    expected += value
                self.assertEqual(determinant(a, Work()), expected)
                self.assertEqual(determinant_newton(a, Work()), expected)

    def test_limits_are_not_mathematical_statuses(self):
        with self.assertRaises(Limit):
            Work(max_bits=10).power2(100000000)
        with self.assertRaises(Limit):
            determinant([[Q(2**20)]], Work(max_bits=10))

    def test_three_alternatives(self):
        models = [
            (dict(A=[[1], [-1]], b=[2, 1], c=[1]), "optimal"),
            (dict(A=[[1], [-1]], b=[-2, 1], c=[1]), "infeasible"),
            (dict(A=[[-1]], b=[0], c=[1]), "unbounded"),
            (dict(A=[], b=[], c=[1, -1]), "unbounded"),
            (dict(A=[[]], b=[-1], c=[]), "infeasible"),
            (dict(A=[[]], b=[0], c=[]), "optimal"),
        ]
        for model, outcome in models:
            with self.subTest(outcome=outcome, model=model):
                result = certificate(model["A"], model["b"], model["c"], Work())
                self.assertEqual(result["status"], outcome)
                self.assertTrue(checker.verify(model, encode(result))["accepted"])

    def test_random_bounded_optima_against_vertex_enumeration(self):
        rng = random.Random(972)
        for n in (1, 2, 3):
            for _ in range(10):
                a, b = [], []
                for j in range(n):
                    row = [Q(int(i == j)) for i in range(n)]
                    a += [row, [-v for v in row]]
                    b += [Q(3), Q(3)]
                a += [[Q(rng.randrange(-4, 5)) for _ in range(n)] for _ in range(2)]
                b += [Q(2), Q(4)]
                c = [Q(rng.randrange(-4, 5)) for _ in range(n)]
                candidates = list(vertices(a, b, Work()))
                expected = max(dot(c, x) for x in candidates)
                result = certificate(a, b, c, Work())
                self.assertEqual(result["value"], expected)
                self.assertTrue(checker.verify(encode(dict(A=a, b=b, c=c)), encode(result))["accepted"])

    def test_degenerate_lexicographic_face(self):
        a = [[1, 0], [-1, 0], [0, 1], [0, -1], [1, 0]]
        b = [1, 0, 1, 0, 1]
        result = certificate(a, b, [1, 0], Work(), lexicographic=True)
        self.assertEqual(result["x"], [1, 0])

    def test_independent_checker_rejects_tampered_and_missing_witnesses(self):
        model = dict(A=[[1], [-1]], b=[2, 0], c=[1])
        result = encode(certificate(model["A"], model["b"], model["c"], Work()))
        result["x"] = [1]
        self.assertFalse(checker.verify(model, result)["accepted"])
        self.assertFalse(checker.verify(model, dict(status="deadline"))["accepted"])
        result = encode(certificate(model["A"], model["b"], model["c"], Work()))
        result["value"] = 900
        self.assertFalse(checker.verify(model, result)["accepted"])
        for bad in (True, 1.5, "1.5", "+-1"):
            with self.assertRaises(ValueError):
                checker.number(dict(numerator=bad, denominator=2))


if __name__ == "__main__":
    unittest.main()
