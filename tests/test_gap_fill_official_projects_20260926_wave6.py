import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class OfficialProjectsGapFillWave6Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        rows = json.loads((ROOT / "data/all_projects_layer.json").read_text(encoding="utf-8"))
        cls.rows = {row.get("canonical_project_id"): row for row in rows}
        cls.dates = json.loads((ROOT / "data/building_dates.json").read_text(encoding="utf-8"))
        classifier = json.loads(
            (ROOT / "data/unified_classifier_audited_2026-08-27.json").read_text(encoding="utf-8")
        )
        cls.classifier = {row.get("unified_id"): row for row in classifier.get("records", [])}

    def test_euler_current_project_facts_replace_stale_values(self):
        row = self.rows["proj-250"]
        self.assertEqual(row["address"], "Береговой проезд, 1В")
        self.assertEqual(row["gba"], 23545)
        self.assertIsNone(row["gla"])
        self.assertEqual((row["input_year"], row["input_quarter"], row["input_date_kind"]), (2026, 3, "planned"))

    def test_year_only_fills_do_not_invent_quarters(self):
        expected = {
            "proj-add-krekshino-20260917": (2026, "planned"),
            "proj-57": (2024, "confirmed"),
            "proj-103": (2024, "confirmed"),
        }
        for project_id, (year, kind) in expected.items():
            row = self.rows[project_id]
            self.assertEqual(row["input_year"], year)
            self.assertIsNone(row["input_quarter"])
            self.assertEqual(row["input_date_kind"], kind)

    def test_berzarina_exact_address_and_gba_are_applied(self):
        row = self.rows["proj-57"]
        self.assertEqual(row["address"], "Берзарина ул., 32, стр. 4")
        self.assertEqual(row["gba"], 11894)
        self.assertIsNone(row["gla"])

    def test_building_dates_are_synchronized(self):
        expected = {
            "эйлер": ("proj-250", 2026, "202609"),
            "мфк крёкшино": ("proj-add-krekshino-20260917", 2026, None),
            "на берзарина": ("proj-57", 2024, None),
            "парк легенд класс в+": ("proj-103", 2024, None),
        }
        for key, values in expected.items():
            row = self.dates[key]
            self.assertEqual((row["canonical_project_id"], row["commission_year"], row["commission_q"]), values)

    def test_classifier_matches_reviewed_precision(self):
        euler = self.classifier["UC-OBJ-0064"]
        self.assertEqual((euler["address"], euler["gba"], euler["gla"]), ("Береговой проезд, 1В", 23545, None))
        self.assertEqual((euler["commission_year"], euler["commission_quarter"]), (2026, 3))
        self.assertEqual(self.classifier["UC-OBJ-ADD-354"]["commission_year"], 2026)
        self.assertIsNone(self.classifier["UC-OBJ-0315"]["commission_quarter"])
        self.assertEqual(self.classifier["UC-OBJ-ADD-194"]["commission_year"], 2024)

    def test_classifier_review_flags_match_actual_unresolved_conflicts(self):
        for unified_id in ("UC-OBJ-0064", "UC-OBJ-ADD-354"):
            self.assertTrue(self.classifier[unified_id]["needs_review"])
            self.assertTrue(self.classifier[unified_id]["review_reason"])
        for unified_id in ("UC-OBJ-0315", "UC-OBJ-ADD-194"):
            self.assertFalse(self.classifier[unified_id]["needs_review"])
            self.assertIsNone(self.classifier[unified_id]["review_reason"])

    def test_berzarina_classifier_keeps_duplicate_merge_history(self):
        note = self.classifier["UC-OBJ-0315"]["classification_note"]
        self.assertIn("UC-OBJ-ADD-180", note)
        self.assertIn("UC-OBJ-ADD-355", note)

    def test_known_conflicts_remain_unfilled(self):
        for project_id in ("proj-19", "proj-73", "proj-136"):
            self.assertIsNone(self.rows[project_id]["input_year"])
            self.assertIsNone(self.rows[project_id]["input_quarter"])


if __name__ == "__main__":
    unittest.main()
