import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class StoneGapFillTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows = json.loads((ROOT / "data" / "all_projects_layer.json").read_text(encoding="utf-8"))

    def test_official_planned_years_are_applied_without_quarters(self):
        expected = {
            ("proj-185", "STONE Мневники I"): 2028,
            ("proj-188", "STONE Мневники II"): 2029,
            ("proj-189", "STONE Мневники III (M3.1)"): 2030,
            ("proj-189", "STONE Мневники III (M3.2)"): 2030,
            ("proj-192", "STONE Римская"): 2028,
        }
        indexed = {(row.get("canonical_project_id"), row.get("canonical_name")): row for row in self.rows}
        for key, year in expected.items():
            row = indexed[key]
            self.assertEqual(row["input_year"], year)
            self.assertIsNone(row["input_quarter"])
            self.assertEqual(row["input_date_kind"], "planned")


if __name__ == "__main__":
    unittest.main()
