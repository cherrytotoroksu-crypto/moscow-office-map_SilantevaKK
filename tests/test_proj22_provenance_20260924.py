import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class Project22ProvenanceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        rows = json.loads((ROOT / "data" / "all_projects_layer.json").read_text(encoding="utf-8"))
        cls.row = next(row for row in rows if row.get("canonical_project_id") == "proj-22")

    def test_foreign_river_park_provenance_is_removed(self):
        self.assertNotIn("river-park", self.row["qa_notes"].lower())
        self.assertNotIn("project/51930", self.row["qa_notes"].lower())

    def test_unresolved_grain_is_explicit(self):
        self.assertEqual(self.row["qa_status"], "conflict")
        self.assertEqual(self.row["verification_status"], "under_review")
        self.assertEqual(self.row["confidence"], "low")
        self.assertIn("grain is resolved", self.row["qa_notes"])
        self.assertEqual(self.row["developer"], "")
        self.assertIsNone(self.row["input_year"])


if __name__ == "__main__":
    unittest.main()
