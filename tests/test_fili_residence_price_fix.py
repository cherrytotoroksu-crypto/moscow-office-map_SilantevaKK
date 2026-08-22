"""2026-08-22: Fili residence (Кастанаевская ул., 16с1, buildings_202606.json
id=124) had one lot ("опт, 7 этаж", 544 м2) priced at 229241213 руб/м2 —
~500x the neighboring lots (~430-450 тыс/м2), dragging the building's
weighted-average price to 102.7 млн/м2 on the map. Reported by the user
directly ("Фили что-то стоит 4,5 млн"). Fixed by dividing the bad lot's
price by 1000 (229241213 -> 229241, lands in the same range as its
siblings) and recomputing the building-level weighted price.
"""
import json
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
LOTS_PATH = REPO_ROOT / "data" / "lots_202606.json"
BUILDINGS_PATH = REPO_ROOT / "data" / "buildings_202606.json"


@unittest.skipUnless(LOTS_PATH.exists() and BUILDINGS_PATH.exists(), "Q2 2026 files not present")
class FiliResidencePriceFixTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lots = json.loads(LOTS_PATH.read_text(encoding="utf-8-sig"))["Fili residence"]
        buildings = json.loads(BUILDINGS_PATH.read_text(encoding="utf-8-sig"))
        cls.building = next(b for b in buildings if b["name"] == "Fili residence")

    def test_bad_lot_price_is_in_range_with_siblings(self):
        # соседние лоты: 447004, 431670, 429795 руб/м2
        prices = [r["price"] for r in self.lots]
        self.assertEqual(max(prices), 447004)
        for p in prices:
            self.assertLess(p, 500000, f"lot price {p} still looks like the parsing artifact")

    def test_fixed_lot_total_recomputed_consistently(self):
        fixed = next(r for r in self.lots if r.get("prev_price") == 229241213)
        self.assertEqual(fixed["price"], 229241)
        self.assertEqual(fixed["total"], fixed["price"] * fixed["area"])

    def test_fixed_lot_keeps_previous_wrong_value_and_source(self):
        fixed = next(r for r in self.lots if r.get("prev_price") == 229241213)
        self.assertEqual(fixed["prev_total"], 124707219872)
        self.assertIn("price_fix_source", fixed)
        self.assertIn("2026-08-22", fixed["price_fix_source"])

    def test_building_weighted_price_no_longer_absurd(self):
        self.assertLess(self.building["price"], 600000)
        self.assertGreater(self.building["price"], 300000)

    def test_building_price_matches_recomputed_weighted_average(self):
        total_sum = sum(r["total"] for r in self.lots)
        area_sum = sum(r["area"] for r in self.lots)
        expected = round(total_sum / area_sum)
        self.assertEqual(self.building["price"], expected)

    def test_building_records_old_absurd_price_and_source(self):
        self.assertEqual(self.building["prev_price"], 102768631)
        self.assertIn("price_fix_source", self.building)


if __name__ == "__main__":
    unittest.main()
