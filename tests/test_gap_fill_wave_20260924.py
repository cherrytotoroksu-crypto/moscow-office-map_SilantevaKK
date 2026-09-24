import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class GapFillWave20260924Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows = json.loads((ROOT / "data" / "all_projects_layer.json").read_text(encoding="utf-8-sig"))
        cls.by_identity = {
            (row.get("canonical_project_id"), row.get("canonical_building_id")): row
            for row in cls.rows
        }
        cls.decisions = json.loads(
            (ROOT / "data" / "qa" / "gap_fill_wave_20260924.json").read_text(encoding="utf-8-sig")
        )

    def test_all_accepted_years_are_applied_to_exact_buildings(self):
        for decision in self.decisions["accepted"]:
            key = (decision["canonical_project_id"], decision["canonical_building_id"])
            row = self.by_identity[key]
            self.assertEqual(row["input_year"], decision["input_year"], key)
            self.assertIsNone(row["input_quarter"], key)
            self.assertEqual(row["input_date_kind"], "confirmed", key)
            self.assertIn("verified 2026-09-24", row.get("qa_notes") or "", key)

    def test_tower_on_embankment_generic_match_stays_unfilled(self):
        row = self.by_identity[("cwhost-0003", "cwhost-0003-bld")]
        self.assertIsNone(row["input_year"])

    def test_vivaldi_conflicting_areas_stay_unfilled(self):
        row = self.by_identity[("cwhost-0058", "cwhost-0058-bld")]
        self.assertIsNone(row["gba"])
        self.assertIsNone(row["gla"])


if __name__ == "__main__":
    unittest.main()
