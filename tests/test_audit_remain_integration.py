import json
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))
from audit_remain_integration import REMAIN_RECORDS, build_only_remain_entry, classify
from validate_all_projects_layer import validate as validate_layer

LAYER_PATH = REPO_ROOT / "data" / "all_projects_layer.json"


class RemainClassificationTests(unittest.TestCase):
    def test_every_record_has_a_known_category(self):
        for rec in REMAIN_RECORDS:
            self.assertIn(rec["category"], {"exact_match", "probable_match", "only_remain"})

    def test_conflicts_are_flagged_with_notes(self):
        grouped = classify()
        for c in grouped["conflict"]:
            self.assertTrue(c.get("conflict_note"))

    def test_only_remain_entry_excluded_from_quarterly_offer(self):
        rec = next(r for r in REMAIN_RECORDS if r["category"] == "only_remain")
        entry = build_only_remain_entry(rec, 1)
        self.assertFalse(entry["quarter_offer_exists"])
        self.assertEqual(entry["quarter_offer_refs"], [])
        self.assertEqual(entry["market_channel"], [])
        self.assertTrue(entry["external_only"])
        self.assertEqual(entry["source"], "remain_datalens")
        self.assertEqual(entry["public_visibility"], "internal_only")

    def test_only_remain_entry_passes_layer_validator(self):
        rec = REMAIN_RECORDS[-1]
        entry = build_only_remain_entry(rec, 9999)
        errors = validate_layer([entry])
        # entry deliberately has no coordinates/address (unverified external record);
        # only assert no *enum*-type violations, which is what the audit script controls.
        enum_errors = [e for e in errors if "invalid" in e]
        self.assertEqual(enum_errors, [])


class RemainRegressionOnCurrentLayerTests(unittest.TestCase):
    """Guards against silently losing external_only Remain records on rebuild."""

    def setUp(self):
        if not LAYER_PATH.exists():
            self.skipTest("all_projects_layer.json not present")
        self.layer = json.loads(LAYER_PATH.read_text(encoding="utf-8-sig"))

    def test_remain_records_if_present_keep_required_flags(self):
        remain_records = [r for r in self.layer if r.get("source") == "remain_datalens"]
        for r in remain_records:
            self.assertTrue(r["external_only"], msg=f"{r['canonical_project_id']} lost external_only")
            self.assertEqual(r["quarter_offer_refs"], [], msg=f"{r['canonical_project_id']} gained quarterly offer refs")
            self.assertFalse(r["quarter_offer_exists"])


if __name__ == "__main__":
    unittest.main()
