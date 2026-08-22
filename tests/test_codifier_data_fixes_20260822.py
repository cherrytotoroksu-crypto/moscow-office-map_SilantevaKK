import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"


def load(name):
    return json.loads((DATA / name).read_text(encoding="utf-8-sig"))


class CodifierDataFixes20260822Tests(unittest.TestCase):
    def test_chelyabinsk_is_not_in_moscow_quarter_and_is_quarantined(self):
        active = load("coworking_202503.json")
        self.assertFalse(any(r.get("name") == "Челябинск" for r in active))
        quarantine = load("coworking_out_of_scope.json")
        row = next(r for r in quarantine if r.get("name") == "Челябинск")
        self.assertTrue(row["out_of_scope"])
        self.assertIn("praktik.work", row["qa_notes"])
        self.assertIn("2026-08-22", row["qa_notes"])

    def test_multispace_porta_has_one_confirmed_building_address(self):
        for filename in ("coworking_202509.json", "coworking_202512.json", "coworking_202603.json"):
            row = next(r for r in load(filename) if r.get("name") == "Multispace Porta")
            self.assertEqual(row["address"], "Москва, Заречная улица, 2/1")
            self.assertEqual((row["lat"], row["lng"]), (55.75048, 37.53953))
            self.assertIn("porta.moscow", row["qa_notes"])
            self.assertIn("prev_lat", row)

    def test_onegin_address_has_two_sources(self):
        row = next(r for r in load("coworking_202603.json") if r.get("name") == "Онегин PMG")
        self.assertEqual(row["address"], "Москва, улица Малая Полянка, 2")
        self.assertIn("pmg-office.ru", row["qa_notes"])
        self.assertIn("cian.ru", row["qa_notes"])


if __name__ == "__main__":
    unittest.main()
