"""CPU admission tests; do not imply runtime or device acceptance."""

import ast
import copy
import json
import subprocess
import tempfile
from fractions import Fraction
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
import lp_expansion_candidate as arithmetic
import lp_state_candidate as candidate
import lp_state_oracle as oracle
import lp_state_admission as admission


class StateAdmissionTests(unittest.TestCase):
    def test_duplicate_and_boolean_evidence_fields_fail_before_private_files(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "admission.json"
            path.write_text('{"schema_version":1,"schema_version":1}')
            with self.assertRaisesRegex(ValueError, "duplicate admission"):
                admission.verify_admission(path)
        # Valid structural header; no private archive is needed to reject types.
        record = dict(schema_version=1, identity="gpup-state-resource-admission-v1",
                      status="refused_resource", cpu_counts=dict(integer_cases=192, fma_cases=270, update_cases=64),
                      fixture_sha256="0"*64, source_sha256="0"*64, host_source_sha256="0"*64,
                      host_binary_sha256="0"*64, image_sha256="0"*64, nvcc_version="test",
                      compiler_command=[], kernels={name:dict(registers=255, stack_bytes=152,
                      local_bytes=0, shared_bytes=0, spill_store_bytes=296, spill_load_bytes=152) for name in admission.KERNELS},
                      gpu_executed=False, gpu_seconds=0, solver_implemented=False, full_controller_accepted=False,
                      primary_attempts=0, planned_primary_attempts=96, planned_profiles=12,
                      files={name:"0"*64 for name in admission.FROZEN_FILES})
        admission.validate_record_header(record)
        for key in ["schema_version", "gpu_seconds", "primary_attempts", "planned_primary_attempts", "planned_profiles"]:
            malformed = copy.deepcopy(record);malformed[key] = False
            with self.assertRaisesRegex(ValueError, "integer field"):
                admission.validate_record_header(malformed)
        malformed = copy.deepcopy(record);malformed["cpu_counts"]["fma_cases"] = True
        with self.assertRaisesRegex(ValueError, "count field"):
            admission.validate_record_header(malformed)
        malformed = copy.deepcopy(record);malformed["kernels"][admission.KERNELS[0]]["local_bytes"] = False
        with self.assertRaisesRegex(ValueError, "resource integer field"):
            admission.validate_record_header(malformed)

    def test_partial_resource_failure_cannot_be_promoted(self):
        inventory = {name:dict(status="fits_resource_gate", reasons=[], forbidden_instructions=[]) for name in admission.KERNELS}
        self.assertEqual(admission.admission_status(inventory), "resource_gate_only_passed")
        inventory["state_integer_p64"].update(status="refused", reasons=["register_limit"])
        self.assertEqual(admission.admission_status(inventory), "partial_refusal")
        inventory["state_integer_p64"]["forbidden_instructions"] = ["DFMA"]
        self.assertEqual(admission.admission_status(inventory), "refused_instruction")

    def test_frozen_transcendental_candidate_is_reexecuted(self):
        document = admission.read_document(admission.FIXTURE)
        self.assertEqual(admission.verify_transcendentals(ROOT / "tools", document), 48)
        with tempfile.TemporaryDirectory() as temporary:
            frozen = Path(temporary)
            for name in ("lp_expansion_candidate.py", "lp_state_candidate.py"):
                (frozen / name).write_bytes((ROOT / "tools" / name).read_bytes())
            # The current checkout remains correct. Only the archive candidate
            # is changed; verification must execute and reject that candidate.
            with (frozen / "lp_state_candidate.py").open("a") as output:
                output.write("\ndef exponential(*args, **kwargs):\n    return Rounded()\n")
            with self.assertRaisesRegex(ValueError, "transcendental result differs"):
                admission.verify_transcendentals(frozen, document)

    def test_missing_frozen_source_inventory_refuses_before_private_files(self):
        summary = admission.read_document(ROOT / "docs/benchmarks/data/state/admission-v1.json")
        record = {key: value for key, value in summary.items()
                  if key not in {"admission_sha256", "evidence_directory", "resource_limit"}}
        record.update(compiler_command=[], files={name:"0"*64 for name in admission.FROZEN_FILES})
        admission.validate_record_header(record)
        for name in admission.FROZEN_FILES:
            malformed = copy.deepcopy(record)
            del malformed["files"][name]
            with self.assertRaisesRegex(ValueError, "file inventory"):
                admission.validate_record_header(malformed)

    def test_frozen_independent_fixture_and_transcendental_results(self):
        path = ROOT / "tests/regression/lp-state-admission-v1.json"
        self.assertEqual(path.read_text(), admission.encoded(admission.fixture()))
        document = json.loads(path.read_text())
        self.assertEqual({key: len(document[key]) for key in ["integer_cases", "fma_cases", "update_cases", "transcendental_cases"]},
                         dict(integer_cases=192, fma_cases=270, update_cases=64, transcendental_cases=48))
        formats = {"matched-fp64": arithmetic.BINARY64, "compensated-pair": candidate.PAIR48, "expansion64": arithmetic.EXPANSION64}
        for case in document["transcendental_cases"]:
            value = arithmetic.load_rounded(case["input"])
            function = candidate.logarithm if case["operation"] == "ln" else candidate.exponential
            self.assertEqual(function(value, formats[case["format"]]).document(), case["result"])

    def test_exact_probe_cpp_matches_independent_integer_fraction_fixture(self):
        with tempfile.TemporaryDirectory() as temporary:
            binary = Path(temporary) / "integer-host"
            subprocess.run(["g++", "-O2", "-Werror", "-Wno-unknown-pragmas", "-std=c++17", str(admission.HARNESS), "-o", str(binary)], check=True, capture_output=True, timeout=120)
            fixture = json.loads(admission.FIXTURE.read_text())
            self.assertEqual(admission.verify_host(binary, fixture), dict(integer_cases=192, fma_cases=270, update_cases=64))
            corrupted = copy.deepcopy(fixture)
            corrupted["fma_cases"][0]["result"]["coefficient"] -= 1
            with self.assertRaisesRegex(ValueError, "independent integer/Fraction"):
                admission.verify_host(binary, corrupted)

    def test_resource_gate_checks_spills_and_registers_even_without_local_bytes(self):
        resources, compiler, sass = [], [], []
        for name in admission.KERNELS:
            full = "full_fma" in name
            registers, stack, stores, loads = (255, 152, 296, 152) if full else (76, 0, 0, 0)
            resources.append(f"Function {name}:\n REG:{registers} STACK:{stack} SHARED:0 LOCAL:0")
            compiler.append(f"Function properties for {name}\n {stack} bytes stack frame, {stores} bytes spill stores, {loads} bytes spill loads")
            sass.append(f"Function : {name}\n /*0000*/ IADD3 R0, R1, R2, RZ;")
        audit = admission.resource_audit("\n".join(resources), "\n".join(compiler), "\n".join(sass))
        self.assertEqual(admission.admission_status(audit), "refused_resource")
        self.assertEqual(audit["state_full_fma_p64"]["reasons"], ["register_limit", "compiler_spills"])
        with self.assertRaisesRegex(ValueError, "incomplete generated-code"):
            admission.resource_audit("\n".join(resources[:-1]), "\n".join(compiler), "\n".join(sass))
        with self.assertRaisesRegex(ValueError, "stack mismatch"):
            admission.resource_audit("\n".join(resources), "\n".join(compiler).replace("152 bytes stack frame", "0 bytes stack frame"), "\n".join(sass))
        with self.assertRaisesRegex(ValueError, "empty instruction"):
            admission.resource_audit("\n".join(resources), "\n".join(compiler), "\n".join(sass).replace("IADD3", ""))
        altered = "\n".join(sass).replace("IADD3", "DFMA")
        audit = admission.resource_audit("\n".join(resources), "\n".join(compiler), altered)
        self.assertEqual(admission.admission_status(audit), "refused_instruction")
        for predicate in ["@UP0", "@!UP0", "@P0", "@!P0", "@PT", "@UPT"]:
            for opcode in ["DFMA", "F2F.F64.F32", "CALL.REL.NOINC", "DMMA.884"]:
                altered = "\n".join(sass) + f"\n /*0010*/ {predicate} {opcode} R0, R1, R2, R3;"
                audit = admission.resource_audit("\n".join(resources), "\n".join(compiler), altered)
                self.assertEqual(admission.admission_status(audit), "refused_instruction")
        for instruction in ["@UNKNOWN DFMA R0, R1, R2, R3;", "DFMA R0, R1", "???;"]:
            with self.assertRaisesRegex(ValueError, "unparsed instruction"):
                admission.resource_audit("\n".join(resources), "\n".join(compiler),
                                         "\n".join(sass) + "\n /*0010*/ " + instruction)

    def test_malformed_transcendental_operands_refuse_before_large_shifts(self):
        for value in [arithmetic.Rounded(True, 0), arithmetic.Rounded(1, -1000000),
                      arithmetic.Rounded(1 << 65, 0), arithmetic.Rounded(1, 0, zero_sign=2)]:
            for function in [candidate.logarithm, candidate.exponential]:
                with self.assertRaises(arithmetic.ArithmeticRefusal):
                    function(value, arithmetic.EXPANSION64)

    def test_transcendentals_against_independent_rational_enclosures(self):
        for name, target in [("matched-fp64", arithmetic.BINARY64),
                             ("compensated-pair", candidate.PAIR48),
                             ("expansion64", arithmetic.EXPANSION64)]:
            logarithms = [(1, 0), (3, -1), (7, -3), (1, -1085),
                          ((1 << 63) + 1, -63), ((1 << 64) - 1, -63), (1, 1023)]
            exponentials = [(0, 0), (1, 0), (-1, 0), (1, -63), (-1, -63),
                            (13, 0), (-13, 0), (-700, 0), (700, 0)]
            for operation, inputs in [("ln", logarithms), ("exp", exponentials)]:
                for coefficient, exponent in inputs:
                    operand = arithmetic.Rounded(coefficient, exponent)
                    actual = (candidate.logarithm if operation == "ln" else candidate.exponential)(operand, target).document()
                    expected = oracle.expected(operation, operand.document(), oracle.FORMATS[name])
                    self.assertEqual(actual, expected, (name, operation, coefficient, exponent))

    def test_directed_intervals_enclose_independent_oracle(self):
        for bits in candidate.WORKING_BITS:
            operand = arithmetic.Rounded(3, -1)
            low, high = candidate.log_interval(operand, bits)
            reference = oracle.logarithm_interval(Fraction(3, 2))
            self.assertLessEqual(Fraction(low, 1 << bits), reference[0])
            self.assertGreaterEqual(Fraction(high, 1 << bits), reference[1])
            interval, scale = candidate.exp_interval(operand, bits)
            reference = oracle.exponential_interval(Fraction(3, 2))
            self.assertLessEqual(interval[0] * oracle.power2(scale - bits), reference[0])
            self.assertGreaterEqual(interval[1] * oracle.power2(scale - bits), reference[1])

    def test_ambiguous_rounding_and_invalid_domains_refuse(self):
        with self.assertRaisesRegex(arithmetic.ArithmeticRefusal, "log_rounding_ambiguous"):
            candidate.logarithm(arithmetic.Rounded((1 << 63) + 1, -63), arithmetic.EXPANSION64, (128,))
        for value in [arithmetic.Rounded(), arithmetic.Rounded(-1, 0)]:
            with self.assertRaisesRegex(arithmetic.ArithmeticRefusal, "log_domain"):
                candidate.logarithm(value, arithmetic.EXPANSION64)
        with self.assertRaisesRegex(arithmetic.ArithmeticRefusal, "working_precision"):
            candidate.logarithm(arithmetic.Rounded(3, -1), arithmetic.EXPANSION64, (127,))
        self.assertEqual(candidate.exponential(arithmetic.Rounded(1024, 0), arithmetic.EXPANSION64).flags, ("overflow", "inexact"))
        self.assertEqual(candidate.exponential(arithmetic.Rounded(-1024, 0), arithmetic.EXPANSION64).flags, ("underflow", "inexact"))

    def test_candidate_uses_no_float_or_rational_oracle(self):
        tree = ast.parse((ROOT / "tools/lp_state_candidate.py").read_text())
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant):
                self.assertFalse(isinstance(node.value, float))
            if isinstance(node, ast.ImportFrom):
                self.assertNotIn(node.module, ("fractions", "lp_state_oracle", "lp_expansion_oracle"))
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                self.assertNotEqual(node.func.id, "float")

    def test_exact_dot_width_cancellation_and_range_refusal(self):
        # Saturates the 128-bit product alignment and 65536-term shape bound.
        large = arithmetic.Rounded((1 << 64) - 1, 0)
        shifted = arithmetic.Rounded((1 << 64) - 1, 64)
        left = [large] * 65535 + [shifted]
        right = [large] * 65535 + [shifted]
        actual = candidate.bounded_dot(left, right, arithmetic.EXPANSION64)
        self.assertEqual(actual, arithmetic.dot(left, right, arithmetic.EXPANSION64))
        # Below 2**272 means at most 272 magnitude bits, not fewer than 272.
        saturated = [shifted] * 65535 + [large]
        exact_coefficient = ((1 << 64) - 1) ** 2 * ((65535 << 128) + 1)
        self.assertEqual(exact_coefficient.bit_length(), 272)
        self.assertEqual(candidate.bounded_dot(saturated, saturated, arithmetic.EXPANSION64),
                         arithmetic.round_rational(exact_coefficient, 1, 0, arithmetic.EXPANSION64))
        self.assertEqual(candidate.bounded_dot([large, large], [large, arithmetic.negate(large)], arithmetic.EXPANSION64), arithmetic.Rounded())
        with self.assertRaisesRegex(arithmetic.ArithmeticRefusal, "dot_exponent_window"):
            candidate.bounded_dot([large, arithmetic.Rounded(1, 129)], [large, arithmetic.Rounded(1, 0)], arithmetic.EXPANSION64)
        with self.assertRaisesRegex(arithmetic.ArithmeticRefusal, "dot_shape"):
            candidate.bounded_dot(left + [large], right + [large], arithmetic.EXPANSION64)

    def test_pair_retains_updates_lost_by_plain_fp32(self):
        one = arithmetic.normalize(arithmetic.Rounded(1, 0), candidate.PAIR48)
        tiny = arithmetic.Rounded(1, -30)
        accumulated = one
        for _ in range(64):
            accumulated = arithmetic.add(accumulated, tiny, candidate.PAIR48).plain()
        self.assertNotEqual(accumulated, one)
        self.assertEqual(arithmetic.add(one, tiny, arithmetic.BINARY32).plain(), arithmetic.normalize(one, arithmetic.BINARY32).plain())
        self.assertEqual(arithmetic.norm([arithmetic.Rounded(1, 900)], 2, arithmetic.EXPANSION64).plain(), arithmetic.normalize(arithmetic.Rounded(1, 900), arithmetic.EXPANSION64).plain())

    def test_stable_prox_exact_real_identity_and_bound_tags(self):
        target = arithmetic.EXPANSION64
        step = arithmetic.Rounded(1, -2)
        lower, upper = arithmetic.Rounded(-2, 0), arithmetic.Rounded(3, 0)
        for integer in range(-12, 13):
            value = arithmetic.Rounded(integer, -2)
            actual = candidate.support_prox(value, step, lower, upper, target)
            z = Fraction(integer, 4)
            projected = min(max(z / Fraction(1, 4), -2), 3)
            expected = arithmetic.round_rational((z - Fraction(1, 4) * projected).numerator,
                                                (z - Fraction(1, 4) * projected).denominator, 0, target)
            self.assertEqual(actual.plain(), expected.plain())
        self.assertEqual(candidate.support_prox(arithmetic.Rounded(7, 0), step, None, None, target), arithmetic.Rounded())
        with self.assertRaisesRegex(arithmetic.ArithmeticRefusal, "nonfinite_operand"):
            candidate.support_prox(arithmetic.Rounded(infinity_sign=1), step, None, None, target)


if __name__ == "__main__":
    unittest.main()
