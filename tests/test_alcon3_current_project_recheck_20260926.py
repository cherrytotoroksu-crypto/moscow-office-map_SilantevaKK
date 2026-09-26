import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class Alcon3CurrentProjectRecheckTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        rows = json.loads((ROOT / "data" / "all_projects_layer.json").read_text(encoding="utf-8"))
        cls.row = next(r for r in rows if r["canonical_project_id"] == "proj-95")
        classifier = json.loads((ROOT / "data" / "unified_classifier_audited_2026-08-27.json").read_text(encoding="utf-8"))
        cls.unified = next(r for r in classifier["records"] if r["unified_id"] == "UC-OBJ-0012")
        cls.date = json.loads((ROOT / "data" / "building_dates.json").read_text(encoding="utf-8"))["алкон 3"]

    def test_current_official_gba_replaces_obsolete_concept_area(self):
        self.assertEqual(self.row["gba"], 35865.0)
        self.assertEqual(self.unified["gba"], 35865.0)
        self.assertIn("https://alcongroup.ru/projects/alcon-3", self.row["qa_notes"])

    def test_unconfirmed_legacy_gla_is_not_reused(self):
        self.assertIsNone(self.row["gla"])
        self.assertIsNone(self.unified["gla"])
        self.assertIn("10,500", self.row["qa_notes"])
        self.assertIn("10,155", self.row["qa_notes"])

    def test_commissioning_quarter_conflict_stays_explicit(self):
        self.assertEqual(self.row["input_year"], 2023)
        self.assertIsNone(self.row["input_quarter"])
        self.assertEqual(self.date["commission_q"], "202307")
        self.assertEqual(self.date["commission_year"], 2023)
        self.assertTrue(self.unified["needs_review"])
        self.assertEqual(self.unified["review_reason"], "commission_quarter_q2_vs_q3")


if __name__ == "__main__":
    unittest.main()
