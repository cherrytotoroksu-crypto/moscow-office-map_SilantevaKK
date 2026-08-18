"""Section 8/9/10 of the Remain-integration follow-up (2026-08-18):

- п.7: internal_only разрешён ТОЛЬКО для неподтверждённых записей —
  явный инвариант, не соглашение.
- п.8: тесты на полноту общего слоя и классификатора — каждая строка
  RAW_DATA из classifier.html должна дойти до all_projects_layer.json
  (никто не потерян при сборке), и наоборот — ни одна external_only
  запись не просочилась обратно в classifier.html.

Не проверяет полноту относительно Remain (заблокировано отсутствием
табличного дампа — см. outputs/remain_integration_audit_2026-08-18.md).
"""
import json
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))
from build_all_projects_layer import load_classifier, BADAEVSKY_IDS

REGISTRY_PATH = REPO_ROOT / "data" / "all_projects_layer.json"
CLASSIFIER_PATH = REPO_ROOT / "classifier.html"


@unittest.skipUnless(REGISTRY_PATH.exists() and CLASSIFIER_PATH.exists(), "generated files not present")
class GeneralLayerCompletenessTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.records = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
        cls.raw_data, _colormap = load_classifier()

    def test_every_classifier_row_reaches_the_general_layer(self):
        # Легаси-строки не удаляются (см. build_all_projects_layer.py) — каждый
        # old_id из RAW_DATA должен встречаться хотя бы один раз среди
        # classifier-производных записей: либо как canonical_project_id/
        # legacy_ids (после слияния технических дублей), либо — для Бадаевского —
        # через canonical_building_id (там canonical_project_id общий "badaevsky",
        # не proj-{old_id}, см. BADAEVSKY_IDS).
        classifier_records = [r for r in self.records if r["source"] == "classifier.html"]
        known_ids = set()
        known_building_ids = set()
        for r in classifier_records:
            known_ids.add(r["canonical_project_id"])
            known_ids.update(r.get("legacy_ids", []))
            if r.get("canonical_building_id"):
                known_building_ids.add(r["canonical_building_id"])

        missing = []
        for row in self.raw_data:
            old_id = row.get("old_id")
            if old_id is None or row.get("out_of_scope"):
                continue
            name_orig = row.get("name_orig") or row.get("name")
            if name_orig in BADAEVSKY_IDS:
                _pid, bld_id, _grain = BADAEVSKY_IDS[name_orig]
                if bld_id not in known_building_ids:
                    missing.append(f"proj-{old_id} (badaevsky/{bld_id})")
                continue
            pid = f"proj-{old_id}"
            if pid not in known_ids:
                missing.append(pid)
        self.assertEqual(missing, [], f"RAW_DATA rows missing from the general layer: {missing}")

    def test_classifier_row_count_matches_layer_exactly(self):
        classifier_records = [r for r in self.records if r["source"] == "classifier.html"]
        rows_in_scope = [
            row for row in self.raw_data
            if row.get("old_id") is not None and not row.get("out_of_scope")
        ]
        self.assertEqual(len(classifier_records), len(rows_in_scope))

    def test_no_external_record_leaked_into_classifier_html(self):
        # classifier.html — источник истины ТОЛЬКО для локальных данных;
        # remain-only-* id не должны попасть в RAW_DATA ни при каком слиянии.
        raw_ids = {f"proj-{row.get('old_id')}" for row in self.raw_data if row.get("old_id") is not None}
        external_ids = {r["canonical_project_id"] for r in self.records if r.get("external_only")}
        self.assertEqual(raw_ids & external_ids, set())

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
