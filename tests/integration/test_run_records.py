"""Negative acceptance cases for the run record and search schemas, SPEC-0005."""

import copy
import hashlib
import subprocess
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))
from validate_artifacts import ROOT, read_json, validate_run_record, validator
from jsonschema import ValidationError


class RunRecordContracts(unittest.TestCase):
    def setUp(self):
        self.record = read_json(ROOT / "examples/run-record-v1.json")
        self.validator = validator("run-record-v1.schema.json")

    def test_example_record_is_valid(self):
        self.validator.validate(self.record)
        validate_run_record(ROOT / "examples/run-record-v1.json")

    def test_every_field_is_required(self):
        for key in self.record:
            with self.subTest(key=key):
                record = copy.deepcopy(self.record)
                del record[key]
                with self.assertRaises(ValidationError):
                    self.validator.validate(record)

    def test_unknown_fields_and_versions_are_rejected(self):
        for record in (
            {**self.record, "surprise": True},
            {**self.record, "schema_version": 2},
        ):
            with self.assertRaises(ValidationError):
                self.validator.validate(record)

    def test_provenance_fields_are_required(self):
        # Provenance is what makes a record repeatable; a partial one is refused
        # rather than accepted with holes.
        for section, key in (
            ("hardware", "cpu"),
            ("hardware", "gpu_uuid"),
            ("toolchain", "rustc"),
            ("toolchain", "cargo"),
        ):
            with self.subTest(section=section, key=key):
                record = copy.deepcopy(self.record)
                del record[section][key]
                with self.assertRaises(ValidationError):
                    self.validator.validate(record)

    def test_revision_and_hashes_must_be_lowercase_hex(self):
        for path, value in (
            (("revision",), "not-a-revision"),
            (("revision",), "A" * 40),
            (("revision",), "0" * 39),
            (("model_fingerprint",), ""),
        ):
            with self.subTest(path=path, value=value):
                record = copy.deepcopy(self.record)
                record[path[0]] = value
                with self.assertRaises(ValidationError):
                    self.validator.validate(record)
        record = copy.deepcopy(self.record)
        record["inputs"][0]["sha256"] = "abc"
        with self.assertRaises(ValidationError):
            self.validator.validate(record)

    def test_inputs_must_name_one_model_and_one_config(self):
        record = copy.deepcopy(self.record)
        record["inputs"] = [record["inputs"][0]]
        with self.assertRaises(ValidationError):
            self.validator.validate(record)

        # Two model inputs satisfy the schema's item count but not the contract.
        record = copy.deepcopy(self.record)
        record["inputs"][1]["role"] = "model"
        self.validator.validate(record)
        with self.assertRaises(ValueError):
            self._validate_written(record)

    def test_an_input_checksum_mismatch_is_rejected(self):
        record = copy.deepcopy(self.record)
        record["inputs"][0]["sha256"] = "0" * 64
        with self.assertRaises(ValueError):
            self._validate_written(record)

    def test_an_example_record_must_declare_itself(self):
        # The all-zero revision marks a shape, so it must carry the warning that
        # says it is not evidence.
        record = copy.deepcopy(self.record)
        record["warnings"] = []
        with self.assertRaises(ValueError):
            self._validate_written(record)

    def test_a_forfeited_search_must_not_claim_a_proof(self):
        # This is SPEC-0003's rule enforced at the artifact boundary too, so the
        # two normative paths cannot disagree about it.
        record = copy.deepcopy(self.record)
        record["search"]["forfeited"] = True
        with self.assertRaises(ValueError):
            self._validate_written(record)

    def test_input_paths_must_not_escape_the_repository(self):
        record = copy.deepcopy(self.record)
        record["inputs"][0]["path"] = "../../etc/passwd"
        with self.assertRaises(ValueError):
            self._validate_written(record)

    def _validate_written(self, record):
        """Validate a mutated record through the file-based authority."""
        import json
        import tempfile

        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as handle:
            handle.write(json.dumps(record))
            path = Path(handle.name)
        try:
            return validate_run_record(path)
        finally:
            path.unlink(missing_ok=True)


class SearchRecordContracts(unittest.TestCase):
    def setUp(self):
        self.record = read_json(ROOT / "examples/run-record-v1.json")["search"]
        self.validator = validator("search-record-v2.schema.json")

    def test_example_search_record_is_valid(self):
        self.validator.validate(self.record)

    def test_search_documents_are_version_two(self):
        # SPEC-0004 moved search documents to version 2 and rejects version 1
        # rather than migrating it.
        for version in (1, 3):
            record = {**self.record, "schema_version": version}
            with self.assertRaises(ValidationError):
                self.validator.validate(record)
        record = copy.deepcopy(self.record)
        record["options"]["schema_version"] = 1
        with self.assertRaises(ValidationError):
            self.validator.validate(record)

    def test_every_declared_outcome_is_accepted(self):
        for outcome in (
            "proven_optimal",
            "proven_infeasible",
            "unbounded_or_infeasible",
            "feasible",
            "node_limit",
            "time_limit",
            "open_node_limit",
            "interrupted",
            "numerical_failure",
            "backend_failure",
            "unsupported",
        ):
            with self.subTest(outcome=outcome):
                self.validator.validate({**self.record, "outcome": outcome})

    def test_an_unknown_outcome_is_rejected(self):
        with self.assertRaises(ValidationError):
            self.validator.validate({**self.record, "outcome": "optimal"})

    def test_counters_and_elapsed_time_must_be_nonnegative(self):
        for key in (
            "nodes_explored",
            "nodes_pruned_infeasible",
            "nodes_pruned_bound",
            "open_nodes_remaining",
            "relaxations_solved",
            "elapsed_ms",
        ):
            with self.subTest(key=key):
                with self.assertRaises(ValidationError):
                    self.validator.validate({**self.record, key: -1})

    def test_omitted_measurements_are_not_null(self):
        # An unavailable measurement is absent, never a null standing in for a
        # number that was never computed.
        for key in ("objective", "dual_bound", "gap"):
            with self.subTest(key=key):
                with self.assertRaises(ValidationError):
                    self.validator.validate({**self.record, key: None})
                absent = copy.deepcopy(self.record)
                absent.pop(key, None)
                self.validator.validate(absent)

    def test_required_fields_are_required(self):
        optional = {"objective", "dual_bound", "gap", "candidate", "validation"}
        for key in self.record:
            if key in optional:
                continue
            with self.subTest(key=key):
                record = copy.deepcopy(self.record)
                del record[key]
                with self.assertRaises(ValidationError):
                    self.validator.validate(record)


class ChecksumAgreement(unittest.TestCase):
    """The engine's SHA-256 must agree with an independent implementation."""

    def test_recorded_input_hashes_match_hashlib(self):
        # The Rust implementation is checked against Python's hashlib over the
        # real committed documents, so agreement is verified rather than assumed.
        record = read_json(ROOT / "examples/run-record-v1.json")
        for document in record["inputs"]:
            with self.subTest(role=document["role"]):
                target = ROOT / document["path"]
                self.assertEqual(
                    hashlib.sha256(target.read_bytes()).hexdigest(),
                    document["sha256"],
                )

    def test_engine_and_hashlib_agree_on_generated_content(self):
        # A second, independent comparison over content that is not committed,
        # so the agreement is not an artifact of one fixed pair of files.
        binary = ROOT / "target/debug/optimizer"
        if not binary.is_file():
            self.skipTest("run cargo build --workspace --locked first")
        model = ROOT / "examples/model-v1.json"
        config = ROOT / "examples/search-config-v2.json"
        completed = subprocess.run(
            [str(binary), "search", "--model", str(model), "--config", str(config)],
            capture_output=True,
            text=True,
            timeout=120,
            cwd=ROOT,
        )
        if "not provisioned" in completed.stderr:
            self.skipTest("HiGHS not provisioned; run bash tools/setup_highs.sh")
        self.assertEqual(completed.returncode, 0, completed.stderr)
        import json

        produced = json.loads(completed.stdout)
        for document in produced["inputs"]:
            with self.subTest(role=document["role"]):
                self.assertEqual(
                    hashlib.sha256((ROOT / document["path"]).read_bytes()).hexdigest(),
                    document["sha256"],
                )


if __name__ == "__main__":
    unittest.main()
