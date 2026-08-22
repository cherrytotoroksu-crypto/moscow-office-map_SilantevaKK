import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class AllProjectsDatesMigrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.layer = json.loads((ROOT / "data" / "all_projects_layer.json").read_text(encoding="utf-8"))
        cls.dates = json.loads((ROOT / "data" / "building_dates.json").read_text(encoding="utf-8"))

    def test_every_date_record_has_a_canonical_project_id(self):
        missing = [key for key, value in self.dates.items() if not value.get("canonical_project_id")]
        self.assertEqual(missing, [])

    def test_imperia_pilot_keeps_area_semantics(self):
        row = next(r for r in self.layer if r["canonical_project_id"] == "cwhost-0001")
        self.assertEqual(row["gba"], 203191)
        self.assertEqual(row["office_area"], 121497)
        self.assertIsNone(row["gla"])
        self.assertEqual(row["construction_start_year"], 2006)
        self.assertEqual(row["input_year"], 2011)
        self.assertIn("moscow-city.guide", row["qa_notes"])
        self.assertIn("imoscowcity.ru", row["qa_notes"])

    def test_unknown_quarter_is_not_fabricated_from_year(self):
        dates = self.dates["империя"]
        self.assertEqual(dates["commission_year"], 2011)
        self.assertIsNone(dates["commission_q"])
        self.assertIsNone(dates["construction_start_q"])


if __name__ == "__main__":
    unittest.main()
