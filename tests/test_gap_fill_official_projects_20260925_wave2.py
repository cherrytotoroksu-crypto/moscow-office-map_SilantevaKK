import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class OfficialProjectsGapFillWave2Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        rows = json.loads(
            (ROOT / "data" / "all_projects_layer.json").read_text(encoding="utf-8")
        )
        cls.rows = {row.get("canonical_project_id"): row for row in rows}
        cls.dates = json.loads(
            (ROOT / "data" / "building_dates.json").read_text(encoding="utf-8")
        )

    def test_verified_years_are_applied_without_invented_quarters(self):
        expected = {"proj-91": 2027, "proj-99": 2026}
        for project_id, year in expected.items():
            row = self.rows[project_id]
            self.assertEqual(row["input_year"], year)
            self.assertIsNone(row["input_quarter"])
            self.assertEqual(row["input_date_kind"], "planned")

    def test_building_dates_are_synchronized(self):
        expected = {
            "stone белорусская": ("proj-91", 2027),
            "магистральная 12 (бывший — магистральная ул., 12)": ("proj-99", 2026),
        }
        for key, values in expected.items():
            row = self.dates[key]
            self.assertEqual(
                (row["canonical_project_id"], row["commission_year"]), values
            )
            self.assertIsNone(row["commission_q"])

    def test_rejected_candidates_remain_unfilled(self):
        for project_id in (
            "proj-96",
            "proj-98",
            "proj-260",
        ):
            row = self.rows[project_id]
            self.assertIsNone(row["input_year"])
            self.assertIsNone(row["input_quarter"])


if __name__ == "__main__":
    unittest.main()
