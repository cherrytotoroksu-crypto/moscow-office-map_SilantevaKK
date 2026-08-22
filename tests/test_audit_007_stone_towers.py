import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class Audit007StoneTowersTests(unittest.TestCase):
    def test_parent_and_towers_remain_distinct_pending_primary_area_register(self):
        rows = json.loads((ROOT / "data" / "all_projects_layer.json").read_text(encoding="utf-8-sig"))
        by_id = {r["canonical_project_id"]: r for r in rows}
        self.assertIn("proj-33", by_id)
        for tower_id in ("proj-88", "proj-89", "proj-90"):
            self.assertIn(tower_id, by_id)
        self.assertIsNone(by_id["proj-33"]["duplicate_of"])
        self.assertEqual(by_id["proj-33"]["entity_grain"], "project")


if __name__ == "__main__":
    unittest.main()
