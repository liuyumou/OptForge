"""Negative acceptance cases for the solve configuration and record schemas, SPEC-0002."""

import copy
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))
from validate_artifacts import ROOT, read_json, validator
from jsonschema import ValidationError


class SolveConfigContracts(unittest.TestCase):
    def setUp(self):
        self.config = read_json(ROOT / "examples/solve-config-v1.json")
        self.validator = validator("solve-config-v1.schema.json")

    def test_example_configuration_is_valid(self):
        self.validator.validate(self.config)

    def test_every_field_is_required(self):
        for key in self.config:
            with self.subTest(key=key):
                record = copy.deepcopy(self.config)
                del record[key]
                with self.assertRaises(ValidationError):
                    self.validator.validate(record)

    def test_unknown_fields_and_versions_are_rejected(self):
        for record in (
            {**self.config, "surprise": True},
            {**self.config, "schema_version": 2},
        ):
            with self.assertRaises(ValidationError):
                self.validator.validate(record)

    def test_zero_limits_are_rejected_but_absent_limits_are_allowed(self):
        # A limit is optional, but a present limit must be positive so that a
        # configuration can never request zero work.
        for key in ("time_limit_ms", "iteration_limit", "node_limit"):
            with self.subTest(key=key):
                with self.assertRaises(ValidationError):
                    self.validator.validate({**self.config, key: 0})
                self.validator.validate({**self.config, key: None})

    def test_only_single_threaded_cpu_solves_are_supported(self):
        for threads in (0, 2, 8):
            with self.subTest(threads=threads):
                with self.assertRaises(ValidationError):
                    self.validator.validate({**self.config, "threads": threads})

    def test_tolerances_are_explicit_and_bounded(self):
        for key in ("absolute", "relative", "integrality"):
            with self.subTest(key=key):
                record = copy.deepcopy(self.config)
                del record["tolerances"][key]
                with self.assertRaises(ValidationError):
                    self.validator.validate(record)
                record = copy.deepcopy(self.config)
                record["tolerances"][key] = -1.0
                with self.assertRaises(ValidationError):
                    self.validator.validate(record)
        # Integrality must stay below one half, or rounding would be ambiguous.
        for value in (0.5, 0.9):
            record = copy.deepcopy(self.config)
            record["tolerances"]["integrality"] = value
            with self.assertRaises(ValidationError):
                self.validator.validate(record)


class SolveRecordContracts(unittest.TestCase):
    def setUp(self):
        self.validator = validator("solve-record-v2.schema.json")
        self.record = {
            "schema_version": 2,
            "model_id": "tiny-mixed",
            "backend": "highs",
            "backend_version": "1.11.0",
            "termination": "optimal",
            "native_status": "optimal",
            "objective": 2.5,
            "warnings": [],
            "elapsed_ms": 3,
            "options": read_json(ROOT / "examples/solve-config-v1.json"),
        }

    def test_minimal_and_complete_records_validate(self):
        self.validator.validate(self.record)
        minimal = {
            key: self.record[key]
            for key in (
                "schema_version",
                "model_id",
                "backend",
                "backend_version",
                "termination",
                "warnings",
                "elapsed_ms",
                "options",
            )
        }
        # Absent measurements are omitted entirely rather than sent as null.
        self.validator.validate(minimal)

    def test_absent_measurements_must_be_omitted_not_null(self):
        for key in ("objective", "best_bound", "gap", "native_status"):
            with self.subTest(key=key):
                with self.assertRaises(ValidationError):
                    self.validator.validate({**self.record, key: None})

    def test_required_provenance_is_present(self):
        for key in (
            "model_id",
            "backend",
            "backend_version",
            "termination",
            "elapsed_ms",
            "options",
        ):
            with self.subTest(key=key):
                record = copy.deepcopy(self.record)
                del record[key]
                with self.assertRaises(ValidationError):
                    self.validator.validate(record)

    def test_every_declared_termination_is_accepted(self):
        for termination in (
            "optimal",
            "feasible",
            "infeasible",
            "unbounded_or_infeasible",
            "unbounded",
            "interrupted",
            "time_limit",
            "iteration_limit",
            "node_limit",
            "numerical_failure",
            "backend_failure",
            "unsupported",
        ):
            with self.subTest(termination=termination):
                self.validator.validate({**self.record, "termination": termination})

    def test_unknown_terminations_and_fields_are_rejected(self):
        for record in (
            {**self.record, "termination": "almost_optimal"},
            {**self.record, "termination": "proven"},
            {**self.record, "surprise": True},
            {**self.record, "schema_version": 1},
            {**self.record, "schema_version": 3},
            {**self.record, "elapsed_ms": -1},
            {**self.record, "backend_version": ""},
        ):
            with self.assertRaises(ValidationError):
                self.validator.validate(record)

    def test_embedded_configuration_must_itself_be_valid(self):
        record = copy.deepcopy(self.record)
        record["options"]["threads"] = 4
        with self.assertRaises(ValidationError):
            self.validator.validate(record)


if __name__ == "__main__":
    unittest.main()

class LpSettingsContracts(unittest.TestCase):
    """SPEC-0011 requirements 9 and 10, from the schema side.

    The Rust parser refuses a settings document that omits a recorded field.
    These assert the schema refuses the same documents, so neither authority is
    laxer than the other -- the parity rule SPEC-0005 requirement 20 and
    SPEC-0009 requirement 26 already apply to the other documents.
    """

    def setUp(self):
        self.validator = validator("lp-settings-v1.schema.json")
        self.settings = read_json(ROOT / "examples/lp-settings-v1.json")

    def test_the_committed_example_validates(self):
        self.validator.validate(self.settings)

    def test_a_document_missing_a_recorded_field_is_refused(self):
        for absent in (
            "preconditioner",
            "check_interval",
            "iteration_limit",
            "power_iterations",
            "restart",
            "primal_weight",
        ):
            partial = {k: v for k, v in self.settings.items() if k != absent}
            with self.subTest(absent=absent), self.assertRaises(ValidationError):
                self.validator.validate(partial)

    def test_unknown_fields_and_out_of_range_values_are_refused(self):
        for settings in (
            {**self.settings, "step_size": 0.5},
            {**self.settings, "schema_version": 2},
            {**self.settings, "check_interval": 0},
            {**self.settings, "iteration_limit": 0},
            {
                **self.settings,
                "restart": {**self.settings["restart"], "sufficient": 1.5},
            },
            {
                **self.settings,
                "preconditioner": {
                    **self.settings["preconditioner"],
                    "pock_chambolle_alpha": 3.0,
                },
            },
        ):
            with self.assertRaises(ValidationError):
                self.validator.validate(settings)

    def test_a_record_embedding_invalid_settings_is_refused(self):
        embedded = {
            "schema_version": 2,
            "model_id": "tiny-continuous",
            "backend": "host-lp",
            "backend_version": "0.1.0",
            "termination": "optimal",
            "warnings": [],
            "elapsed_ms": 3,
            "options": read_json(ROOT / "examples/solve-config-v1.json"),
            "lp_settings": {k: v for k, v in self.settings.items() if k != "check_interval"},
        }
        with self.assertRaises(ValidationError):
            validator("solve-record-v2.schema.json").validate(embedded)
