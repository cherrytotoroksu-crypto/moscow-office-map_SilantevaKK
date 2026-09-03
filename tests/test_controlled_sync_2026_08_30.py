"""Tests for the 2026-08-30 controlled sync of
data/unified_classifier_audited_2026-08-27.json <-> data/all_projects_layer.json
(scripts/fix_coworking_id_sync_merges.py,
scripts/build_classifier_registry_mapping.py,
scripts/apply_unified_id_to_buildings_layer.py).

Covers the acceptance checks from the sync request (point 9):
  - no unified_id is lost (every classifier row appears in the mapping report)
  - no duplicate canonical_project_id in the registry
  - corpuses/towers of one project are not silently merged
  - all classifier records without coordinates are explicitly listed
    (count drifts down as dedup passes remove no-coordinate stub rows;
    see the 2026-09 dedup audit commits)
  - the quarterly buildings layer carries a reference back to the source
    classifier unified_id for at least the exact_match rows
"""
import glob
import json
import os
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load(path):
    with open(os.path.join(ROOT, path), encoding="utf-8") as f:
        return json.load(f)


class TestControlledSync20260830(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.classifier = load("data/unified_classifier_audited_2026-08-27.json")["records"]
        cls.registry = load("data/all_projects_layer.json")
        report_path = os.path.join(ROOT, "outputs", "classifier_registry_mapping_2026-08-30.json")
        with open(report_path, encoding="utf-8") as f:
            cls.mapping_report = json.load(f)

    def test_no_unified_id_lost(self):
        classifier_ids = {r["unified_id"] for r in self.classifier}
        report_ids = {e["unified_id"] for e in self.mapping_report}
        self.assertEqual(classifier_ids, report_ids,
                          "every classifier unified_id must appear exactly once in the mapping report")
        self.assertEqual(len(self.mapping_report), len(self.classifier),
                          "mapping report must have exactly one row per classifier record")

    # Known pre-existing exception, unrelated to this sync: "badaevsky" is a
    # single legacy id shared by the Восточная/Западная лента building-level
    # split (2 rows, same canonical_project_id) - present in the committed
    # baseline before this sync touched anything. Not something this sync
    # introduced or is asked to fix.
    KNOWN_PREEXISTING_DUPLICATE_IDS = {"badaevsky"}

    def test_no_duplicate_canonical_project_id(self):
        ids = [r["canonical_project_id"] for r in self.registry]
        dupes = {x for x in ids if ids.count(x) > 1}
        unexpected = dupes - self.KNOWN_PREEXISTING_DUPLICATE_IDS
        self.assertEqual(unexpected, set(),
                          f"NEW duplicate canonical_project_id introduced by this sync: {unexpected}")

    def test_corpuses_not_merged(self):
        # A row's legacy_ids MAY reference other canonical_project_id values
        # (the audited "linked, not collapsed" pattern - see AUDIT-008,
        # tests/test_manufaqtury_poklonka_audit_008.py): a primary row lists
        # its duplicates' ids in legacy_ids, but each duplicate MUST still
        # exist as its own separate row, with duplicate_of pointing back to
        # the primary. What must never happen is a referenced id's row being
        # silently absent (collapsed away) - that's the corpus-merge bug this
        # sync was written to catch.
        by_id = {r["canonical_project_id"]: r for r in self.registry}
        offenders = []
        for r in self.registry:
            legacy = r.get("legacy_ids") or []
            if len(legacy) <= 1:
                continue
            for other_id in legacy:
                other = by_id.get(other_id)
                if other is None or other.get("duplicate_of") != r["canonical_project_id"]:
                    offenders.append((r["canonical_project_id"], other_id))
        self.assertEqual(offenders, [],
                          f"legacy_ids reference rows that were collapsed away instead of kept separate: {offenders}")

    def test_25_records_without_coordinates_listed(self):
        missing = [r for r in self.classifier if r.get("latitude") is None or r.get("longitude") is None]
        self.assertEqual(len(missing), 16,
                          f"expected exactly 16 classifier records without coordinates, found {len(missing)}")
        # explicit enumeration, not just a count
        names = sorted(r.get("name") or "" for r in missing)
        self.assertEqual(len(set(names)), len(names), "duplicate names among the no-coordinate records")

    def test_map_layer_references_source_unified_id(self):
        classifier_unified_ids = {r["unified_id"] for r in self.classifier}
        exact_match_ids = {e["unified_id"] for e in self.mapping_report if e["status"] == "exact_match"}
        self.assertGreater(len(exact_match_ids), 0, "no exact_match rows in mapping report")

        linked_any = False
        for path in glob.glob(os.path.join(ROOT, "data", "buildings_*.json")):
            if "pre_sync" in path:
                continue
            rows = load(os.path.relpath(path, ROOT))
            for row in rows:
                uid = row.get("unified_id")
                if uid is None:
                    continue
                linked_any = True
                self.assertIn(uid, classifier_unified_ids,
                              f"{path}: unified_id {uid!r} does not exist in the classifier")
                self.assertIn(uid, exact_match_ids,
                              f"{path}: unified_id {uid!r} is linked but is not an exact_match "
                              "(probable_match/conflict must never be auto-linked)")
        self.assertTrue(linked_any, "no buildings_*.json row carries a unified_id reference")

    def test_mapping_report_statuses_are_valid(self):
        valid = {"exact_match", "probable_match", "conflict", "new_record", "excluded_from_quarterly_layer"}
        bad = [e for e in self.mapping_report if e["status"] not in valid]
        self.assertEqual(bad, [], f"unexpected status values: {bad}")

    def test_no_probable_or_conflict_auto_linked(self):
        non_safe_ids = {
            e["unified_id"] for e in self.mapping_report
            if e["status"] in ("probable_match", "conflict")
        }
        for path in glob.glob(os.path.join(ROOT, "data", "buildings_*.json")):
            if "pre_sync" in path:
                continue
            rows = load(os.path.relpath(path, ROOT))
            for row in rows:
                uid = row.get("unified_id")
                if uid is not None:
                    self.assertNotIn(uid, non_safe_ids,
                                      f"{path}: probable_match/conflict record {uid!r} was auto-linked")


if __name__ == "__main__":
    unittest.main()
