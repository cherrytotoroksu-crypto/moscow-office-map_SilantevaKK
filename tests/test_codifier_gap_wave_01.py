import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load(relative):
    return json.loads((ROOT / relative).read_text(encoding="utf-8-sig"))


class CodifierGapWave01Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.layer = {row["canonical_project_id"]: row for row in load("data/all_projects_layer.json")}
        cls.evidence = load("data/qa/codifier_gap_wave_01_20260822.json")

    def test_stone_presnya_uses_building_and_rentable_area(self):
        row = self.layer["proj-1"]
        self.assertEqual((row["gba"], row["gla"]), (16277, 13338))
        self.assertIn("ibcrealestate.ru", row["qa_notes"])
        self.assertIn("of.ru", row["qa_notes"])

    def test_plaza_technopark_has_two_matching_area_sources(self):
        row = self.layer["proj-85"]
        self.assertEqual((row["gba"], row["gla"]), (32138, 23358))
        self.assertIn("plazatechnopark.ru", row["qa_notes"])
        self.assertIn("morrowgroup.ru", row["qa_notes"])

    def test_evidence_preserves_before_values_and_conflicts(self):
        self.assertEqual(len(self.evidence["applied"]), 2)
        self.assertEqual(len(self.evidence["deferred_conflicts"]), 4)
        presnya = next(row for row in self.evidence["applied"] if row["canonical_project_id"] == "proj-1")
        self.assertEqual(presnya["before"]["gba"], 15000)
        self.assertGreaterEqual(len(presnya["sources"]), 2)


if __name__ == "__main__":
    unittest.main()
