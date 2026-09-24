import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class OfficialPlansGapFillTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        rows = json.loads((ROOT / "data" / "all_projects_layer.json").read_text(encoding="utf-8"))
        cls.rows = {(row.get("canonical_project_id"), row.get("canonical_name")): row for row in rows}

    def test_reviewed_plans_are_applied(self):
        expected = {
            ("proj-164", "One Tower"): (2030, 2),
            ("proj-204", "Top Tower"): (2029, None),
        }
        for key, date in expected.items():
            row = self.rows[key]
            self.assertEqual((row["input_year"], row["input_quarter"]), date)
            self.assertEqual(row["input_date_kind"], "planned")

    def test_k_city_conflict_remains_unfilled(self):
        row = self.rows[("proj-136", "K-city")]
        self.assertIsNone(row["input_year"])
        self.assertIsNone(row["input_quarter"])
        self.assertIn("Q2 2028", row["qa_notes"])
        self.assertIn("Q4 2028", row["qa_notes"])


if __name__ == "__main__":
    unittest.main()
