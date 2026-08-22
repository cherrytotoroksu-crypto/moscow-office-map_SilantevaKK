"""2026-08-22: wide check of the whole Q1 2024 (202403) quarter, requested
after the STONE Дмитровская fix, found the same contamination pattern
(a trailing garbage row per building leaking a subtotal's block/area/floor
into the lots array) across ~32 buildings, plus 3 fully-synthetic
top-level "buildings" (А, В+, Общий итог) that are class/grand-total
subtotal rows promoted to building keys by mistake. All garbage rows are
flagged (qa_flag), never deleted or given fabricated numbers — only
STONE Дмитровская's summary needed an actual price/volume/weight fix
(everything else recomputed within rounding noise and was reverted to
avoid overwriting legitimately-computed values with noise).
"""
import json
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
LOTS_PATH = REPO_ROOT / "data" / "lots_202403.json"
BUILDINGS_PATH = REPO_ROOT / "data" / "buildings_202403.json"

PURE_GARBAGE_KEYS = {"А", "В+", "Общий итог"}


@unittest.skipUnless(LOTS_PATH.exists() and BUILDINGS_PATH.exists(), "2024-Q1 files not present")
class Quarter202403WideAnomalyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lots = json.loads(LOTS_PATH.read_text(encoding="utf-8-sig"))
        cls.buildings = json.loads(BUILDINGS_PATH.read_text(encoding="utf-8-sig"))

    def test_pure_garbage_keys_are_fully_flagged(self):
        for key in PURE_GARBAGE_KEYS:
            self.assertIn(key, self.lots)
            for r in self.lots[key]:
                self.assertIn("qa_flag", r, f"{key}: unflagged row")

    def test_at_least_30_garbage_rows_flagged_across_the_file(self):
        flagged = sum(1 for rows in self.lots.values() for r in rows if "qa_flag" in r)
        self.assertGreaterEqual(flagged, 30)

    def test_flagged_rows_are_never_deleted_and_never_given_a_fabricated_price(self):
        for name, rows in self.lots.items():
            for r in rows:
                if "qa_flag" in r and name not in PURE_GARBAGE_KEYS:
                    self.assertEqual(r["price"], 0)
                    self.assertEqual(r["total"], 0)

    def test_only_stone_dmitrovskaya_building_summary_was_corrected(self):
        # остальные "похожие" пересчёты оказались шумом округления, не багом —
        # откачены; только у STONE Дмитровская была реальная контаминация.
        corrected = [b for b in self.buildings if "prev_price" in b]
        names = {b["name"] for b in corrected}
        self.assertEqual(names, {"STONE Дмитровская"})

    def test_stone_dmitrovskaya_weight_no_longer_equals_garbage_block_id(self):
        r = next(b for b in self.buildings if b["name"] == "STONE Дмитровская")
        self.assertNotEqual(r["weight"], 5003121000.0)
        self.assertEqual(r["prev_weight"], 5003121000.0)


if __name__ == "__main__":
    unittest.main()
