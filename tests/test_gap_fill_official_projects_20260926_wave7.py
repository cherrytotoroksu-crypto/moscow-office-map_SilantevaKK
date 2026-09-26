import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class OfficialProjectsGapFillWave7Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        rows = json.loads((ROOT / "data/all_projects_layer.json").read_text(encoding="utf-8"))
        cls.rows = {row.get("canonical_project_id"): row for row in rows}
        cls.dates = json.loads((ROOT / "data/building_dates.json").read_text(encoding="utf-8"))
        classifier = json.loads(
            (ROOT / "data/unified_classifier_audited_2026-08-27.json").read_text(encoding="utf-8")
        )
        cls.classifier = {row.get("unified_id"): row for row in classifier.get("records", [])}

    def test_slava_office_phase_is_confirmed_without_inventing_quarter(self):
        row = self.rows["proj-87"]
        self.assertEqual(row["project_status"], "Введён")
        self.assertEqual((row["input_year"], row["input_quarter"], row["input_date_kind"]), (2025, None, "confirmed"))
        self.assertIn("https://slava-moscow.com/about", row["qa_notes"])

    def test_aurus_official_planned_quarter_is_applied(self):
        row = self.rows["proj-259"]
        self.assertEqual((row["input_year"], row["input_quarter"], row["input_date_kind"]), (2031, 4, "planned"))
        self.assertIn("https://strana.com/msk/projects/premium/aurus/", row["qa_notes"])

    def test_building_dates_are_synchronized(self):
        self.assertEqual((self.dates["slava"]["commission_year"], self.dates["slava"]["commission_q"]), (2025, None))
        self.assertEqual((self.dates["aurus"]["commission_year"], self.dates["aurus"]["commission_q"]), (2031, "203112"))

    def test_classifier_matches_reviewed_status_and_precision(self):
        slava = self.classifier["UC-OBJ-ADD-184"]
        self.assertEqual((slava["status"], slava["commission_year"], slava["commission_quarter"]), ("Сданный", 2025, None))
        aurus = self.classifier["UC-OBJ-0374"]
        self.assertEqual((aurus["commission_year"], aurus["commission_quarter"]), (2031, 4))
        for row in (slava, aurus):
            self.assertFalse(row["needs_review"])
            self.assertIsNone(row["review_reason"])

    def test_unresolved_rows_remain_unfilled(self):
        unresolved = {
            "proj-19", "proj-22", "proj-33", "proj-96", "proj-98",
            "proj-136", "proj-171", "proj-260", "proj-264",
            "proj-add-luzhnetskaya-sminex-20260925",
        }
        for project_id in unresolved:
            self.assertIsNone(self.rows[project_id]["input_year"])


if __name__ == "__main__":
    unittest.main()
