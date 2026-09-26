import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class OfficialProjectsGapFillWave9Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        rows = json.loads((ROOT / "data/all_projects_layer.json").read_text(encoding="utf-8"))
        cls.rows = {row.get("canonical_project_id"): row for row in rows}
        cls.dates = json.loads((ROOT / "data/building_dates.json").read_text(encoding="utf-8"))
        classifier = json.loads(
            (ROOT / "data/unified_classifier_audited_2026-08-27.json").read_text(encoding="utf-8")
        )
        cls.classifier = {row.get("unified_id"): row for row in classifier.get("records", [])}

    def test_enthusiast_registry_date_is_applied_as_planned(self):
        row = self.rows["proj-264"]
        self.assertEqual(
            (row["input_year"], row["input_quarter"], row["input_date_kind"]),
            (2028, 2, "planned"),
        )
        self.assertEqual(row["project_status"], "Строится")
        self.assertIn("/объект/68926", row["qa_notes"])

    def test_enthusiast_building_date_uses_quarter_end_convention(self):
        record = self.dates["энтузиаст"]
        self.assertEqual(
            (record["commission_year"], record["commission_q"]),
            (2028, "202806"),
        )
        self.assertEqual(record["canonical_project_id"], "proj-264")

    def test_classifier_uses_developer_not_general_contractor(self):
        row = self.classifier["UC-OBJ-0389"]
        self.assertEqual(row["developer"], "Объект Гарант")
        self.assertEqual((row["commission_year"], row["commission_quarter"]), (2028, 2))
        self.assertIn("ТЭН", row["classification_note"])
        self.assertFalse(row["needs_review"])

    def test_remaining_phase_conflicts_stay_unfilled(self):
        for project_id in ("proj-33", "proj-98", "proj-136", "proj-260"):
            self.assertIsNone(self.rows[project_id]["input_year"])


if __name__ == "__main__":
    unittest.main()
