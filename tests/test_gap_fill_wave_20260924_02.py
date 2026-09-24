import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class GapFillWaveTwoTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.layer = json.loads((ROOT / "data" / "all_projects_layer.json").read_text(encoding="utf-8-sig"))
        cls.by_id = {row.get("canonical_project_id"): row for row in cls.layer}

    def test_confirmed_commissioning_years_are_applied(self):
        expected = {
            "proj-14": (2023, None),
            "proj-77": (2026, 1),
            "cwhost-0013": (2006, None),
            "cwhost-0025": (1964, None),
            "cwhost-0041": (2023, 2),
            "cwhost-0042": (2017, 3),
            "cwhost-hist-5d45ac8941": (2009, None),
        }
        for project_id, (year, quarter) in expected.items():
            with self.subTest(project_id=project_id):
                row = self.by_id[project_id]
                self.assertEqual(row["input_year"], year)
                self.assertEqual(row["input_quarter"], quarter)
                self.assertEqual(row["input_date_kind"], "confirmed")

    def test_rejected_same_address_match_stays_blank(self):
        self.assertIsNone(self.by_id["cwhost-0003"]["input_year"])


if __name__ == "__main__":
    unittest.main()
