import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class OfficialProjectsGapFillWave10Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        rows = json.loads((ROOT / "data/all_projects_layer.json").read_text(encoding="utf-8"))
        cls.rows = {row.get("canonical_project_id"): row for row in rows}
        cls.dates = json.loads((ROOT / "data/building_dates.json").read_text(encoding="utf-8"))
        classifier = json.loads(
            (ROOT / "data/unified_classifier_audited_2026-08-27.json").read_text(encoding="utf-8")
        )
        cls.classifier = {row.get("unified_id"): row for row in classifier.get("records", [])}

    def test_current_registry_dates_are_applied_as_planned(self):
        expected = {
            "proj-136": (2028, 2),
            "proj-171": (2026, 3),
        }
        for project_id, date in expected.items():
            row = self.rows[project_id]
            self.assertEqual((row["input_year"], row["input_quarter"]), date)
            self.assertEqual(row["input_date_kind"], "planned")
            self.assertEqual(row["project_status"], "Строится")
            self.assertIn("xn--80az8a.xn--d1aqf.xn--p1ai", row["qa_notes"])

    def test_building_dates_use_quarter_end_convention(self):
        expected = {
            "k-city": ("proj-136", 2028, "202806"),
            "qoob": ("proj-171", 2026, "202609"),
        }
        for key, values in expected.items():
            row = self.dates[key]
            self.assertEqual(
                (row["canonical_project_id"], row["commission_year"], row["commission_q"]),
                values,
            )

    def test_classifier_uses_current_registry_quarters(self):
        self.assertEqual(
            (self.classifier["UC-OBJ-0123"]["commission_year"], self.classifier["UC-OBJ-0123"]["commission_quarter"]),
            (2028, 2),
        )
        self.assertEqual(
            (self.classifier["UC-OBJ-0056"]["commission_year"], self.classifier["UC-OBJ-0056"]["commission_quarter"]),
            (2026, 3),
        )
        for unified_id in ("UC-OBJ-0123", "UC-OBJ-0056"):
            self.assertFalse(self.classifier[unified_id]["needs_review"])
            self.assertIsNone(self.classifier[unified_id]["review_reason"])

    def test_prior_audit_history_is_preserved(self):
        self.assertIn("UC-OBJ-ADD-207", self.classifier["UC-OBJ-0123"]["classification_note"])
        self.assertIn("RBC", self.classifier["UC-OBJ-0123"]["layer_qa_notes"])
        self.assertIn("IPG.Estate", self.classifier["UC-OBJ-0056"]["layer_qa_notes"])
        self.assertIn("первый бетон", self.dates["qoob"]["source"])

    def test_qoob_zos_does_not_become_confirmed_commissioning(self):
        row = self.rows["proj-171"]
        self.assertEqual(row["input_date_kind"], "planned")
        self.assertEqual(row["project_status"], "Строится")
        self.assertIn("ZOS", row["qa_notes"])


if __name__ == "__main__":
    unittest.main()
