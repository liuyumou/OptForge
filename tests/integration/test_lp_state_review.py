"""CPU-only challenge of the full-bin FMA stopping reason in PR 19."""

import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
import lp_state_admission as admission
import lp_state_review as review


class StateReviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.temporary.cleanup)
        cls.binary = Path(cls.temporary.name) / "fma-host"
        subprocess.run(["g++", "-O1", "-fsanitize=undefined", "-fno-sanitize-recover=all",
                        "-Werror", "-Wno-unknown-pragmas", "-std=c++17",
                        str(review.HARNESS), "-o", str(cls.binary)],
                       check=True, capture_output=True, timeout=120)
        cls.document = admission.read_document(review.FIXTURE)

    def test_supplementary_fixture_reproduces_independently(self):
        self.assertEqual(review.FIXTURE.read_text(), admission.encoded(review.fixture()))
        self.assertEqual(len(self.document["cases"]), 5900)
        self.assertEqual({case["precision"] for case in self.document["cases"]}, {48, 64})
        self.assertEqual({case["category"] for case in self.document["cases"]},
                         {"alignment", "cancellation", "full_range", "midpoint",
                          "overflow", "underflow", "signed_zero"})

    def test_both_constructions_match_boundaries_without_undefined_behavior(self):
        counts = review.verify_host(self.binary, self.document)
        self.assertEqual(counts["comparisons"], 11800)
        historical = admission.read_document(admission.FIXTURE)
        counts = review.verify_host(self.binary, {"cases": [dict(category="historical", **case)
                                                           for case in historical["fma_cases"]]})
        self.assertEqual(counts["comparisons"], 540)

    def test_corrupted_rounding_result_is_rejected(self):
        document = copy.deepcopy(self.document)
        document["cases"][0]["result"]["coefficient"] += 1
        with self.assertRaisesRegex(ValueError, "independent review FMA result differs"):
            review.verify_host(self.binary, document)

    def test_invalid_host_inputs_refuse_before_arithmetic(self):
        valid = ["4", "64", str(1 << 63), "-63", "0"] * 1
        valid += [str(1 << 63), "-63", "0", "0", "0", "0"]
        for index, value in ((0, "0"), (1, "63"), (2, "1"), (3, "-1000000"), (4, "2")):
            malformed = valid.copy()
            malformed[index] = value
            result = subprocess.run([str(self.binary)], input=" ".join(malformed) + "\n",
                                    text=True, capture_output=True, timeout=10)
            self.assertEqual(result.returncode, 2, malformed)
            self.assertEqual(result.stderr, "")

    def test_frozen_verification_tools_have_all_import_dependencies(self):
        with tempfile.TemporaryDirectory() as temporary:
            frozen = Path(temporary)
            for source in review.SOURCES:
                (frozen / source.name).write_bytes(source.read_bytes())
            # Source-only archive in an unrelated directory: no current checkout
            # or private campaign artifacts can supply a missing dependency.
            script = "import sys; sys.path.insert(0, sys.argv[1]); import lp_state_review as r; print(len(r.fixture()['cases']))"
            result = subprocess.run([sys.executable, "-I", "-B", "-c", script, str(frozen)],
                                    cwd=frozen, text=True, capture_output=True, check=True, timeout=120)
            self.assertEqual(result.stdout, "5900\n")

    def test_incomplete_review_receipt_refuses_before_private_files(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "review.json"
            for record in ({}, {"schema_version": True, "identity": review.IDENTITY}):
                path.write_text(json.dumps(record))
                with self.assertRaisesRegex(ValueError, "review identity/fields"):
                    review.verify(path)


if __name__ == "__main__":
    unittest.main()
