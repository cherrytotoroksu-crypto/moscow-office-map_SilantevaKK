import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load_build_module():
    path = ROOT / "scripts" / "build_public_site.py"
    spec = importlib.util.spec_from_file_location("build_public_site", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class BuildPublicSiteBuildingDatesTests(unittest.TestCase):
    def test_public_build_keeps_commission_year_and_strips_qa_fields(self):
        module = load_build_module()
        with tempfile.TemporaryDirectory() as tmp:
            module.OUT_DIR = tmp
            module.build_data_dir()
            public = json.loads(
                (Path(tmp) / "data" / "building_dates.json").read_text(encoding="utf-8")
            )

        one_tower = public["one tower"]
        self.assertEqual(one_tower["commission_year"], 2030)
        self.assertNotIn("source", one_tower)
        self.assertNotIn("last_checked", one_tower)


if __name__ == "__main__":
    unittest.main()
