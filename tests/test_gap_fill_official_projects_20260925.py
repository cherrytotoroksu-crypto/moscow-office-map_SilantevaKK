import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class OfficialProjectsGapFillTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        rows = json.loads(
            (ROOT / "data" / "all_projects_layer.json").read_text(encoding="utf-8")
        )
        cls.rows = {row.get("canonical_project_id"): row for row in rows}
        cls.dates = json.loads(
            (ROOT / "data" / "building_dates.json").read_text(encoding="utf-8")
        )

    def test_official_developer_plans_are_applied(self):
        expected = {
            "proj-267": (2028, 3),
            "proj-273": (2028, 4),
        }
        for project_id, date in expected.items():
            row = self.rows[project_id]
            self.assertEqual((row["input_year"], row["input_quarter"]), date)
            self.assertEqual(row["input_date_kind"], "planned")

    def test_light_city_keeps_conflicting_quarter_empty(self):
        row = self.rows["proj-147"]
        self.assertEqual(row["input_year"], 2028)
        self.assertIsNone(row["input_quarter"])
        self.assertEqual(row["input_date_kind"], "planned")
        self.assertIn("Q1/January", row["qa_notes"])
        self.assertIn("Q2", row["qa_notes"])

    def test_building_dates_are_synchronized(self):
        expected = {
            "light city": ("proj-147", 2028, None),
            "level нижегородская": ("proj-267", 2028, "202809"),
            "плэйн (бывший — workplace авиационная)": ("proj-273", 2028, "202812"),
        }
        for key, values in expected.items():
            row = self.dates[key]
            self.assertEqual(
                (row["canonical_project_id"], row["commission_year"], row["commission_q"]),
                values,
            )


if __name__ == "__main__":
    unittest.main()
