import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class UnifiedCodifierBuildingColumnsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = (ROOT / "codifier.html").read_text(encoding="utf-8")

    def test_general_codifier_exposes_building_identity_and_all_dates(self):
        for key in (
            "canonical_building_id",
            "construction_start_year",
            "sales_start_year",
            "input_year",
            "observed_market_channels",
        ):
            self.assertIn(f"key:'{key}'", self.html)

    def test_quarter_joins_carry_the_same_building_id(self):
        self.assertIn("row.canonical_building_id = match ? match.canonical_building_id : null", self.html)
        self.assertIn("row.reg_observed_market_channels = match ? match.observed_market_channels : null", self.html)


if __name__ == "__main__":
    unittest.main()
