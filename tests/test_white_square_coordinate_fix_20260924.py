import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class WhiteSquareCoordinateFixTests(unittest.TestCase):
    def test_placeholder_is_replaced_in_both_registries(self):
        layer = json.loads((ROOT / "data" / "all_projects_layer.json").read_text(encoding="utf-8"))
        row = next(r for r in layer if r.get("canonical_project_id") == "cwhost-hist-5d45ac8941")
        self.assertAlmostEqual(row["latitude"], 55.7778039613667)
        self.assertAlmostEqual(row["longitude"], 37.5866961479187)
        self.assertEqual(row["geometry_quality"], "house_exact")
        self.assertEqual(row["submarket"], "ТТК Север")

        unified = json.loads((ROOT / "data" / "unified_classifier_audited_2026-08-27.json").read_text(encoding="utf-8"))
        target = next(r for r in unified["records"] if r.get("unified_id") == "UC-OBJ-ADD-328")
        self.assertEqual(target["coordinates_status"], "verified")
        self.assertAlmostEqual(target["latitude"], row["latitude"])
        self.assertAlmostEqual(target["longitude"], row["longitude"])
        self.assertIn("realty-guide.ru", " ".join(target["source_links"]))


if __name__ == "__main__":
    unittest.main()
