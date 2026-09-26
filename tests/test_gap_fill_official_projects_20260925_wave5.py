import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class OfficialProjectsGapFillWave5Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        rows = json.loads(
            (ROOT / "data" / "all_projects_layer.json").read_text(encoding="utf-8")
        )
        cls.rows = {row.get("canonical_project_id"): row for row in rows}
        cls.dates = json.loads(
            (ROOT / "data" / "building_dates.json").read_text(encoding="utf-8")
        )
        classifier = json.loads(
            (ROOT / "data" / "unified_classifier_audited_2026-08-27.json").read_text(
                encoding="utf-8"
            )
        )
        cls.classifier = {
            row.get("unified_id"): row for row in classifier.get("records", [])
        }

    def test_orbital_2_year_is_filled_without_invented_quarter(self):
        row = self.rows["proj-168"]
        self.assertEqual(row["input_year"], 2027)
        self.assertIsNone(row["input_quarter"])
        self.assertEqual(row["input_date_kind"], "planned")
        self.assertIn("ibcrealestate.ru", row["qa_notes"])
        self.assertIn("core-xp.ru", row["qa_notes"])

    def test_mozhayskiy_val_is_no_longer_marked_commissioned(self):
        row = self.rows["proj-add-mozhayskiy-val-7-20260925"]
        self.assertEqual(row["project_status"], "Строится")
        self.assertEqual(row["input_year"], 2027)
        self.assertIsNone(row["input_quarter"])
        self.assertEqual(row["input_date_kind"], "planned")

    def test_building_dates_are_synchronized(self):
        for key, project_id in (
            ("orbital-2", "proj-168"),
            ("можайский вал, вл. 7", "proj-add-mozhayskiy-val-7-20260925"),
        ):
            row = self.dates[key]
            self.assertEqual(row["canonical_project_id"], project_id)
            self.assertEqual(row["commission_year"], 2027)
            self.assertIsNone(row["commission_q"])

    def test_classifier_does_not_restore_unsupported_quarter_or_status(self):
        orbital = self.classifier["UC-OBJ-0104"]
        self.assertEqual(orbital["commission_year"], 2027)
        self.assertIsNone(orbital["commission_quarter"])
        mozhayskiy = self.classifier["UC-OBJ-ADD-356"]
        self.assertEqual(mozhayskiy["commission_year"], 2027)
        self.assertEqual(mozhayskiy["status"], "Строящийся")
        self.assertEqual(mozhayskiy["layer_status"], "Строится")

    def test_rejected_conflicts_remain_empty(self):
        for project_id in ("proj-95", "proj-96", "proj-279"):
            row = self.rows[project_id]
            if project_id in ("proj-95", "proj-279"):
                self.assertIsNone(row["gla"])
            if project_id == "proj-96":
                self.assertIsNone(row["input_year"])


if __name__ == "__main__":
    unittest.main()
