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


class RemainConflictResolutionTests(unittest.TestCase):
    """2026-08-18: Botanica Plaza / Rail.A conflicts closed by re-verifying
    against developer official sites and correcting the local geocode.
    А101 Прокшино stays a documented scope-difference, GBA/GLA must not move."""

    def setUp(self):
        if not LAYER_PATH.exists():
            self.skipTest("all_projects_layer.json not present")
        self.layer = json.loads(LAYER_PATH.read_text(encoding="utf-8-sig"))
        self.by_id = {r["canonical_project_id"]: r for r in self.layer}

    def test_botanica_plaza_coordinates_match_official_address(self):
        r = self.by_id["proj-170"]
        self.assertAlmostEqual(r["latitude"], 55.839861, places=3)
        self.assertAlmostEqual(r["longitude"], 37.6365, places=3)
        self.assertIn("Вильгельма Пика", r["address"])
        self.assertIn("remain_conflict_resolved", r["qa_notes"])

    def test_rail_a_coordinates_tightened_to_official_source(self):
        r = self.by_id["proj-173"]
        self.assertAlmostEqual(r["latitude"], 55.779406, places=3)
        self.assertAlmostEqual(r["longitude"], 37.687831, places=3)
        self.assertIn("remain_conflict_resolved", r["qa_notes"])

    def test_prokshino_gba_gla_untouched_by_scope_conflict(self):
        r = self.by_id["proj-216"]
        # единственный корпус из 5 в квартале — площадь всего комплекса (Remain
        # сумма 113029 / офиц. >177 тыс. кв.м) НЕ подставляется вместо площади
        # одного здания без разбивки по building.
        self.assertEqual(r["gba"], 42000)
        self.assertEqual(r["gla"], 22700)
        self.assertIn("resolved_scope_difference", r["qa_notes"])

    def test_layer_still_passes_validator_after_conflict_fixes(self):
        self.assertEqual(validate_layer(self.layer), [])


class RemainOnlyRemainWebVerificationTests(unittest.TestCase):
    """2026-08-18: web-проверка 4 only_remain кандидатов через офиц. сайты
    девелоперов (не NF-подтверждение самих лотов в квартальном срезе)."""

    def setUp(self):
        if not LAYER_PATH.exists():
            self.skipTest("all_projects_layer.json not present")
        self.layer = json.loads(LAYER_PATH.read_text(encoding="utf-8-sig"))
        self.by_id = {r["canonical_project_id"]: r for r in self.layer}

    def test_central_telegraph_rejected_after_building_sold_to_third_party(self):
        # Т-Банк выкупил здание целиком под корп. университет — лотов не будет.
        r = self.by_id["remain-only-0001"]
        self.assertEqual(r["verification_status"], "blocked")
        self.assertEqual(r["offer_status"], "Не применяется")
        self.assertFalse(r["quarter_offer_exists"])
        self.assertEqual(r["quarter_offer_refs"], [])
        self.assertEqual(r["public_visibility"], "internal_only")

    def test_confirmed_lot_candidates_stay_internal_only_pending_nf_process(self):
        # web-проверка подтверждает, что лоты реально существуют, но это не
        # заменяет NF-подтверждение — public_visibility/verification_status
        # не должны стать public/accepted только от web-сигнала.
        for pid in ("remain-only-0002", "remain-only-0003"):
            r = self.by_id[pid]
            self.assertEqual(r["public_visibility"], "internal_only")
            self.assertEqual(r["verification_status"], "under_review")
            self.assertFalse(r["quarter_offer_exists"])
            self.assertEqual(r["quarter_offer_refs"], [])
            self.assertEqual(r["market_channel"], [])

    def test_moscow_towers_reclassified_as_cross_registry_duplicate(self):
        """2026-08-19: remain-only-0004 (Moscow Towers) подтверждён как дубль
        data/future_projects.json OBJ-0021 (Гранд Сити, GLA 262800 совпадает
        точно) — не пробел покрытия. audit_remain_integration.py сверял
        только против all_projects_layer.json/classifier.html и не видел
        future_projects.json (отдельный xlsx-производный реестр) — отсюда
        ложный only_remain. Запись НЕ удалена, помечена duplicate_suspect."""
        r = self.by_id["remain-only-0004"]
        self.assertEqual(r["verification_status"], "blocked")
        self.assertEqual(r["qa_status"], "duplicate_suspect")
        self.assertIn("OBJ-0021", r["qa_notes"])
        self.assertFalse(r["quarter_offer_exists"])
        self.assertEqual(r["public_visibility"], "internal_only")

    def test_nagatinskaya_added_as_genuine_gap_not_duplicate(self):
        """2026-08-19: «Офисно-торговый центр Нагатинская» независимо
        подтверждён (stroi.mos.ru, часть ТПУ «Нагатинская») и не найден ни
        в all_projects_layer.json, ни в future_projects.json — реальный
        пробел, добавлен как remain-only-0005. Ввод заявлен на 2028-Q3—
        слишком рано для лотов в текущих кварталах, остаётся internal_only."""
        r = self.by_id["remain-only-0005"]
        self.assertEqual(r["canonical_name"], "Офисно-торговый центр Нагатинская")
        self.assertEqual(r["developer"], "Трэйд Инвестментс")
        self.assertTrue(r["external_only"])
        self.assertEqual(r["source"], "remain_datalens")
        self.assertEqual(r["public_visibility"], "internal_only")
        self.assertEqual(r["verification_status"], "under_review")
        self.assertFalse(r["quarter_offer_exists"])
        self.assertEqual(r["quarter_offer_refs"], [])
        self.assertEqual(r["market_channel"], [])


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
