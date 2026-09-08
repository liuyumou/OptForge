"""Negative acceptance cases for the artifact authority boundary, SPEC-0007."""

import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))
from validate_artifacts import ROOT, read_json, validate_manifest, validate_result, validator
from jsonschema import ValidationError


class ArtifactContracts(unittest.TestCase):
    def setUp(self):
        self.example = read_json(ROOT / "examples/experiment-result.json")

    def validate_record(self, record):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "result.json"
            path.write_text(json.dumps(record))
            return validate_result(path)

    def test_example_has_complete_provenance(self):
        self.validate_record(self.example)

    def test_no_premature_optimality_or_failure_objective(self):
        for status in ("optimal", "backend_failure", "infeasible", "unbounded"):
            with self.subTest(status=status):
                record = copy.deepcopy(self.example)
                record.update(status=status, objective=1.0)
                with self.assertRaises(ValidationError):
                    self.validate_record(record)

    def test_changed_manifest_configuration_and_device_are_rejected(self):
        for mutation in ("hash", "seed", "device", "revision", "samples"):
            with self.subTest(mutation=mutation):
                record = copy.deepcopy(self.example)
                if mutation == "hash":
                    record["manifest"]["sha256"] = "f" * 64
                elif mutation == "seed":
                    record["configuration"]["seed"] += 1
                elif mutation == "device":
                    record["hardware"]["gpu_uuid"] = "GPU-fake"
                elif mutation == "revision":
                    record["kind"] = "measured"
                else:
                    record["timing"]["samples"] += 1
                with self.assertRaises(ValueError):
                    self.validate_record(record)

    def test_required_metadata_unknown_fields_and_schema_versions(self):
        for key in ("revision", "hardware", "configuration", "timing", "manifest"):
            record = copy.deepcopy(self.example)
            del record[key]
            with self.assertRaises(ValidationError):
                self.validate_record(record)
        for record in ({**self.example, "surprise": True}, {**self.example, "schema_version": 2}):
            with self.assertRaises(ValidationError):
                self.validate_record(record)

    def test_fixture_tampering_and_path_escape_are_rejected(self):
        manifest = read_json(ROOT / "benchmarks/manifests/bootstrap-smoke.json")
        for path_value, checksum in (("tests/fixtures/bootstrap.txt", "0" * 64), ("../outside", "0" * 64)):
            manifest["instances"][0].update(path=path_value, sha256=checksum)
            with tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / "manifest.json"
                path.write_text(json.dumps(manifest))
                with self.assertRaises((ValueError, ValidationError)):
                    validate_manifest(path)

    def test_all_declared_outcomes_have_explicit_records(self):
        for status in ("smoke_passed", "feasible", "infeasible", "unbounded", "interrupted", "time_limited", "backend_failure", "unsupported"):
            record = copy.deepcopy(self.example)
            record["status"] = status
            record["error"] = "backend unavailable" if status == "backend_failure" else None
            self.validate_record(record)

    def test_json_nonfinite_numbers_and_duplicate_keys_are_rejected(self):
        for value in ('{"x": NaN}', '{"x": Infinity}', '{"x": 1e999}', '{"x": 1, "x": 2}'):
            with tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / "invalid.json"
                path.write_text(value)
                with self.assertRaises(ValueError):
                    read_json(path)

    def test_zero_limits_and_unsupported_settings_are_rejected(self):
        config = read_json(ROOT / "examples/run-config.json")
        for key in ("time_limit_ms", "memory_limit_mib", "threads"):
            with self.assertRaises(ValidationError):
                validator("run-config-v1.schema.json").validate({**config, key: 0})
        with self.assertRaises(ValidationError):
            validator("run-config-v1.schema.json").validate({**config, "settings": {"unimplemented": True}})
