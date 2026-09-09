"""Regression for LEGACY_CLASS_OVERRIDES (2026-09-09).

264 of the 510 legacy_supplement map points (data/future_projects.json
records shown on the "Все проекты" map) had no class (cls) field. Ten
parallel web-verification agents checked all 264; only 33 came back with a
confident, address-matched class within the accepted A/B+/B/Prime scale —
the rest were either genuinely unpublished (projects still at the planning
stage, developer hasn't announced a class yet), the found building didn't
match the exact address, or the class fell outside the accepted scale
(e.g. "B-", "C", "deluxe") and was deliberately left out.
"""
import os
import re
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INDEX_HTML = os.path.join(ROOT, "index.html")


class LegacyClassOverridesTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open(INDEX_HTML, encoding="utf-8") as f:
            cls.html = f.read()

    def _overrides_block(self):
        match = re.search(
            r"LEGACY_CLASS_OVERRIDES\s*=\s*\{(.*?)\n\s*\};", self.html, re.S
        )
        self.assertIsNotNone(match, "LEGACY_CLASS_OVERRIDES not found in index.html")
        return match.group(1)

    def test_confidently_verified_ids_are_present(self):
        expected_ids = [
            "OBJ-0159", "OBJ-0161", "OBJ-0180", "OBJ-0199", "OBJ-0248",
            "OBJ-0254", "OBJ-0260", "OBJ-0285", "OBJ-0295", "OBJ-0299",
            "OBJ-0305", "OBJ-0313", "OBJ-0320", "OBJ-0321", "OBJ-0325",
            "OBJ-0328", "OBJ-0354", "OBJ-0381", "OBJ-0385", "OBJ-0388",
            "OBJ-0394", "OBJ-0397", "OBJ-0399", "OBJ-0408", "OBJ-0415",
            "OBJ-0433", "OBJ-0505", "OBJ-0510", "OBJ-0519", "OBJ-0538",
            "OBJ-0546", "OBJ-0558", "OBJ-0693",
        ]
        block = self._overrides_block()
        for oid in expected_ids:
            self.assertIn(f"'{oid}'", block, f"{oid} missing from LEGACY_CLASS_OVERRIDES")
        all_ids = re.findall(r"'(OBJ-\d{4})'\s*:", block)
        self.assertEqual(len(all_ids), len(set(all_ids)), "duplicate id in LEGACY_CLASS_OVERRIDES")
        self.assertEqual(
            len(all_ids), len(expected_ids),
            "unexpected extra id in LEGACY_CLASS_OVERRIDES — low-confidence or off-scale class added?",
        )

    def test_all_values_are_within_accepted_class_scale(self):
        block = self._overrides_block()
        values = re.findall(r"'OBJ-\d{4}'\s*:\s*'([^']+)'", block)
        self.assertTrue(values, "no values parsed from LEGACY_CLASS_OVERRIDES")
        for v in values:
            self.assertIn(v, {"A", "B+", "B", "Prime"}, f"off-scale class value: {v!r}")

    def test_override_is_only_applied_when_class_field_is_empty(self):
        match = re.search(
            r"if \(!mapped\.cls && LEGACY_CLASS_OVERRIDES\[p\.id\]\)\s*\{(.*?)\n\s*\}",
            self.html, re.S,
        )
        self.assertIsNotNone(match, "class override guard not found — must not clobber existing data")
        body = match.group(1)
        self.assertIn("mapped.cls = LEGACY_CLASS_OVERRIDES[p.id]", body)


if __name__ == "__main__":
    unittest.main()
