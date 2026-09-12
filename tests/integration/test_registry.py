"""Extension registry and conformance schema contracts (SPEC-0009).

These tests exist because the JSON Schemas and the Rust parsers are both normative
and must accept exactly the same documents. A schema laxer than the parser would
let the validator bless a document the engine refuses; a schema stricter than the
parser would reject one the engine accepts. Either way the two authorities would
disagree about what a valid registry is.
"""

import copy
import json
import subprocess
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))

import validate_artifacts as validator  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
REGISTRY = ROOT / "examples/extension-registry-v1.json"
CONFORMANCE = ROOT / "examples/conformance-record-v1.json"
BINARY = ROOT / "target/debug/optimizer"


def registry():
    return json.loads(REGISTRY.read_text())


def conformance():
    return json.loads(CONFORMANCE.read_text())


class RegistrySchemaContracts(unittest.TestCase):
    """The committed examples validate, and malformed variants do not."""

    def test_committed_examples_validate(self):
        validator.validate_registry(REGISTRY)
        validator.validate_conformance(CONFORMANCE)

    def test_registry_requires_every_field(self):
        for field in registry()["entries"][0]:
            document = registry()
            del document["entries"][0][field]
            with self.subTest(field=field), self.assertRaises(Exception):
                validator.validator("extension-registry-v1.schema.json").validate(document)

    def test_registry_rejects_unknown_fields(self):
        for target in ("document", "entry"):
            document = registry()
            if target == "document":
                document["unknown"] = 1
            else:
                document["entries"][0]["unknown"] = 1
            with self.subTest(target=target), self.assertRaises(Exception):
                validator.validator("extension-registry-v1.schema.json").validate(document)

    def test_registry_rejects_unknown_enum_variants(self):
        cases = {
            "category": "reformulation",
            "authority_basis": "decide_optimality",
            "data_requirement": "job_shop_instance",
            "hardware_requirement": "tpu",
        }
        for field, value in cases.items():
            document = registry()
            document["entries"][0][field] = value
            with self.subTest(field=field), self.assertRaises(Exception):
                validator.validator("extension-registry-v1.schema.json").validate(document)

    def test_registry_rejects_a_wrong_version(self):
        for level in ("document", "entry"):
            document = registry()
            if level == "document":
                document["schema_version"] = 2
            else:
                document["entries"][0]["schema_version"] = 2
            with self.subTest(level=level), self.assertRaises(Exception):
                validator.validator("extension-registry-v1.schema.json").validate(document)

    def test_registry_rejects_a_positional_array(self):
        with self.assertRaises(Exception):
            validator.validator("extension-registry-v1.schema.json").validate([1, "id", []])

    def test_promotion_requires_its_conformance_fields(self):
        # An experimental entry naming a conformance record, and a promoted entry
        # naming none, are both refused: promotion is a checkable claim, so a
        # half-stated one must not validate.
        experimental = registry()
        experimental["entries"][0]["promotion"] = {
            "state": "experimental",
            "conformance_path": "somewhere.json",
        }
        promoted = registry()
        promoted["entries"][0]["promotion"] = {"state": "promoted"}
        for name, document in (("experimental", experimental), ("promoted", promoted)):
            with self.subTest(case=name), self.assertRaises(Exception):
                validator.validator("extension-registry-v1.schema.json").validate(document)

    def test_promotion_checksum_must_be_hex(self):
        document = registry()
        document["entries"][0]["promotion"]["conformance_sha256"] = "not-a-hash"
        with self.assertRaises(Exception):
            validator.validator("extension-registry-v1.schema.json").validate(document)

    def test_authority_must_be_implied_by_the_category(self):
        document = registry()
        document["entries"][0]["authority_basis"] = "propose_checked_action"
        with self.assertRaises(ValueError):
            validator.validate_registry_document(document)

    def test_a_duplicate_identity_is_refused(self):
        document = registry()
        document["entries"].append(copy.deepcopy(document["entries"][0]))
        with self.assertRaises(ValueError):
            validator.validate_registry_document(document)

    def test_conformance_outcome_must_match_its_checks(self):
        record = conformance()
        record["checks"][0]["passed"] = False
        with self.assertRaises(ValueError):
            validator.validate_conformance_record(record)

    def test_conformance_requires_at_least_one_check(self):
        record = conformance()
        record["checks"] = []
        with self.assertRaises(Exception):
            validator.validator("conformance-record-v1.schema.json").validate(record)

    def test_conformance_records_no_timing(self):
        # SPEC-0009 requirement 27: a duration here would be read as a performance
        # result. Asserting the absence keeps a later field from arriving quietly.
        forbidden = {"elapsed_ms", "elapsed_ns", "duration", "timing", "samples"}
        self.assertEqual(forbidden & set(conformance()), set())


class RegistryParserAgreement(unittest.TestCase):
    """The Rust parser refuses what the schema refuses."""

    def setUp(self):
        if not BINARY.is_file():
            self.skipTest("run cargo build --workspace --locked first")

    def run_list(self, document, directory):
        path = Path(directory) / "registry.json"
        path.write_text(json.dumps(document))
        return subprocess.run(
            [str(BINARY), "registry", "list", "--registry", str(path)],
            capture_output=True,
            text=True,
            timeout=60,
            cwd=ROOT,
        )

    def test_the_rust_parser_accepts_the_committed_registry(self):
        completed = subprocess.run(
            [str(BINARY), "registry", "list", "--registry", str(REGISTRY)],
            capture_output=True,
            text=True,
            timeout=60,
            cwd=ROOT,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        listing = json.loads(completed.stdout)
        self.assertEqual(listing["registry_id"], "example-local-registry")
        self.assertEqual(len(listing["entries"]), len(registry()["entries"]))

    def test_the_rust_parser_refuses_what_the_schema_refuses(self):
        import tempfile

        cases = {}
        document = registry()
        document["entries"][0]["unknown"] = 1
        cases["unknown field"] = document

        document = registry()
        document["schema_version"] = 2
        cases["wrong document version"] = document

        document = registry()
        document["entries"][0]["schema_version"] = 2
        cases["wrong entry version"] = document

        document = registry()
        document["entries"][0]["hardware_requirement"] = "tpu"
        cases["unknown variant"] = document

        # These two are cross-field rules a JSON Schema cannot express: whether an
        # authority follows from a category, and whether two entries collide. They
        # live in the validator's own checks, so the pairing asserted here is the
        # Rust parser against `validate_registry_document` rather than against the
        # schema alone.
        cross_field = {}
        document = registry()
        document["entries"][0]["authority_basis"] = "propose_checked_action"
        cross_field["wrong authority"] = document

        document = registry()
        document["entries"].append(copy.deepcopy(document["entries"][0]))
        cross_field["duplicate identity"] = document

        with tempfile.TemporaryDirectory() as directory:
            for name, document in cases.items():
                with self.subTest(case=name):
                    # Both authorities must refuse it. Asserting only the Rust side
                    # would let the schema drift laxer without any test noticing.
                    with self.assertRaises(Exception):
                        validator.validator("extension-registry-v1.schema.json").validate(
                            document
                        )
                    completed = self.run_list(document, directory)
                    self.assertEqual(completed.returncode, 2, completed.stdout)
                    self.assertIn("optimizer:", completed.stderr)

            for name, document in cross_field.items():
                with self.subTest(case=name):
                    with self.assertRaises(ValueError):
                        validator.validate_registry_document(document)
                    completed = self.run_list(document, directory)
                    self.assertEqual(completed.returncode, 2, completed.stdout)
                    self.assertIn("optimizer:", completed.stderr)


if __name__ == "__main__":
    unittest.main()
