import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from unified_building_identity import link_coworking_sites


class UnifiedBuildingIdentityPilotTests(unittest.TestCase):
    def setUp(self):
        self.host = {
            "canonical_project_id": "cwhost-0001",
            "canonical_building_id": "cwhost-0001-bld",
            "canonical_name": "Империя",
            "entity_role": "host_building",
            "address": "Пресненская наб., 6с2 (Москва-Сити)",
            "latitude": 55.748154,
            "longitude": 37.540236,
        }
        self.site = {
            "canonical_project_id": "proj-179",
            "canonical_building_id": None,
            "flex_site_label": "Империя",
            "entity_role": "coworking_site",
            "address": "Пресненская набережная, 6с2",
            "latitude": 55.748154,
            "longitude": 37.540236,
        }
        self.observation = {
            "id": 179,
            "bc": "Империя",
            "address": "Пресненская набережная, 6с2",
            "lat": 55.748154,
            "lng": 37.540236,
        }

    def test_imperia_pilot_links_site_to_physical_host(self):
        links, rejected = link_coworking_sites([self.host, self.site], [self.observation])
        self.assertEqual(links["proj-179"]["canonical_building_id"], "cwhost-0001-bld")
        self.assertEqual(rejected, {})

    def test_nearest_coordinate_without_exact_bc_never_links(self):
        wrong = dict(self.observation, bc="Другое здание")
        links, _ = link_coworking_sites([self.host, self.site], [wrong])
        self.assertEqual(links, {})

    def test_exact_bc_without_address_or_coordinate_corroboration_never_links(self):
        wrong = dict(self.observation, address="Другой адрес", lat=55.0, lng=37.0)
        links, rejected = link_coworking_sites([self.host, self.site], [wrong])
        self.assertEqual(links, {})
        self.assertIn("proj-179", rejected)


if __name__ == "__main__":
    unittest.main()
