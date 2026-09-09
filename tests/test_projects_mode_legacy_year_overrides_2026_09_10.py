"""Regression for LEGACY_YEAR_OVERRIDES (2026-09-10).

353 of the 510 legacy_supplement map points (data/future_projects.json
records shown on the "Все проекты" map) had no commission_year. Thirteen
parallel web-verification agents checked all 353; only 31 came back with a
confident, address-matched year (either a completed building's actual
commissioning year, or a developer-announced planned year for a
project/construction-stage record) — the rest were either genuinely
unannounced (early planning stage), had conflicting dates across sources,
or the found project didn't match the exact address.
"""
import os
import re
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INDEX_HTML = os.path.join(ROOT, "index.html")


class LegacyYearOverridesTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open(INDEX_HTML, encoding="utf-8") as f:
            cls.html = f.read()

    def _overrides_block(self):
        match = re.search(
            r"LEGACY_YEAR_OVERRIDES\s*=\s*\{(.*?)\n\s*\};", self.html, re.S
        )
        self.assertIsNotNone(match, "LEGACY_YEAR_OVERRIDES not found in index.html")
        return match.group(1)

    def test_confidently_verified_ids_are_present(self):
        expected_ids = [
            "OBJ-0102", "OBJ-0248", "OBJ-0260", "OBJ-0297", "OBJ-0397",
            "OBJ-0407", "OBJ-0433", "OBJ-0441", "OBJ-0443", "OBJ-0465",
            "OBJ-0480", "OBJ-0518", "OBJ-0521", "OBJ-0538", "OBJ-0541",
            "OBJ-0551", "OBJ-0559", "OBJ-0646", "OBJ-0654", "OBJ-0657",
            "OBJ-0663", "OBJ-0702", "OBJ-0705", "OBJ-0712", "OBJ-0713",
            "OBJ-0714", "OBJ-0723", "OBJ-0724", "OBJ-0748", "OBJ-0768",
            "OBJ-0773",
        ]
        block = self._overrides_block()
        for oid in expected_ids:
            self.assertIn(f"'{oid}'", block, f"{oid} missing from LEGACY_YEAR_OVERRIDES")
        all_ids = re.findall(r"'(OBJ-\d{4})'\s*:", block)
        self.assertEqual(len(all_ids), len(set(all_ids)), "duplicate id in LEGACY_YEAR_OVERRIDES")
        self.assertEqual(
            len(all_ids), len(expected_ids),
            "unexpected extra id in LEGACY_YEAR_OVERRIDES — low-confidence year added?",
        )

    def test_all_values_are_plausible_years(self):
        block = self._overrides_block()
        values = re.findall(r"'OBJ-\d{4}'\s*:\s*(\d{4})", block)
        self.assertTrue(values, "no values parsed from LEGACY_YEAR_OVERRIDES")
        for v in values:
            year = int(v)
            self.assertTrue(2000 <= year <= 2035, f"implausible year: {year}")

    def test_override_is_only_applied_when_year_field_is_empty(self):
        match = re.search(
            r"if \(!mapped\.commission_year && LEGACY_YEAR_OVERRIDES\[p\.id\]\)\s*\{(.*?)\n\s*\}",
            self.html, re.S,
        )
        self.assertIsNotNone(match, "year override guard not found — must not clobber existing data")
        body = match.group(1)
        self.assertIn("mapped.commission_year = LEGACY_YEAR_OVERRIDES[p.id]", body)


if __name__ == "__main__":
    unittest.main()
