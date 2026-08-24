import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class UnifiedClassifierTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = json.loads((ROOT / "data" / "unified_classifier.json").read_text(encoding="utf-8"))
        cls.records = cls.data["records"]

    def test_full_registry_count_and_coordinate_split(self):
        self.assertEqual(len(self.records), 705)
        self.assertEqual(self.data["with_coordinates"], 680)
        self.assertEqual(self.data["without_coordinates"], 25)

    def test_unified_ids_are_stable_and_unique(self):
        ids = [r["unified_id"] for r in self.records]
        self.assertTrue(all(r["unified_id"] == f"UC-{r['source_id']}" for r in self.records))
        self.assertEqual(len(ids), len(set(ids)))

    def test_source_ids_are_unique(self):
        ids = [r["source_id"] for r in self.records]
        self.assertEqual(len(ids), len(set(ids)))

    def test_missing_coordinates_are_explicit(self):
        missing = [r for r in self.records if r["coordinates_status"] == "missing"]
        self.assertEqual(len(missing), 25)

    def test_every_unmatched_record_requires_review_even_without_address(self):
        unmatched = [r for r in self.records if not r["legacy_ids"]]
        self.assertTrue(unmatched)
        self.assertTrue(all(r["needs_review"] for r in unmatched))


if __name__ == "__main__":
    unittest.main()
