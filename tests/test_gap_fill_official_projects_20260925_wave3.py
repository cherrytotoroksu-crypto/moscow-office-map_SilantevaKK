import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class OfficialProjectsGapFillWave3Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        rows = json.loads(
            (ROOT / "data" / "all_projects_layer.json").read_text(encoding="utf-8")
        )
        cls.rows = {row.get("canonical_project_id"): row for row in rows}
        cls.dates = json.loads(
            (ROOT / "data" / "building_dates.json").read_text(encoding="utf-8")
        )

    def test_verified_dates_are_applied_with_supported_precision(self):
        expected = {
            "proj-102": (2023, 2, "confirmed"),
            "proj-152": (2029, None, "planned"),
            "proj-252": (2027, 4, "planned"),
        }
        for project_id, values in expected.items():
            row = self.rows[project_id]
            self.assertEqual(
                (row["input_year"], row["input_quarter"], row["input_date_kind"]),
                values,
            )

    def test_building_dates_are_synchronized(self):
        expected = {
            "парк легенд класс а": ("proj-102", 2023, "202304"),
            "mind": ("proj-152", 2029, None),
            "бизнес-парк раменки (бывший — огни)": ("proj-252", 2027, "202710"),
        }
        for key, values in expected.items():
            row = self.dates[key]
            self.assertEqual(
                (
                    row["canonical_project_id"],
                    row["commission_year"],
                    row["commission_q"],
                ),
                values,
            )

    def test_rejected_candidates_remain_unfilled(self):
        for project_id in (
            "proj-87",
            "proj-106",
            "proj-171",
            "proj-259",
        ):
            row = self.rows[project_id]
            self.assertIsNone(row["input_year"])
            self.assertIsNone(row["input_quarter"])


if __name__ == "__main__":
    unittest.main()
