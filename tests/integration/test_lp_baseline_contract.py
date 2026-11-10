"""SPEC-0022 new CPU contracts only; no solver imports, device jobs or old gates."""

import copy
from fractions import Fraction
import json
from pathlib import Path
import struct
import sys
import tempfile
import unittest

from jsonschema import ValidationError

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
import lp_baseline_contract as contract

ERRORS = (ValueError, ValidationError)


def original():
    return json.loads((ROOT / "examples/lp-model-v1.json").read_text())


def raw(doc):
    return json.dumps(doc, sort_keys=True).encode()


def model():
    return contract.canonicalize(raw(original()))


def endpoint(m):
    ref = {"path": "fixtures/explicitly-synthetic.json", "sha256": "a" * 64}
    return dict(schema_version=1, kind="lp-baseline-endpoint", evidence_kind="fixture",
                model_sha256=contract.sha256(raw(m)), original_sha256=m["original_sha256"],
                proposal_sha256="b" * 64, configuration_id="cuopt-pdlp-double", solver="cuopt",
                solver_version="26.10.0", adapter=ref.copy(), environment=ref.copy(),
                requested_device="gpu", executed_device="gpu", device_uuid="GPU-fixture",
                gpu_evidence=ref.copy(), algorithm_requested="pdlp", algorithm_executed="pdlp",
                transport="completed", native_status="optimal", variable_ids=m["variable_ids"],
                row_ids=m["row_ids"], primal=[.5, 1.0], dual=[-1.0],
                dual_convention="original_units_min_lower_positive", native_reduced_costs=[0.0, -2.0],
                checker={"state": "not_run", "receipt": None}, elapsed_ns=100,
                native_solve_ns=60, certificate_ns=None, limitations=["synthetic checker not run"])


class CanonicalContracts(unittest.TestCase):
    def test_binary64_values_sense_offset_and_input_not_mutated(self):
        d = original()
        d["variables"].reverse()
        d["objective"].update(sense="maximize", offset=7.125)
        d["constraints"][0]["terms"][0]["coefficient"] = -0.0
        source = raw(d)
        result = contract.canonicalize(source)
        self.assertEqual(result["original_sha256"], contract.sha256(source))
        self.assertEqual(result["variable_ids"], [0, 1])
        self.assertEqual(result["sense"], "maximize")
        self.assertEqual(result["offset"], 7.125)
        self.assertEqual(struct.pack("!d", result["values"][0]), struct.pack("!d", -0.0))
        self.assertEqual(source, raw(d))

    def test_ranged_fixed_free_and_empty_shapes(self):
        d = original()
        d["variables"][0].update(lower={"kind": "negative_infinity"}, upper={"kind": "positive_infinity"})
        d["variables"][1].update(lower={"kind": "finite", "value": 1}, upper={"kind": "finite", "value": 1})
        d["constraints"][0]["lower"] = {"kind": "finite", "value": -3}
        d["constraints"].append({"id": 8, "lower": {"kind": "finite", "value": 0},
                                 "upper": {"kind": "finite", "value": 0}, "terms": []})
        m = contract.canonicalize(raw(d))
        self.assertEqual(m["variable_lower"], [None, 1])
        self.assertEqual(m["row_lower"], [-3, 0])
        d["variables"] = []
        d["constraints"] = []
        d["objective"]["terms"] = []
        self.assertEqual(contract.canonicalize(raw(d))["column_pointers"], [0])

    def test_csr_permutation_preserves_rows_and_value_bits(self):
        d = original()
        d["constraints"].append({"id": 4, "lower": {"kind": "finite", "value": -1},
                                 "upper": {"kind": "positive_infinity"},
                                 "terms": [{"variable_id": 1, "coefficient": -0.0}]})
        offsets, indices, values = contract.csr(contract.canonicalize(raw(d)))
        self.assertEqual((offsets, indices), ([0, 2, 3], [0, 1, 1]))
        self.assertEqual(struct.pack("!d", values[-1]), struct.pack("!d", -0.0))

    def test_rejects_duplicate_ids_terms_unknowns_and_noncontinuous(self):
        changes = [lambda d: d["variables"].append(copy.deepcopy(d["variables"][0])),
                   lambda d: d["constraints"].append(copy.deepcopy(d["constraints"][0])),
                   lambda d: d["constraints"][0]["terms"].append(copy.deepcopy(d["constraints"][0]["terms"][0])),
                   lambda d: d["objective"]["terms"].append(copy.deepcopy(d["objective"]["terms"][0])),
                   lambda d: d["objective"]["terms"][0].update(variable_id=999),
                   lambda d: d["variables"][0].update(domain="integer"),
                   lambda d: d["variables"][0].update(id=True),
                   lambda d: d.update(unrecognized="field")]
        for change in changes:
            with self.subTest(change=change):
                d = original(); change(d)
                with self.assertRaises(ERRORS): contract.canonicalize(raw(d))

    def test_bound_orientation_reversal_and_inexact_integer_refuse(self):
        for value in [{"kind": "positive_infinity"}, {"kind": "finite", "value": 2},
                      {"kind": "finite", "value": 2**53 + 1}]:
            d = original(); d["variables"][0]["lower"] = value
            with self.assertRaises(ERRORS): contract.canonicalize(raw(d))

    def test_nonfinite_duplicate_json_and_numeric_boolean_refuse(self):
        for source in [b'{"x":1,"x":2}', b'{"x":NaN}', b'{"x":1e999}']:
            with self.assertRaises(ValueError): contract.canonicalize(source)
        for value in [True, float("nan"), float("inf")]:
            d = original(); d["objective"]["offset"] = value
            with self.assertRaises(ERRORS): contract.canonicalize(raw(d))

    def test_tiny_and_large_finite_inputs_are_not_silently_clipped(self):
        d = original()
        d["objective"]["terms"][0]["coefficient"] = 1e-12
        d["variables"][0]["upper"]["value"] = 1e30
        m = contract.canonicalize(raw(d))
        self.assertEqual(m["objective"][0], 1e-12)
        self.assertEqual(m["variable_upper"][0], 1e30)
        # Vendor-specific import refusal belongs to the later adapter, not this conversion.

    def test_csc_cross_field_corruption_refuses(self):
        for key, value in [("column_pointers", [0, 2]), ("column_pointers", [0, 2, 1]),
                           ("row_indices", [0, 9]), ("values", [1]), ("objective", []),
                           ("variable_ids", [1, 0]), ("variable_ids", [0.0, 1])]:
            m = model(); m[key] = value
            with self.subTest(key=key, value=value), self.assertRaises(ERRORS): contract.validate_model(m)
        m = model(); m.update(column_pointers=[0, 2, 2], row_indices=[0, 0])
        with self.assertRaisesRegex(ValueError, "duplicate"): contract.validate_model(m)

    def test_dual_convention_with_independent_exact_min_max_witness(self):
        # max x+3y+7, x+y<=3/2, 0<=x,y<=1: x=1/2,y=1, objective=21/2.
        x = [Fraction(1, 2), Fraction(1)]
        for sense, costs, native_y, offset in [("minimize", [-1, -3], [-1], 0),
                                                ("maximize", [1, 3], [1], 7)]:
            sigma = 1 if sense == "minimize" else -1
            y = Fraction(contract.normalize_original_sense_dual(native_y, sense)[0])
            reduced = [sigma * c - y for c in costs]
            lower_bound = sigma * offset + y * Fraction(3, 2) + sum(min(Fraction(0), z) for z in reduced)
            normalized_objective = sigma * (offset + sum(c * v for c, v in zip(costs, x)))
            self.assertEqual(lower_bound, normalized_objective)


class EndpointContracts(unittest.TestCase):
    def validate(self, e, m):
        return contract.validate_endpoint(e, m, contract.sha256(raw(m)))

    def test_native_optimal_does_not_supply_a_certificate(self):
        m = model(); e = endpoint(m)
        self.validate(e, m)
        self.assertEqual(e["checker"]["state"], "not_run")
        e["dual"] = None
        self.validate(e, m)
        e["checker"] = {"state": "accepted", "receipt": e["adapter"]}
        with self.assertRaisesRegex(ValueError, "incomplete"): self.validate(e, m)

    def test_structurally_complete_limit_endpoint_still_needs_receipt_verification(self):
        m = model(); e = endpoint(m)
        e.update(native_status="limit", certificate_ns=20)
        e["checker"] = {"state": "accepted", "receipt": e["adapter"]}
        self.validate(e, m)  # This validates no numerical claim and does not read the synthetic receipt.
        e["transport"] = "timeout"
        with self.assertRaisesRegex(ValueError, "incomplete"): self.validate(e, m)

    def test_endpoint_substitution_dimensions_and_nonfinite_refuse(self):
        for key, value in [("original_sha256", "c" * 64), ("model_sha256", "c" * 64),
                           ("row_ids", [7]), ("primal", [1]), ("dual", [float("nan")]),
                           ("native_reduced_costs", []), ("native_solve_ns", 101), ("elapsed_ns", 100.0)]:
            m = model(); e = endpoint(m); e[key] = value
            with self.subTest(key=key), self.assertRaises(ERRORS): self.validate(e, m)

    def test_gpu_confirmation_requires_evidence(self):
        m = model(); e = endpoint(m); e["gpu_evidence"] = None
        with self.assertRaisesRegex(ValueError, "GPU"): self.validate(e, m)
        e["executed_device"] = "unknown"
        self.validate(e, m)  # Unknown is retained, never upgraded to GPU.

    def test_unavailable_and_infeasible_are_not_certified_timings(self):
        m = model(); e = endpoint(m)
        e.update(transport="unavailable", executed_device="not_run", native_status="not_run",
                 primal=None, dual=None, elapsed_ns=None, native_solve_ns=None,
                 device_uuid=None, gpu_evidence=None, native_reduced_costs=None)
        self.validate(e, m)
        e["elapsed_ns"] = 0
        with self.assertRaisesRegex(ValueError, "timing"): self.validate(e, m)
        e = endpoint(m); e["native_status"] = "infeasible"
        self.validate(e, m)
        e["checker"] = {"state": "accepted", "receipt": e["adapter"]}; e["certificate_ns"] = 10
        with self.assertRaisesRegex(ValueError, "contradictory"): self.validate(e, m)

    def test_unknown_fields_receipt_state_and_missing_reason_refuse(self):
        for mutate in [lambda e: e.update(unknown=0),
                       lambda e: e["checker"].update(receipt=e["adapter"]),
                       lambda e: e.update(limitations=[])]:
            m = model(); e = endpoint(m); mutate(e)
            with self.assertRaises(ERRORS): self.validate(e, m)


class ProposalContracts(unittest.TestCase):
    def setUp(self):
        self.p = json.loads((ROOT / "benchmarks/configs/lp-external-baseline-proposal-v1.json").read_text())

    def test_exact_grid_two_phase_arithmetic_and_no_execution(self):
        r = contract.validate_proposal(self.p)
        self.assertEqual(r["screening_jobs"], 240)
        self.assertFalse(r["execution_authorized"])
        for prefix, cpu, gpu in [("A-", 6040, 480), ("B-", 58600, 10080)]:
            phases = [p for p in self.p["phases"] if p["id"].startswith(prefix)]
            self.assertEqual(sum(p["cpu_seconds"] for p in phases), cpu)
            self.assertEqual(sum(p["gpu_seconds"] for p in phases), gpu)

    def test_order_is_permutation_stable_and_complete(self):
        before = list(contract.screening_jobs(self.p))
        self.p["instances"].reverse(); self.p["configurations"].reverse()
        self.assertEqual(before, list(contract.screening_jobs(self.p)))
        self.assertEqual(len({(j["instance_id"], j["configuration_id"], j["repetition"]) for j in before}), 240)
        self.assertEqual(sum(j["gpu"] for j in before), 168)

    def test_budget_changes_and_authority_escalation_refuse(self):
        changes = [lambda p: p.update(execution_authorized=True), lambda p: p.update(held_out_access=True),
                   lambda p: p.update(total_gpu_seconds=10561), lambda p: p.update(repetitions=4),
                   lambda p: p["phases"][2].update(cpu_seconds=2399),
                   lambda p: p["phases"][5].update(gpu_jobs=167),
                   lambda p: p["instances"].append(copy.deepcopy(p["instances"][0]))]
        for change in changes:
            p = copy.deepcopy(self.p); change(p)
            with self.subTest(change=change), self.assertRaises(ERRORS): contract.validate_proposal(p)

    def test_solver_parameter_drift_and_false_precision_refuse(self):
        changes = [lambda c: c["parameters"].update(pdlp_precision=0),
                   lambda c: c["parameters"].update(absolute_gap_tolerance=1e-4),
                   lambda c: c["parameters"].update(method=True),
                   lambda c: c["parameters"].update(presolve=2),
                   lambda c: c["parameters"].update(typo_parameter=1),
                   lambda c: c.update(version="unfrozen"), lambda c: c.update(gpu=False)]
        for change in changes:
            p = copy.deepcopy(self.p); c = next(c for c in p["configurations"] if c["id"] == "cuopt-pdlp-double"); change(c)
            with self.assertRaises(ERRORS): contract.validate_proposal(p)

    def test_reference_hash_and_symlink_escape_refuse(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); (root / "a.txt").write_bytes(b"original")
            ref = {"path": "a.txt", "sha256": contract.sha256(b"original")}
            self.assertEqual(contract.checked_reference(ref, root), b"original")
            (root / "a.txt").write_bytes(b"changed")
            with self.assertRaisesRegex(ValueError, "hash"): contract.checked_reference(ref, root)
            (root / "outside").symlink_to(root.parent, target_is_directory=True)
            for path in ["../escape", "outside/escape", "/absolute"]:
                with self.assertRaisesRegex(ValueError, "path"):
                    contract.checked_reference({"path": path, "sha256": "a" * 64}, root)


if __name__ == "__main__":
    unittest.main()
