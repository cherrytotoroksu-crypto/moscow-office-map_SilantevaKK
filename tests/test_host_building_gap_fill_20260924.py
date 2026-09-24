import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class HostBuildingGapFillTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows = json.loads((ROOT / "data" / "all_projects_layer.json").read_text(encoding="utf-8"))

    def row(self, project_id):
        matches = [row for row in self.rows if row.get("canonical_project_id") == project_id]
        self.assertEqual(len(matches), 1)
        return matches[0]

    def test_sadovaya_plaza_verified_fields(self):
        row = self.row("cwhost-0015")
        self.assertEqual((row["gba"], row["gla"], row["input_year"]), (16250, 11978, 2002))

    def test_white_stone_verified_fields(self):
        row = self.row("cwhost-0045")
        self.assertEqual((row["gba"], row["gla"], row["input_year"]), (49520, 39698, 2005))

    def test_conflicting_candidates_stay_unfilled(self):
        for project_id in ("cwhost-0025", "cwhost-0051"):
            row = self.row(project_id)
            self.assertIsNone(row["gba"])


if __name__ == "__main__":
    unittest.main()
