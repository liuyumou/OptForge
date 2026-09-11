"""Frozen flow-shop subset provenance under SPEC-0008 requirements 22 to 24.

The manifest records how each instance was produced, so this checks the derivation
rather than only the bytes: an independent Python implementation of Taillard's
generator is run from each recorded seed and must reproduce the committed document
exactly. A checksum alone would only prove the file has not changed; this proves the
file is what the recorded generator and seed actually produce.

The generator is reimplemented here on purpose. Calling the Rust one would make the
agreement a tautology, which is the same reason the repository checks its SHA-256
against Python's hashlib rather than against itself.
"""

import hashlib
import json
import math
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "benchmarks/manifests/taillard-flow-shop-development.json"

# Taillard's published verification instance, ta001 from seed 873654221. Rows are
# machines and columns are jobs, exactly as the source prints it.
TA001_FIRST_ROW = [54, 83, 15, 71, 77, 36, 53, 38, 27, 87, 76, 91, 14, 29, 12, 77, 32, 87, 68, 94]
TA001_LAST_ROW = [58, 56, 20, 85, 53, 35, 53, 41, 69, 13, 86, 72, 8, 49, 47, 87, 58, 18, 68, 28]


def read_json(path):
    """Reject duplicate keys and non-finite numbers, matching the artifact validator."""

    def unique_keys(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"duplicate JSON key: {key}")
            result[key] = value
        return result

    def finite_float(value):
        number = float(value)
        if not math.isfinite(number):
            raise ValueError(f"non-finite JSON number: {value}")
        return number

    return json.loads(
        path.read_text(),
        object_pairs_hook=unique_keys,
        parse_float=finite_float,
        parse_constant=lambda value: (_ for _ in ()).throw(ValueError(f"non-finite: {value}")),
    )


class Lehmer:
    """Taillard's generator, transcribed from the paper rather than from the crate."""

    M = 2147483647
    A = 16807
    B = 127773
    C = 2836

    def __init__(self, seed):
        self.seed = seed

    def next_in(self, low, high):
        k = self.seed // self.B
        self.seed = self.A * (self.seed % self.B) - k * self.C
        if self.seed < 0:
            self.seed += self.M
        value_0_1 = self.seed / self.M
        return low + int(value_0_1 * (high - low + 1))


def generate(seed, jobs, machines, low, high):
    """Machines outermost, jobs innermost, as generate_flow_shop does."""
    generator = Lehmer(seed)
    return [[generator.next_in(low, high) for _ in range(jobs)] for _ in range(machines)]


class FlowShopManifest(unittest.TestCase):
    def setUp(self):
        self.manifest = read_json(MANIFEST)

    def test_manifest_describes_a_frozen_development_subset(self):
        """Requirement 22: the split, purpose and suite are recorded."""
        self.assertEqual(self.manifest["split"], "development")
        self.assertEqual(self.manifest["purpose"], "correctness")
        self.assertEqual(self.manifest["suite"], "taillard-flow-shop")
        self.assertEqual(len(self.manifest["instances"]), 10)

    def test_every_instance_records_its_generator_and_seed(self):
        """Requirement 22: provenance is the generator, not only a checksum."""
        seeds = set()
        for instance in self.manifest["instances"]:
            generator = instance["generator"]
            self.assertIsNotNone(generator, f"{instance['id']} must record its generator")
            self.assertEqual(generator["name"], "taillard-1993-flow-shop")
            self.assertNotIn(generator["seed"], seeds, "seeds must be unique")
            seeds.add(generator["seed"])
            self.assertEqual(generator["parameters"]["jobs"], 20)
            self.assertEqual(generator["parameters"]["machines"], 5)
            self.assertIn("Taillard", instance["source"])

    def test_regenerating_each_instance_reproduces_the_committed_document(self):
        """Requirement 23 and 27: the derivation is checked, not just the bytes."""
        for instance in self.manifest["instances"]:
            with self.subTest(instance=instance["id"]):
                path = ROOT / instance["path"]
                document = read_json(path)
                parameters = instance["generator"]["parameters"]
                expected = generate(
                    instance["generator"]["seed"],
                    parameters["jobs"],
                    parameters["machines"],
                    parameters["minimum_processing_time"],
                    parameters["maximum_processing_time"],
                )
                self.assertEqual(
                    document["processing_times"],
                    expected,
                    f"{instance['id']} is not what its recorded seed produces",
                )
                self.assertEqual(document["instance_id"], instance["id"])
                self.assertEqual(document["jobs"], parameters["jobs"])
                self.assertEqual(document["machines"], parameters["machines"])
                # The checksum is checked here too, so a document edited after
                # generation fails even if the generator still agrees.
                self.assertEqual(
                    hashlib.sha256(path.read_bytes()).hexdigest(),
                    instance["sha256"],
                    f"{instance['id']} checksum does not match the manifest",
                )

    def test_the_generator_reproduces_the_published_reference_instance(self):
        """Requirement 23: agreement with the source's own printed matrix."""
        ta001 = next(i for i in self.manifest["instances"] if i["id"] == "ta001")
        self.assertEqual(ta001["generator"]["seed"], 873654221)
        produced = generate(873654221, 20, 5, 1, 99)
        self.assertEqual(produced[0], TA001_FIRST_ROW)
        self.assertEqual(produced[4], TA001_LAST_ROW)
        # And the committed document is that same matrix.
        committed = read_json(ROOT / ta001["path"])
        self.assertEqual(committed["processing_times"][0], TA001_FIRST_ROW)
        self.assertEqual(committed["processing_times"][4], TA001_LAST_ROW)

    def test_processing_times_stay_in_the_published_range(self):
        """Requirement 2: every generated time is a positive integer within 1..99."""
        for instance in self.manifest["instances"]:
            document = read_json(ROOT / instance["path"])
            for machine, row in enumerate(document["processing_times"]):
                for job, time in enumerate(row):
                    self.assertIsInstance(time, int)
                    self.assertTrue(
                        1 <= time <= 99,
                        f"{instance['id']} job {job} machine {machine} time {time} out of range",
                    )

    def test_a_wrong_seed_does_not_reproduce_a_committed_instance(self):
        """The regeneration check must be able to fail, or it establishes nothing."""
        ta001 = next(i for i in self.manifest["instances"] if i["id"] == "ta001")
        committed = read_json(ROOT / ta001["path"])["processing_times"]
        wrong = generate(ta001["generator"]["seed"] + 1, 20, 5, 1, 99)
        self.assertNotEqual(committed, wrong, "a different seed must produce a different instance")
        # A transposed loop order must also disagree, since that is the mistake
        # requirement 23 exists to catch.
        transposed = [list(column) for column in zip(*generate(873654221, 5, 20, 1, 99))]
        self.assertNotEqual(committed, transposed, "loop order must matter")


if __name__ == "__main__":
    unittest.main()
