import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class LunarDuplicateResolutionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        rows = json.loads((ROOT / "data" / "all_projects_layer.json").read_text(encoding="utf-8"))
        cls.by_id = {row["canonical_project_id"]: row for row in rows}
        cls.dates = json.loads((ROOT / "data" / "building_dates.json").read_text(encoding="utf-8"))
        classifier = json.loads(
            (ROOT / "data" / "unified_classifier_audited_2026-08-27.json").read_text(
                encoding="utf-8"
            )
        )
        cls.classifier = {row["unified_id"]: row for row in classifier["records"]}

    def test_proj_80_is_the_single_live_lunar_module_b_record(self):
        canonical = self.by_id["proj-80"]
        duplicate = self.by_id["proj-14"]
        self.assertIsNone(canonical["duplicate_of"])
        self.assertIn("proj-14", canonical["legacy_ids"])
        self.assertEqual(duplicate["duplicate_of"], "proj-80")
        for field in ("project_no", "subid", "address", "latitude", "longitude"):
            self.assertEqual(duplicate[field], canonical[field])

    def test_official_date_and_areas_are_synchronized(self):
        for project_id in ("proj-14", "proj-80"):
            row = self.by_id[project_id]
            self.assertEqual((row["input_year"], row["input_quarter"]), (2024, 3))
            self.assertEqual(row["input_date_kind"], "confirmed")
            self.assertEqual(row["gba"], 13431.0)
            self.assertAlmostEqual(row["gla"], 9941.78, places=2)
            self.assertIn("https://hutton.ru/offices/lunar", row["qa_notes"])
            self.assertIn("ZaPQcCSB9MmcVwe7X0LNBSlWtesHV9V0SuOX2542.pdf", row["qa_notes"])

    def test_date_aliases_point_to_the_canonical_record(self):
        for key in ("lunar", "lunar модуль в"):
            record = self.dates[key]
            self.assertEqual(record["canonical_project_id"], "proj-80")
            self.assertEqual(record["commission_year"], 2024)
            self.assertEqual(record["commission_q"], "202409")
            self.assertIn("hutton.ru", record["source"])

    def test_classifier_uses_official_values_and_is_not_ambiguous(self):
        record = self.classifier["UC-OBJ-0745"]
        self.assertEqual(record["legacy_ids"], ["proj-14", "proj-80"])
        self.assertEqual((record["commission_year"], record["commission_quarter"]), (2024, 3))
        self.assertEqual(record["gba"], 13431.0)
        self.assertAlmostEqual(record["gla"], 9941.78, places=2)
        self.assertFalse(record["needs_review"])
        self.assertIsNone(record["review_reason"])


if __name__ == "__main__":
    unittest.main()
