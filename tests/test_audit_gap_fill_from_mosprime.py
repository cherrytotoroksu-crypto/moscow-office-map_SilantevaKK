import unittest
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from audit_gap_fill_from_mosprime import audit


class MosPrimeGapFillGuardrailTests(unittest.TestCase):
    def test_same_address_and_coordinates_do_not_override_name_mismatch(self):
        target = {
            "canonical_project_id": "target-1",
            "canonical_building_id": "building-1",
            "canonical_name": "Башня на набережной B",
            "raw_name": "Башня на набережной B",
            "aliases": [],
            "entity_role": "host_building",
            "public_visibility": "public",
            "duplicate_of": None,
            "address": "Пресненская наб., 8",
            "latitude": 55.748,
            "longitude": 37.538,
            "gba": None,
            "input_year": None,
            "cls": "A",
        }
        source = {
            "id": 1,
            "name": "Бизнес-центр",
            "address": "Пресненская наб., 8",
            "lat": 55.748,
            "lng": 37.538,
            "year": 2014,
            "total_area": 10000,
            "source_url": "https://example.test/card",
        }
        self.assertEqual(audit([target], [source])["candidate_count"], 0)

    def test_reviewed_source_conflict_is_not_reproposed(self):
        target = {
            "canonical_project_id": "target-1",
            "canonical_building_id": "building-1",
            "canonical_name": "Авион",
            "raw_name": "Авион",
            "aliases": [],
            "entity_role": "host_building",
            "public_visibility": "public",
            "duplicate_of": None,
            "address": "Ленинградский просп., 47, стр. 2, Москва",
            "latitude": 55.799088,
            "longitude": 37.530839,
            "gba": None,
            "input_year": 1964,
            "cls": "B+",
        }
        source = {
            "id": 272,
            "name": "Авион",
            "address": "Ленинградский просп., 47, стр. 2, Москва",
            "lat": 55.799088,
            "lng": 37.530839,
            "year": 1964,
            "total_area": 16667,
            "source_url": "https://example.test/avion",
        }
        report = audit([target], [source], reviewed_rejections={"target-1"})
        self.assertEqual(report["candidate_count"], 0)
        self.assertEqual(report["rejected"]["reviewed_source_conflict"], 1)


if __name__ == "__main__":
    unittest.main()
