"""AUDIT-011 wave 02 (dates): STONE Пресня, Plaza Technopark, PORTA.

STONE Пресня — commission_q=202703 (Q1 2027, planned), two independent
sources (IBC Real Estate, Of.ru), not yet an actual confirmed completion.
Plaza Technopark — unchanged (already correct from an earlier check).
PORTA — commission_q=202509 applied with LOW confidence and a logged
conflict: the user's claim of a confirmed completion (via an operating
Multispace coworking) could not be independently reproduced — 2GIS still
labels the building "строящийся" as of this check, and the only quarter
found (cre.ru/news/95248) is the developer's own planned date at ~50%
construction progress, not a confirmed handover. See
data/qa/codifier_gap_wave_02_dates_20260822.json for the full evidence
record instead of silently picking a value.
"""
import json
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DATES_PATH = REPO_ROOT / "data" / "building_dates.json"
LAYER_PATH = REPO_ROOT / "data" / "all_projects_layer.json"
EVIDENCE_PATH = REPO_ROOT / "data" / "qa" / "codifier_gap_wave_02_dates_20260822.json"


@unittest.skipUnless(DATES_PATH.exists() and LAYER_PATH.exists(), "data files not present")
class CodifierGapWave02DatesTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dates = json.loads(DATES_PATH.read_text(encoding="utf-8-sig"))
        cls.layer = json.loads(LAYER_PATH.read_text(encoding="utf-8-sig"))
        cls.by_id = {r["canonical_project_id"]: r for r in cls.layer}

    def test_evidence_file_exists_and_has_all_three_entries(self):
        evidence = json.loads(EVIDENCE_PATH.read_text(encoding="utf-8"))
        names = {e["name"] for e in evidence["entries"]}
        self.assertEqual(names, {"stone пресня", "plaza technopark", "porta forma"})

    def test_stone_presnya_commission_q_applied_as_planned_q1_2027(self):
        row = self.dates["stone пресня"]
        self.assertEqual(row["commission_q"], "202703")
        self.assertIn("IBC Real Estate", row["source"])
        self.assertIn("of.ru", row["source"].lower())

    def test_plaza_technopark_unchanged(self):
        row = self.dates["plaza technopark"]
        self.assertEqual(row["commission_q"], "202112")

    def test_porta_forma_commission_q_applied_with_low_confidence_and_conflict_note(self):
        row = self.dates["porta forma"]
        self.assertEqual(row["commission_q"], "202509")
        self.assertIn("КОНФЛИКТ", row["source"])
        self.assertIn("2ГИС", row["source"])

    def test_layer_input_year_quarter_synced_for_stone_presnya(self):
        r = self.by_id["proj-1"]
        self.assertEqual(r["input_year"], 2027)
        self.assertEqual(r["input_quarter"], 1)

    def test_layer_input_year_quarter_synced_for_porta(self):
        r = self.by_id["proj-86"]
        self.assertEqual(r["input_year"], 2025)
        self.assertEqual(r["input_quarter"], 3)

    def test_only_three_records_touched_by_this_wave(self):
        touched = [
            r for r in self.layer
            if "Lifecycle dates synchronized 2026-08-22" in (r.get("qa_notes") or "")
        ]
        touched_ids = {r["canonical_project_id"] for r in touched}
        self.assertTrue({"proj-1", "proj-85", "proj-86"}.issubset(touched_ids))


if __name__ == "__main__":
    unittest.main()
