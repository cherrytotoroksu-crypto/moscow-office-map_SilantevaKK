import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from recompute_geo import compute_geo


KNOWN_PLACEHOLDER_COORDS = {(55.755819, 37.617644)}


class AllProjectsGeoGapFillTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows = json.loads((ROOT / "data" / "all_projects_layer.json").read_text(encoding="utf-8"))

    def test_every_computable_public_geo_value_is_present(self):
        missing = []
        for row in self.rows:
            if row.get("public_visibility") != "public" or row.get("duplicate_of"):
                continue
            if row.get("latitude") is None or row.get("longitude") is None:
                continue
            if (row["latitude"], row["longitude"]) in KNOWN_PLACEHOLDER_COORDS:
                continue
            computed = compute_geo(row["latitude"], row["longitude"])
            for field in ("zone", "submarket", "bizFormed", "bizForming"):
                if computed[field] and not row.get(field):
                    missing.append((row.get("canonical_project_id"), row.get("canonical_name"), field))
        self.assertEqual(missing, [])

    def test_known_host_building_geo_is_derived(self):
        row = next(row for row in self.rows if row.get("canonical_project_id") == "cwhost-0015")
        computed = compute_geo(row["latitude"], row["longitude"])
        self.assertEqual(row["zone"], computed["zone"])
        self.assertEqual(row["submarket"], computed["submarket"])

    def test_source_backed_white_square_point_generates_geography(self):
        row = next(
            row for row in self.rows
            if row.get("canonical_project_id") == "cwhost-hist-5d45ac8941"
        )
        self.assertNotIn((row["latitude"], row["longitude"]), KNOWN_PLACEHOLDER_COORDS)
        computed = compute_geo(row["latitude"], row["longitude"])
        for field in ("zone", "submarket", "bizFormed", "bizForming"):
            self.assertEqual(row.get(field) or "", computed[field] or "")


if __name__ == "__main__":
    unittest.main()
