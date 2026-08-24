import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class LiveSync20260824Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dates = json.loads((ROOT / "data/building_dates.json").read_text(encoding="utf-8-sig"))
        layer = json.loads((ROOT / "data/all_projects_layer.json").read_text(encoding="utf-8-sig"))
        cls.layer = {row["canonical_project_id"]: row for row in layer}

    def test_chalet_keeps_current_official_q2_2028(self):
        row = self.dates["chalet пятницкая 40"]
        self.assertEqual(row["commission_q"], "202806")
        self.assertIn("актуальный официальный сайт", row["qa_notes"])
        self.assertIn("не используются для текущего значения", row["qa_notes"])

    def test_river_park_source_trace_is_not_lost(self):
        notes = self.layer["proj-279"]["qa_notes"]
        self.assertIn("official River Park news", notes)
        self.assertIn("EISZH registry", notes)


if __name__ == "__main__":
    unittest.main()
