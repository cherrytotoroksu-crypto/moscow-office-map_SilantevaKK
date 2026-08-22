"""Regression coverage for AUDIT-008 (Manufaqtury / Poklonka Place).

The three historical rows represent one flex project, while their two
coordinate pairs remain separate building candidates until a building-level
source resolves them. The fix flags legacy rows; it does not collapse points.
"""
import json
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from build_all_projects_layer import DUPLICATE_GROUPS, STRUCTURED_DUPLICATE_GROUPS

LAYER_PATH = REPO_ROOT / "data" / "all_projects_layer.json"
PROJECT_IDS = {"proj-83", "proj-84", "proj-174"}
EXPECTED_COORDINATES = {
    (55.737258, 37.534514),
    (55.736179, 37.533194),
}
EVIDENCE_URLS = (
    "https://cntez.ru/manufaqtury",
    "https://poklonka-place.com/",
)


@unittest.skipUnless(LAYER_PATH.exists(), "all_projects_layer.json not present")
class ManufaqturyPoklonkaAudit008Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        records = json.loads(LAYER_PATH.read_text(encoding="utf-8-sig"))
        cls.rows = {
            row["canonical_project_id"]: row
            for row in records
            if row["canonical_project_id"] in PROJECT_IDS
        }

    def test_all_three_rows_are_retained_under_one_canonical_project(self):
        self.assertEqual(set(self.rows), PROJECT_IDS)
        self.assertIsNone(self.rows["proj-83"]["duplicate_of"])
        self.assertEqual(self.rows["proj-83"]["legacy_ids"], ["proj-84", "proj-174"])
        for legacy_id in ("proj-84", "proj-174"):
            self.assertEqual(self.rows[legacy_id]["duplicate_of"], "proj-83")

    def test_two_coordinate_candidates_are_not_collapsed(self):
        coordinates = {
            (row["latitude"], row["longitude"])
            for row in self.rows.values()
        }
        self.assertEqual(coordinates, EXPECTED_COORDINATES)

    def test_qa_notes_contain_two_sources_date_and_non_collapse_rule(self):
        for project_id, row in self.rows.items():
            notes = row["qa_notes"]
            self.assertIn("AUDIT-008", notes, project_id)
            self.assertIn("2026-08-22", notes, project_id)
            self.assertIn("не схлопывать", notes, project_id)
            for url in EVIDENCE_URLS:
                self.assertIn(url, notes, project_id)

    def test_fix_survives_registry_regeneration(self):
        self.assertEqual(DUPLICATE_GROUPS["proj-83"], ["proj-84", "proj-174"])
        self.assertIn("proj-83", STRUCTURED_DUPLICATE_GROUPS)


if __name__ == "__main__":
    unittest.main()
