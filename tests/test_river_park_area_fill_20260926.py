import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class RiverParkAreaFillTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.layer = {r["canonical_project_id"]: r for r in json.loads(
            (ROOT / "data" / "all_projects_layer.json").read_text(encoding="utf-8"))}
        cls.buildings = {r["id"]: r for r in json.loads(
            (ROOT / "data" / "buildings_202606.json").read_text(encoding="utf-8"))}
        classifier = json.loads((ROOT / "data" / "unified_classifier_audited_2026-08-27.json").read_text(encoding="utf-8"))
        cls.classifier = {r["unified_id"]: r for r in classifier["records"]}
        cls.dates = json.loads((ROOT / "data" / "building_dates.json").read_text(encoding="utf-8"))

    def test_official_areas_are_synchronized(self):
        for record in (self.layer["proj-279"], self.buildings[279], self.classifier["UC-OBJ-ADD-001"]):
            self.assertEqual(record["gba"], 10800.0)
            self.assertEqual(record["gla"], 8243.8)

    def test_commissioning_is_synchronized(self):
        row = self.layer["proj-279"]
        self.assertEqual((row["input_year"], row["input_quarter"]), (2026, 2))
        self.assertEqual(row["project_status"], "Введён")
        self.assertIn("77-05-013108-2026", row["qa_notes"])
        date = self.dates["river park коломенское"]
        self.assertEqual(date["canonical_project_id"], "proj-279")
        self.assertEqual((date["commission_year"], date["commission_q"]), (2026, "202604"))

    def test_address_conflict_remains_visible_without_coordinate_guessing(self):
        row = self.layer["proj-279"]
        self.assertEqual(row["address"], "ул. Корабельная, 3А")
        self.assertEqual((row["latitude"], row["longitude"]), (55.686558, 37.700056))
        self.assertIn("address 2", row["qa_notes"])
        unified = self.classifier["UC-OBJ-ADD-001"]
        self.assertTrue(unified["needs_review"])
        self.assertEqual(unified["review_reason"], "commissioned_address_conflict_3A_vs_2")


if __name__ == "__main__":
    unittest.main()
