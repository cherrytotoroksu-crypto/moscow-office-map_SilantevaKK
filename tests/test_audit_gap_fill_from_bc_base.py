import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from audit_gap_fill_from_bc_base import audit  # noqa: E402


class GapFillIdentityGuardrailTests(unittest.TestCase):
    def test_same_address_and_coordinates_do_not_override_name_mismatch(self):
        target = {
            "canonical_project_id": "target-1",
            "canonical_building_id": "target-1-bld",
            "canonical_name": "Башня на Набережной",
            "raw_name": "Башня на Набережной",
            "aliases": [],
            "entity_role": "host_building",
            "public_visibility": "public",
            "duplicate_of": None,
            "address": "Пресненская наб., 10",
            "latitude": 55.75,
            "longitude": 37.54,
            "cls": "A",
            "gba": None,
            "gla": None,
            "construction_start_year": None,
            "input_year": None,
        }
        source = {
            "no": 1,
            "name": "Бизнес-центр",
            "name_src": "Бизнес-центр",
            "address": "Пресненская наб., 10",
            "lat": 55.75,
            "lng": 37.54,
            "year": 2014,
        }

        report = audit([target], [source])

        self.assertEqual(report["candidate_count"], 0)


if __name__ == "__main__":
    unittest.main()
