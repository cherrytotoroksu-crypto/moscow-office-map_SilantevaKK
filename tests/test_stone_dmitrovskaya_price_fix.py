"""2026-08-22: lots_202403.json "STONE Дмитровская" had 41 lots (floors
9-13, blocks SD-901..SD-1314) priced at 5000 руб/м2 vs the building's own
~296000-368000 range in the same file. Every one of those 41 blocks has a
matching row (same block id) in both the prior (202311) and following
(202410) quarter, showing a clean, consistent linear price trend
(~+19000 руб/м2 across the two quarters). Fixed by interpolating between
202311 and 202410 per block, per the user's explicit instruction to use
prior-quarter data and match by block/floor/area rather than invent a
number. A separate garbage row (numeric block id, floor=19473,
area=256914.2 m2) has no match in any quarter and was left in place with a
qa_flag instead of being deleted or given a fabricated price.
"""
import json
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
LOTS_PATH = REPO_ROOT / "data" / "lots_202403.json"
BUILDINGS_PATH = REPO_ROOT / "data" / "buildings_202403.json"

FIXED_BLOCKS = {
    "SD-901", "SD-903", "SD-904", "SD-906", "SD-908", "SD-909", "SD-910", "SD-912",
    "SD-1001", "SD-1002", "SD-1003", "SD-1004", "SD-1006", "SD-1009", "SD-1010", "SD-1014",
    "SD-1102", "SD-1103", "SD-1107", "SD-1108", "SD-1109", "SD-1110",
    "SD-1201", "SD-1202", "SD-1203", "SD-1205", "SD-1207", "SD-1208", "SD-1209", "SD-1210", "SD-1214",
    "SD-1301", "SD-1302", "SD-1303", "SD-1305", "SD-1307", "SD-1308", "SD-1309", "SD-1311", "SD-1313", "SD-1314",
}


@unittest.skipUnless(LOTS_PATH.exists() and BUILDINGS_PATH.exists(), "2024-Q1 files not present")
class StoneDmitrovskayaPriceFixTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lots = json.loads(LOTS_PATH.read_text(encoding="utf-8-sig"))["STONE Дмитровская"]
        buildings = json.loads(BUILDINGS_PATH.read_text(encoding="utf-8-sig"))
        cls.building = next(b for b in buildings if b["name"] == "STONE Дмитровская")

    def test_no_lot_still_priced_at_the_placeholder_value(self):
        for r in self.lots:
            self.assertNotEqual(r["price"], 5000, r["block"])

    def test_all_41_fixed_blocks_are_in_the_normal_range(self):
        fixed = [r for r in self.lots if r["block"] in FIXED_BLOCKS]
        self.assertEqual(len(fixed), 41)
        for r in fixed:
            self.assertGreater(r["price"], 250000, r["block"])
            self.assertLess(r["price"], 400000, r["block"])

    def test_fixed_lots_keep_previous_value_and_interpolation_source(self):
        fixed = [r for r in self.lots if r["block"] in FIXED_BLOCKS]
        for r in fixed:
            self.assertEqual(r["prev_price"], 5000, r["block"])
            self.assertIn("price_fix_source", r)
            self.assertIn("202311", r["price_fix_source"])
            self.assertIn("202410", r["price_fix_source"])

    def test_fixed_lots_total_recomputed_consistently(self):
        fixed = [r for r in self.lots if r["block"] in FIXED_BLOCKS]
        for r in fixed:
            self.assertEqual(r["total"], r["price"] * r["area"], r["block"])

    def test_garbage_row_flagged_not_deleted_not_fabricated(self):
        garbage = next(r for r in self.lots if r.get("area", 0) > 10000)
        self.assertEqual(garbage["price"], 0)
        self.assertIn("qa_flag", garbage)

    def test_building_price_no_longer_matches_garbage_row_area(self):
        # было: building.price == 256914 (== мусорная area 256914.2, усечено)
        self.assertNotEqual(self.building["price"], 256914)

    def test_building_price_matches_recomputed_weighted_average(self):
        priced = [r for r in self.lots if r.get("price") and r.get("area")]
        total_sum = sum(r["total"] for r in priced)
        area_sum = sum(r["area"] for r in priced)
        expected = round(total_sum / area_sum)
        self.assertEqual(self.building["price"], expected)

    def test_building_records_old_contaminated_price_and_source(self):
        self.assertEqual(self.building["prev_price"], 256914)
        self.assertIn("price_fix_source", self.building)


if __name__ == "__main__":
    unittest.main()
