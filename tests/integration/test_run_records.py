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
        self.record = read_json(ROOT / "examples/run-record-v2.json")
        self.validator = validator("run-record-v2.schema.json")

    def test_example_record_is_valid(self):
        self.validator.validate(self.record)
        validate_run_record(ROOT / "examples/run-record-v2.json")

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
            # Version 1 is what every run record carried before SPEC-0010 added a
            # device to the configuration a record embeds. It is refused rather
            # than migrated, because a version-1 record of a device run and one of
            # a CPU run are indistinguishable.
            {**self.record, "schema_version": 1},
            {**self.record, "schema_version": 3},
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
        self.record = read_json(ROOT / "examples/run-record-v2.json")["search"]
        self.validator = validator("search-record-v3.schema.json")

    def test_example_search_record_is_valid(self):
        self.validator.validate(self.record)

    def test_search_documents_are_version_three(self):
        # SPEC-0004 moved search documents to version 2 for the extension policy
        # and SPEC-0010 moved them to version 3 for the device. Earlier versions
        # are refused rather than migrated.
        for version in (1, 2, 4):
            record = {**self.record, "schema_version": version}
            with self.assertRaises(ValidationError):
                self.validator.validate(record)
        for version in (1, 2):
            record = copy.deepcopy(self.record)
            record["options"]["schema_version"] = version
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
        record = read_json(ROOT / "examples/run-record-v2.json")
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
        config = ROOT / "examples/search-config-v3.json"
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


class DeviceSelectionContracts(unittest.TestCase):
    """SPEC-0010 requirements 2, 40 and 41: the device the configuration names.

    The schema and the Rust parser must accept the same documents, neither laxer
    than the other. These check the schema half; the Rust half lives in
    `crates/optimizer-solver/tests/executive.rs`, and the two are deliberately
    written against the same cases so a divergence shows up as one failing and the
    other passing rather than as both being silently wrong.
    """

    def setUp(self):
        self.config = read_json(ROOT / "examples/search-config-v3.json")
        self.validator = validator("search-config-v3.schema.json")

    def test_the_committed_configuration_is_valid_and_names_the_cpu(self):
        self.validator.validate(self.config)
        self.assertEqual(self.config["device"], "cpu")

    def test_a_configuration_without_a_device_is_refused(self):
        # A version-2 document is exactly this one without the device, which is
        # what makes accepting it tempting. Refusing it is requirement 41: a
        # version-2 record of a device run and one of a CPU run are the same
        # bytes, so a migration would have to invent what distinguishes them.
        stale = copy.deepcopy(self.config)
        del stale["device"]
        with self.assertRaises(ValidationError):
            self.validator.validate(stale)

        stale["schema_version"] = 2
        with self.assertRaises(ValidationError):
            self.validator.validate(stale)

    def test_only_the_cpu_and_a_uuid_are_accepted(self):
        for accepted in ("cpu", "GPU-dfb2449a-9eff-e868-3597-2c448c9a8e48"):
            with self.subTest(device=accepted):
                self.validator.validate({**self.config, "device": accepted})

        for refused in (
            # An enumeration index: CUDA_VISIBLE_DEVICES renumbers devices per
            # process, so a record carrying one could not be re-executed.
            "0",
            "gpu:0",
            # Case matters, so two spellings of one device cannot compare unequal.
            "gpu-dfb2449a",
            "GPU-",
            "",
            "CPU",
            "cuda",
            "GPU-dfb2449a_9eff",
        ):
            with self.subTest(device=refused):
                with self.assertRaises(ValidationError):
                    self.validator.validate({**self.config, "device": refused})

    def test_the_rust_parser_refuses_what_the_schema_refuses(self):
        """Requirement 41: neither authority may be laxer than the other."""
        binary = ROOT / "target/debug/optimizer"
        if not binary.is_file():
            self.skipTest("optimizer binary not built")
        import json
        import tempfile

        model = ROOT / "examples/model-v1.json"
        for name, mutation in (
            ("absent device", lambda c: c.pop("device")),
            ("enumeration index", lambda c: c.update(device="0")),
            ("lowercase prefix", lambda c: c.update(device="gpu-dfb2449a")),
            ("version 2", lambda c: (c.pop("device"), c.update(schema_version=2))),
        ):
            with self.subTest(case=name):
                mutated = copy.deepcopy(self.config)
                mutation(mutated)
                with self.assertRaises(ValidationError):
                    self.validator.validate(mutated)
                with tempfile.TemporaryDirectory() as directory:
                    path = Path(directory) / "config.json"
                    path.write_text(json.dumps(mutated))
                    completed = subprocess.run(
                        [str(binary), "search", "--model", str(model),
                         "--config", str(path), "--output", str(Path(directory) / "out.json")],
                        capture_output=True, text=True, timeout=120, cwd=ROOT,
                    )
                    self.assertNotEqual(
                        completed.returncode, 0,
                        f"{name}: the Rust parser accepted what the schema refused",
                    )

    def test_a_named_device_is_refused_rather_than_run_on_the_cpu(self):
        """Requirement 6: a record must not claim hardware the run did not use.

        The schema accepts a UUID, because the document is well formed. The engine
        refuses it, because no search path dispatches to a device yet. Running it
        would produce a record naming a device, which verification would re-run on
        the CPU and agree with, certifying a claim nothing checked.
        """
        binary = ROOT / "target/debug/optimizer"
        if not binary.is_file():
            self.skipTest("optimizer binary not built")
        import json
        import tempfile

        named = {**self.config, "device": "GPU-dfb2449a-9eff-e868-3597-2c448c9a8e48"}
        self.validator.validate(named)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.json"
            path.write_text(json.dumps(named))
            output = Path(directory) / "out.json"
            completed = subprocess.run(
                [str(binary), "search", "--model", str(ROOT / "examples/model-v1.json"),
                 "--config", str(path), "--output", str(output)],
                capture_output=True, text=True, timeout=120, cwd=ROOT,
            )
            if "not provisioned" in completed.stderr:
                self.skipTest("HiGHS not provisioned; run bash tools/setup_highs.sh")
            self.assertNotEqual(completed.returncode, 0, completed.stdout)
            self.assertIn("GPU-dfb2449a", completed.stderr)
            self.assertFalse(output.exists(), "a refused search must write no record")


if __name__ == "__main__":
    unittest.main()
