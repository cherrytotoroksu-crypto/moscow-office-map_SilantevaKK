import json
import importlib.util
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load_migration_module():
    path = ROOT / "scripts" / "migrate_all_projects_dates.py"
    scripts_path = str(path.parent)
    if scripts_path not in sys.path:
        sys.path.insert(0, scripts_path)
    spec = importlib.util.spec_from_file_location("migrate_all_projects_dates", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


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

    def test_project_level_date_does_not_collapse_multi_building_project(self):
        migration = load_migration_module()
        layer = [
            {
                "entity_role": "office_project",
                "canonical_project_id": "proj-multi",
                "canonical_building_id": "building-a",
                "canonical_name": "Проект (А)",
                "raw_name": "Проект",
                "aliases": [],
            },
            {
                "entity_role": "office_project",
                "canonical_project_id": "proj-multi",
                "canonical_building_id": "building-b",
                "canonical_name": "Проект (Б)",
                "raw_name": "Проект",
                "aliases": [],
            },
        ]
        dates = {
            "проект": {
                "canonical_project_id": "proj-multi",
                "canonical_building_id": None,
                "construction_start_q": "202001",
                "start_q": None,
                "commission_q": None,
                "last_checked": "2026-09-24",
            }
        }

        matched, unmatched = migration.synchronize_dates(layer, dates)

        self.assertEqual(matched, 0)
        self.assertEqual(unmatched, ["проект"])
        self.assertTrue(all(row["construction_start_year"] is None for row in layer))


if __name__ == "__main__":
    unittest.main()
