import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"


def load(name):
    return json.loads((DATA / name).read_text(encoding="utf-8-sig"))


class CoworkingGapFill20260924Tests(unittest.TestCase):
    def test_afi_gallery_uses_verified_building_point(self):
        for period in ("202509", "202512", "202603", "202606"):
            row = next(r for r in load(f"coworking_{period}.json") if r.get("id") == 176)
            self.assertEqual(row["address"], "пл. Тверская Застава, 4")
            self.assertAlmostEqual(row["lat"], 55.775682)
            self.assertAlmostEqual(row["lng"], 37.581191)

    def test_duplicate_tariff_rows_are_not_normalized_without_user_data(self):
        expected_missing = {"202512": 3, "202603": 2}
        for period, expected in expected_missing.items():
            rows = [r for r in load(f"coworking_{period}.json") if r.get("id") == 84]
            self.assertGreater(len(rows), 1)
            self.assertEqual(sum(r.get("seats") is None for r in rows), expected)

    def test_latest_dubinin_rate_is_source_backed(self):
        row = next(r for r in load("coworking_202606.json") if r.get("id") == 157)
        self.assertEqual(row["seats"], 650)
        self.assertEqual(row["rate"], 70000.0)

    def test_unverified_sokolniki_address_stays_blank(self):
        row = next(r for r in load("coworking_202412.json") if r.get("id") == 23)
        self.assertEqual(row["address"], "")

    def test_canonical_rows_receive_verified_values(self):
        layer = load("all_projects_layer.json")
        by_id = {row.get("canonical_project_id"): row for row in layer}
        self.assertEqual(by_id["proj-176"]["address"], "пл. Тверская Застава, 4")
        self.assertEqual(by_id["proj-157"]["seats"], 650)
        self.assertEqual(by_id["proj-157"]["rate"], 70000.0)


if __name__ == "__main__":
    unittest.main()
