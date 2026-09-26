import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class SilverFountainGlaFillTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        rows = json.loads((ROOT / "data" / "all_projects_layer.json").read_text(encoding="utf-8"))
        cls.row = next(r for r in rows if r["canonical_project_id"] == "proj-20")
        classifier = json.loads((ROOT / "data" / "unified_classifier_audited_2026-08-27.json").read_text(encoding="utf-8"))
        cls.unified = next(r for r in classifier["records"] if r["unified_id"] == "UC-OBJ-0058")

    def test_current_asset_manager_gla_is_used(self):
        self.assertEqual(self.row["gla"], 18717.0)
        self.assertEqual(self.unified["gla"], 18717.0)
        self.assertIn("2026-04-30", self.row["qa_notes"])
        self.assertIn("wimsavings.ru", self.row["qa_notes"])

    def test_precise_gba_and_address_are_not_overwritten_by_rounded_or_conflicting_values(self):
        self.assertEqual(self.row["gba"], 21403.0)
        self.assertEqual(self.row["address"], "ул. Новоалексеевская, 16, корпус 5")
        self.assertTrue(self.unified["needs_review"])
        self.assertEqual(self.unified["review_reason"], "address_corpus_1_vs_5")

    def test_unsupported_commissioning_quarter_is_not_restored(self):
        self.assertEqual(self.unified["commission_year"], 2025)
        self.assertIsNone(self.unified["commission_quarter"])
        self.assertEqual(self.unified["layer_status"], "Введён")


if __name__ == "__main__":
    unittest.main()
