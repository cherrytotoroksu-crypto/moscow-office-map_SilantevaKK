import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load(relative):
    return json.loads((ROOT / relative).read_text(encoding="utf-8-sig"))


class CodifierGapWave03GlaRecheckTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.layer = {row["canonical_project_id"]: row for row in load("data/all_projects_layer.json")}
        cls.evidence = load("data/qa/codifier_gap_wave_03_gla_recheck_20260824.json")

    def test_park_legends_b_plus_gla_has_two_independent_sources(self):
        row = self.layer["proj-103"]
        self.assertEqual((row["gba"], row["gla"]), (48000, 48000))
        self.assertIn("NF Group Research", row["qa_notes"])
        self.assertIn("IBC Real Estate/JLL", row["qa_notes"])
        self.assertGreaterEqual(row["source_count"], 2)

    def test_conflicting_records_remain_unfilled(self):
        self.assertIsNone(self.layer["proj-95"]["gla"])
        self.assertIsNone(self.layer["proj-102"]["gla"])
        deferred = {entry["canonical_project_id"] for entry in self.evidence["deferred"]}
        self.assertEqual(deferred, {"proj-95", "proj-102"})

    def test_evidence_is_backlog_track_not_point_audit(self):
        self.assertEqual(self.evidence["track"], "missing_data_backlog")
        self.assertEqual(len(self.evidence["applied"][0]["sources"]), 2)


if __name__ == "__main__":
    unittest.main()
