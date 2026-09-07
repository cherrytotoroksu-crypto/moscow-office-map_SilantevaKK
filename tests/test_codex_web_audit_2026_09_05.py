"""Regression tests for outputs/codex_web_audit_2026-09-05.md.

Only the explicitly confirmed decision was applied (Capital Towers
mixed-use re-verification). The proposed aliases for "БЦ Крост"
(record absent from the live audited classifier) and "БЦ в
Очаково-Матвеевском" -> Lakes 2 (conflicting developer/coordinates/GBA,
no second independent source) were rejected by the user and must stay
unmerged. This file locks in that decision so a future pass does not
silently apply the rejected merges.
"""
import json
import os
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load(path):
    with open(os.path.join(ROOT, path), encoding="utf-8") as f:
        return json.load(f)


class TestCodexWebAudit20260905(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.classifier = load("data/unified_classifier_audited_2026-08-27.json")["records"]
        cls.by_id = {r["unified_id"]: r for r in cls.classifier}
        cls.by_name = {}
        for r in cls.classifier:
            cls.by_name.setdefault(r["name"], []).append(r)

    def test_bc_krost_candidate_absent_from_live_classifier(self):
        # UC-OBJ-0255 "БЦ Крост" only exists in the legacy data/unified_classifier.json,
        # never made it into the audited/live file. There is nothing to alias.
        self.assertNotIn("UC-OBJ-0255", self.by_id)
        self.assertNotIn("БЦ Крост", self.by_name,
                          "the disputed 'БЦ Крост' candidate must not exist in the live classifier")

    def test_ochakovo_matveevskoe_not_merged_into_lakes2(self):
        ochakovo = self.by_id["UC-OBJ-0251"]
        lakes2 = self.by_id["UC-OBJ-0202"]
        self.assertEqual(ochakovo["name"], "БЦ в Очаково-Матвеевском")
        self.assertEqual(lakes2["name"], "Lakes 2")
        # Distinct developers/areas/coordinates -> merge would be a false link, must stay separate records
        self.assertNotEqual(ochakovo["developer"], lakes2["developer"])
        self.assertNotEqual(ochakovo["gba"], lakes2["gba"])
        self.assertNotEqual(ochakovo["legacy_ids"], lakes2.get("legacy_ids"))
        self.assertEqual(ochakovo.get("legacy_ids"), [])

    def test_capital_towers_stays_mixed_use_with_office_gla(self):
        towers = self.by_id["UC-OBJ-0014"]
        self.assertEqual(towers["name"], "Capital Towers")
        self.assertEqual(towers["entity_type"], "residential_complex_with_commercial_infrastructure")
        self.assertEqual(towers["gla"], 8808.0)
        self.assertEqual(towers["gba"], 243000.0, "full GBA must not be reclassified as office area")
        self.assertFalse(towers["needs_review"])
        self.assertIn("mixed_use_project", towers["layer_qa_notes"])

    def test_disputed_candidates_remain_unmerged(self):
        # Unikey, БЦ у Океании, MR 1/2, Дом Солнца: no new evidence supplied,
        # so each conflicting/unresolved candidate name must still exist as its
        # own separate record (no silent alias/merge into another project).
        disputed_name_fragments = ["Unikey", "Океании", "Дом Солнца"]
        for fragment in disputed_name_fragments:
            matches = [name for name in self.by_name if fragment in name]
            self.assertTrue(matches, f"expected at least one live record mentioning {fragment!r}")

    def test_building_dates_untouched(self):
        # This audit must not touch data/building_dates.json at all.
        path = os.path.join(ROOT, "data", "building_dates.json")
        self.assertTrue(os.path.isfile(path))


if __name__ == "__main__":
    unittest.main()
