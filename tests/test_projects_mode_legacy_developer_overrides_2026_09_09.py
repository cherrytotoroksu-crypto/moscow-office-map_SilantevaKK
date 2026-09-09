"""Regression for LEGACY_DEVELOPER_OVERRIDES (2026-09-09).

113 of the 510 legacy_supplement map points (data/future_projects.json
records shown on the "Все проекты" map) had no developer field. A wave of
parallel web-verification agents checked all 113; only 18 came back with a
confident, address-matched developer — the rest were either genuinely
unpublished (completed BCs with no active marketing) or the found project
didn't match the exact address ("умеренная уверенность" / "вероятно"),
and were deliberately left out to avoid showing unverified data on a public
map. This test locks the override map to exactly those 18 ids so a future
edit can't silently drop or expand it without updating this record.
"""
import os
import re
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INDEX_HTML = os.path.join(ROOT, "index.html")


class LegacyDeveloperOverridesTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open(INDEX_HTML, encoding="utf-8") as f:
            cls.html = f.read()

    def _overrides_block(self):
        match = re.search(
            r"LEGACY_DEVELOPER_OVERRIDES\s*=\s*\{(.*?)\n\s*\};", self.html, re.S
        )
        self.assertIsNotNone(match, "LEGACY_DEVELOPER_OVERRIDES not found in index.html")
        return match.group(1)

    def test_confidently_verified_ids_are_present(self):
        expected_ids = [
            "OBJ-0013", "OBJ-0289", "OBJ-0292", "OBJ-0309", "OBJ-0354",
            "OBJ-0439", "OBJ-0523", "OBJ-0525", "OBJ-0526", "OBJ-0528",
            "OBJ-0539", "OBJ-0550", "OBJ-0565", "OBJ-0613", "OBJ-0658",
            "OBJ-0664", "OBJ-0676", "OBJ-0720",
        ]
        block = self._overrides_block()
        for oid in expected_ids:
            self.assertIn(f"'{oid}'", block, f"{oid} missing from LEGACY_DEVELOPER_OVERRIDES")
        all_ids = re.findall(r"'(OBJ-\d{4})'\s*:", block)
        self.assertEqual(len(all_ids), len(set(all_ids)), "duplicate id in LEGACY_DEVELOPER_OVERRIDES")
        self.assertEqual(
            len(all_ids), len(expected_ids),
            "unexpected extra id in LEGACY_DEVELOPER_OVERRIDES — low-confidence match added?",
        )

    def test_override_is_only_applied_when_developer_field_is_empty(self):
        match = re.search(
            r"if \(!mapped\.developer && LEGACY_DEVELOPER_OVERRIDES\[p\.id\]\)\s*\{(.*?)\n\s*\}",
            self.html, re.S,
        )
        self.assertIsNotNone(match, "developer override guard not found — must not clobber existing data")
        body = match.group(1)
        self.assertIn("mapped.developer = LEGACY_DEVELOPER_OVERRIDES[p.id]", body)
        self.assertIn("enriched_from", body)


if __name__ == "__main__":
    unittest.main()
