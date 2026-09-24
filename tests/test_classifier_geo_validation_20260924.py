import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from recompute_geo import compute_geo


class ClassifierGeoValidationTests(unittest.TestCase):
    def test_krekshino_submarket_matches_current_polygons(self):
        payload = json.loads(
            (ROOT / "data" / "unified_classifier_audited_2026-08-27.json").read_text(encoding="utf-8")
        )
        row = next(r for r in payload["records"] if r.get("unified_id") == "UC-OBJ-ADD-354")
        computed = compute_geo(row["latitude"], row["longitude"])
        self.assertEqual(row.get("geo_submarket") or "", computed["submarket"] or "")


if __name__ == "__main__":
    unittest.main()
