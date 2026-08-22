"""AUDIT-005 (CODEX_AUDIT_REQUEST_2026-08-22.md): Multispace Павелецкая had
its address copy-pasted from Multispace Динамо in data/coworking_*.json.
Fixed 2026-08-22 for Q4 2025 / Q1 2026 / Q2 2026 — pins the corrected
address/coordinates and that it never collides with Multispace Динамо again.
"""
import json
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

CORRECT_ADDRESS = "1-й Щипковский переулок, 5"
CORRECT_LAT = 55.722593
CORRECT_LNG = 37.632035
QUARTERS = ("202512", "202603", "202606")


class MultispacePaveletskayaAddressFixTests(unittest.TestCase):
    def _load(self, quarter):
        path = REPO_ROOT / "data" / f"coworking_{quarter}.json"
        if not path.exists():
            self.skipTest(f"{path.name} not present")
        return json.loads(path.read_text(encoding="utf-8-sig"))

    def _find(self, records, name):
        matches = [r for r in records if r.get("name") == name]
        self.assertEqual(len(matches), 1, f"expected exactly one {name!r} record")
        return matches[0]

    def test_address_corrected_in_all_three_quarters(self):
        for q in QUARTERS:
            records = self._load(q)
            pavel = self._find(records, "Multispace Павелецкая")
            self.assertEqual(pavel["address"], CORRECT_ADDRESS, f"quarter {q}")

    def test_coordinates_match_shchipkovsky_pereulok_in_all_three_quarters(self):
        # Q4 2025 (202512) и Q2 2026 (202606) уже были верны — сохранены.
        # Q1 2026 (202603) был скопирован с Multispace Динамо — исправлен.
        for q in QUARTERS:
            records = self._load(q)
            pavel = self._find(records, "Multispace Павелецкая")
            self.assertAlmostEqual(pavel["lat"], CORRECT_LAT, places=4, msg=f"quarter {q}")
            self.assertAlmostEqual(pavel["lng"], CORRECT_LNG, places=4, msg=f"quarter {q}")

    def test_q1_2026_records_the_previous_wrong_coordinates(self):
        records = self._load("202603")
        pavel = self._find(records, "Multispace Павелецкая")
        self.assertIn("prev_lat", pavel)
        self.assertIn("prev_lng", pavel)
        # старые координаты были координатами Multispace Динамо в том же квартале
        dinamo = self._find(records, "Multispace Динамо")
        self.assertAlmostEqual(pavel["prev_lat"], dinamo["lat"], places=3)
        self.assertAlmostEqual(pavel["prev_lng"], dinamo["lng"], places=3)

    def test_source_and_verification_date_recorded(self):
        for q in QUARTERS:
            records = self._load(q)
            pavel = self._find(records, "Multispace Павелецкая")
            self.assertIn("address_fix_source", pavel)
            self.assertIn("2026-08-22", pavel["address_fix_source"])
            self.assertIn("AUDIT-005", pavel["address_fix_source"])

    def test_never_collides_with_multispace_dinamo_address_or_coords(self):
        for q in QUARTERS:
            records = self._load(q)
            pavel = self._find(records, "Multispace Павелецкая")
            dinamo = self._find(records, "Multispace Динамо")
            self.assertNotEqual(pavel["address"], dinamo["address"], f"quarter {q}")
            self.assertNotEqual(
                (round(pavel["lat"], 4), round(pavel["lng"], 4)),
                (round(dinamo["lat"], 4), round(dinamo["lng"], 4)),
                f"quarter {q}: Павелецкая and Динамо still share coordinates",
            )

    def test_multispace_pavel_and_dinamo_stay_separate_ids(self):
        # явное требование: не объединять эти два coworking-объекта
        for q in QUARTERS:
            records = self._load(q)
            pavel = self._find(records, "Multispace Павелецкая")
            dinamo = self._find(records, "Multispace Динамо")
            self.assertNotEqual(pavel.get("id"), dinamo.get("id"), f"quarter {q}")


if __name__ == "__main__":
    unittest.main()
