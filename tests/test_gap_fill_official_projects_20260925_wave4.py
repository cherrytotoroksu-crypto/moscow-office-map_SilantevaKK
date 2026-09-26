import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class OfficialProjectsGapFillWave4Tests(unittest.TestCase):
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
        for project_id in ("proj-173", "proj-234"):
            row = self.rows[project_id]
            self.assertEqual(row["input_year"], 2026)
            self.assertIsNone(row["input_quarter"])
            self.assertEqual(row["input_date_kind"], "planned")

    def test_building_dates_are_synchronized(self):
        for key, project_id in (("rail.a", "proj-173"), ("мфк юг", "proj-234")):
            row = self.dates[key]
            self.assertEqual(row["canonical_project_id"], project_id)
            self.assertEqual(row["commission_year"], 2026)
            self.assertIsNone(row["commission_q"])

    def test_area_fills_preserve_object_grain(self):
        self.assertEqual(self.rows["proj-281"]["gla"], 7300)
        self.assertIsNone(self.rows["proj-281"]["gba"])
        self.assertEqual(
            (self.rows["proj-282"]["gba"], self.rows["proj-282"]["gla"]),
            (77315, 57924),
        )
        self.assertEqual(self.rows["proj-283"]["gba"], 23870.84)
        self.assertIsNone(self.rows["proj-283"]["gla"])

    def test_qoob_later_registry_review_uses_exact_object_date(self):
        row = self.rows["proj-171"]
        self.assertEqual((row["input_year"], row["input_quarter"]), (2026, 3))
        self.assertEqual(row["input_date_kind"], "planned")


if __name__ == "__main__":
    unittest.main()
