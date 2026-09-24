import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class ProjectStatusSyncTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows = json.loads((ROOT / "data" / "all_projects_layer.json").read_text(encoding="utf-8"))

    def test_confirmed_commissioning_is_reflected_in_lifecycle_status(self):
        stale = [
            (row.get("canonical_project_id"), row.get("canonical_name"))
            for row in self.rows
            if row.get("public_visibility") == "public"
            and row.get("entity_role") == "office_project"
            and row.get("input_date_kind") == "confirmed"
            and row.get("input_year")
            and row.get("input_year") <= 2026
            and row.get("project_status") != "Введён"
        ]
        self.assertEqual(stale, [])


if __name__ == "__main__":
    unittest.main()
