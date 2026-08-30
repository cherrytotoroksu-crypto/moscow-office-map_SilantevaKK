"""Regression checks for comparison defaults and area metric wording."""

import re
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent


def function_body(source: str, name: str) -> str:
    match = re.search(rf"(?:async\s+)?function\s+{name}\s*\([^)]*\)\s*\{{", source)
    if not match:
        raise AssertionError(f"function {name} not found")
    depth = 0
    for index in range(match.end() - 1, len(source)):
        if source[index] == "{":
            depth += 1
        elif source[index] == "}":
            depth -= 1
            if depth == 0:
                return source[match.end() - 1:index + 1]
    raise AssertionError(f"function {name} has unbalanced braces")


class ComparisonDefaultsAndMetricSemanticsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.index = (REPO_ROOT / "index.html").read_text(encoding="utf-8")
        cls.analytics = (REPO_ROOT / "analytics.html").read_text(encoding="utf-8")
        cls.codifier = (REPO_ROOT / "codifier.html").read_text(encoding="utf-8")

    def test_map_comparison_modals_use_latest_data_bearing_pair(self):
        helper = function_body(self.index, "getDefaultComparisonQuarters")
        self.assertIn("withData", helper)
        self.assertIn("currentQuarter.id", helper)
        for name in ("openCompare", "openBldCompareModal"):
            body = function_body(self.index, name)
            self.assertIn("getDefaultComparisonQuarters(mode)", body)
            self.assertNotIn("qs[0].id", body)

    def test_analytics_defaults_to_last_two_quarters(self):
        body = function_body(self.analytics, "initAnalyticsConstructor")
        self.assertIn("qs[Math.max(0, qs.length - 2)].id", body)
        self.assertIn("qs[qs.length-1].id", body)
        self.assertNotIn("qOpts, qs[0].id", body)

    def test_sale_and_rent_area_labels_are_unambiguous(self):
        for source in (self.index, self.analytics):
            self.assertIn("Площадь лотов в продаже", source)
            self.assertIn("Площадь в аренду", source)
        self.assertIn("Контрольная площадь продажи (Golden File), м²", self.codifier)
        self.assertIn("Контрольная площадь аренды (Golden File), м²", self.codifier)
        self.assertNotIn("Площадь, м² (Golden File, контрольно)", self.codifier)

    def test_rent_map_selector_uses_rate_not_price_wording(self):
        self.assertIn("const METRIC_OPTIONS_RENT", self.index)
        self.assertIn("Ср. взвешенная ставка (руб/кв.м/год)", self.index)
        self.assertNotIn("METRIC_OPTIONS_SALERENT", self.index)


if __name__ == "__main__":
    unittest.main()
