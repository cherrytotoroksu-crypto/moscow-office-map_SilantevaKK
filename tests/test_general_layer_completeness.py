"""Completeness checks for the current classifier/registry architecture.

- classifier.html now reads the audited unified classifier JSON and no longer
  embeds the legacy RAW_DATA array;
- every unified classifier row must be represented exactly once in the mapping
  report, and every exact match must point to an existing registry row;
- public/internal visibility rules remain registry invariants.

Не проверяет полноту относительно Remain (заблокировано отсутствием
табличного дампа — см. outputs/remain_integration_audit_2026-08-18.md).
"""
import json
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))
from build_all_projects_layer import load_classifier

REGISTRY_PATH = REPO_ROOT / "data" / "all_projects_layer.json"
CLASSIFIER_PATH = REPO_ROOT / "data" / "unified_classifier_audited_2026-08-27.json"
MAPPING_PATH = REPO_ROOT / "outputs" / "classifier_registry_mapping_2026-08-30.json"
CLASSIFIER_HTML_PATH = REPO_ROOT / "classifier.html"


class LegacyClassifierLoaderContractTests(unittest.TestCase):
    @unittest.skipUnless(CLASSIFIER_HTML_PATH.exists(), "classifier page not present")
    def test_legacy_builder_rejects_the_current_non_embedded_classifier(self):
        with self.assertRaisesRegex(RuntimeError, "circular build"):
            load_classifier()


@unittest.skipUnless(
    REGISTRY_PATH.exists() and CLASSIFIER_PATH.exists() and MAPPING_PATH.exists(),
    "generated files not present",
)
class GeneralLayerCompletenessTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.records = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
        cls.classifier = json.loads(CLASSIFIER_PATH.read_text(encoding="utf-8"))["records"]
        cls.mapping = json.loads(MAPPING_PATH.read_text(encoding="utf-8"))

    def test_every_classifier_row_reaches_the_mapping_report_exactly_once(self):
        classifier_ids = [row["unified_id"] for row in self.classifier]
        mapping_ids = [row["unified_id"] for row in self.mapping]
        self.assertEqual(len(classifier_ids), len(set(classifier_ids)), "duplicate classifier unified_id")
        self.assertEqual(len(mapping_ids), len(set(mapping_ids)), "duplicate mapping unified_id")
        self.assertEqual(set(classifier_ids), set(mapping_ids))

    def test_exact_classifier_matches_reference_existing_registry_rows(self):
        registry_ids = {row["canonical_project_id"] for row in self.records}
        exact_matches = [row for row in self.mapping if row["status"] == "exact_match"]
        self.assertTrue(exact_matches, "mapping report has no exact matches")
        missing = [
            (row["unified_id"], row.get("matched_project_id"))
            for row in exact_matches
            if row.get("matched_project_id") not in registry_ids
        ]
        self.assertEqual(missing, [], f"exact matches missing from registry: {missing}")

    def test_non_exact_matches_are_not_presented_as_exact(self):
        for row in self.mapping:
            if row["status"] != "exact_match":
                self.assertIsNone(row.get("matched_project_id"), row["unified_id"])

    def test_public_visibility_requires_confirmation(self):
        # п.7: internal_only разрешён ТОЛЬКО для неподтверждённых записей.
        # Обратное правило: public допустим только когда verification_status
        # не 'unverified'/'blocked'/'quarantine' — то есть запись прошла хоть
        # какую-то проверку (accepted/under_review — двигается к подтверждению;
        # blocked/quarantine/unverified обязаны быть internal_only).
        no_confirmation_yet = {"unverified", "blocked", "quarantine"}
        violations = [
            r["canonical_project_id"] for r in self.records
            if r["public_visibility"] == "public" and r["verification_status"] in no_confirmation_yet
        ]
        self.assertEqual(violations, [], f"public records without any confirmation: {violations}")

    def test_external_only_records_default_to_internal_until_accepted(self):
        # Более узкое правило специально для внешних источников (remain_datalens
        # и любые будущие external_only источники): internal_only, пока
        # verification_status не станет 'accepted' — 'under_review' одной
        # веб-проверки недостаточно для публичного показа.
        for r in self.records:
            if r.get("external_only") and r["verification_status"] != "accepted":
                self.assertEqual(
                    r["public_visibility"], "internal_only",
                    f"{r['canonical_project_id']}: external_only record with verification_status="
                    f"{r['verification_status']!r} must stay internal_only",
                )


if __name__ == "__main__":
    unittest.main()
