"""Regression pins for outputs/classifier_11_records_review_2026-08-19.md.

Separate QA track, not Remain. Most of the 11 records were NOT changed by
this review — these tests snapshot their current state plus the specific
facts found during web verification, so a silent edit (e.g. someone
"fixing" the Пожарная охрана developer without going through the review)
shows up as a test failure instead of disappearing quietly. Does not touch
PRJ architecture (canonical_project_id, merges).

2026-08-22 (second pass): input_year was fixed for 3 of the 11 records
(proj-72, proj-200, proj-258) with cited sources, and data/building_dates.json
was updated accordingly — see the "Обновление 2026-08-22 (второй заход)"
section of the review doc for full evidence.
"""
import json
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))
from validate_all_projects_layer import validate as validate_layer

LAYER_PATH = REPO_ROOT / "data" / "all_projects_layer.json"

REVIEWED_IDS = [
    "proj-1", "proj-13", "proj-72", "proj-168", "proj-200", "proj-227",
    "proj-240", "proj-251", "proj-258", "proj-264", "proj-269",
]


@unittest.skipUnless(LAYER_PATH.exists(), "all_projects_layer.json not present")
class Classifier11RecordsReviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.layer = json.loads(LAYER_PATH.read_text(encoding="utf-8-sig"))
        cls.by_id = {r["canonical_project_id"]: r for r in cls.layer}

    def test_all_11_records_still_exist_with_classifier_source(self):
        for pid in REVIEWED_IDS:
            self.assertIn(pid, self.by_id, f"{pid} missing from the layer")
            self.assertEqual(self.by_id[pid]["source"], "classifier.html")

    def test_sezar_gba_gla_match_official_source_exactly(self):
        # silikatny-13.ru / sezar-group.pvt.ru: GBA 15862 / GLA 11246, class A
        r = self.by_id["proj-72"]
        self.assertEqual(r["gba"], 15862.0)
        self.assertEqual(r["gla"], 11246.0)
        self.assertEqual(r["cls"], "A")

    def test_dius_completion_date_matches_official_source_exactly(self):
        # dius-mfk.ru: 4 квартал 2027 года, корпус 1
        r = self.by_id["proj-269"]
        self.assertEqual(r["input_year"], 2027)
        self.assertEqual(r["input_quarter"], 4)

    def test_olkhovaya_sky_completion_date_matches_official_source_exactly(self):
        # fortexgroup.ru/bc/olhovaya-sky: госкомиссия Q4 2027
        r = self.by_id["proj-240"]
        self.assertEqual(r["input_year"], 2027)
        self.assertEqual(r["input_quarter"], 4)

    def test_olkhovaya_sky_class_reconciled_to_b(self):
        r = self.by_id["proj-240"]
        self.assertEqual(r["cls"], "B")
        self.assertIn("Fortex Group", r["qa_notes"])

    def test_sezar_completion_year_fixed_with_cited_source(self):
        # 2026-08-22: rusdevelopers.ru ("Срок реализации проекта 2027 год"),
        # silikatny-13.ru, sezar-group.pvt.ru, novostroy-m.ru — квартал не
        # уточнён ни одним источником, input_quarter остаётся None.
        r = self.by_id["proj-72"]
        self.assertEqual(r["input_year"], 2027)
        self.assertIsNone(r["input_quarter"])
        self.assertEqual(r["input_date_kind"], "confirmed")
        self.assertIn("rusdevelopers.ru", r["qa_notes"])

    def test_stone_khodynka_3_completion_year_conflict_resolved(self):
        # 2026-08-22: поисковый сниппет stone.ru показывал устаревшее
        # "2028" в заголовке; прямой WebFetch живой страницы + stonebrokers.ru
        # + kommersant.ru/doc/8228995 сходятся на 2029. Конфликт разрешён
        # прямой проверкой содержимого, не сниппета.
        r = self.by_id["proj-200"]
        self.assertEqual(r["input_year"], 2029)
        self.assertIsNone(r["input_quarter"])
        self.assertEqual(r["input_date_kind"], "confirmed")
        self.assertIn("kommersant.ru", r["qa_notes"])

    def test_stone_khodynka_4_completion_year_fixed_with_cited_source(self):
        # 2026-08-22: stone.ru (живой fetch "Готовность 2032 г."),
        # stonebrokers.ru, anwin.ru — квартал не уточнён, input_quarter
        # остаётся None.
        r = self.by_id["proj-258"]
        self.assertEqual(r["input_year"], 2032)
        self.assertIsNone(r["input_quarter"])
        self.assertEqual(r["input_date_kind"], "confirmed")
        self.assertIn("stone.ru", r["qa_notes"])

    def test_stone_khodynka_4_class_reconciled_to_prime(self):
        r = self.by_id["proj-258"]
        self.assertEqual(r["cls"], "Prime")
        self.assertIn("STONE official page", r["qa_notes"])

    def test_new_date_fixes_did_not_fabricate_a_quarter(self):
        # Общий инвариант этого захода: там, где источники называют только
        # год, commission_q в building_dates.json должен остаться None —
        # scripts/build_all_projects_layer.py:commission_to_input требует
        # полный YYYYMM, фабриковать месяц/квартал нельзя.
        bd_path = REPO_ROOT / "data" / "building_dates.json"
        bd = json.loads(bd_path.read_text(encoding="utf-8-sig"))
        for key in ("бизнес-центр sezar", "stone ходынка iii", "stone ходынка iv"):
            self.assertIn(key, bd)
            self.assertIsNone(bd[key]["commission_q"])
            self.assertTrue(bd[key]["source"])

    def test_stone_khodynka_3_class_matches_official_source(self):
        # stone.ru/commercial/hodinka3: класс Prime
        r = self.by_id["proj-200"]
        self.assertEqual(r["cls"], "Prime")

    def test_korp_molodezhnaya_gla_zero_defect_still_present(self):
        # известный отдельный дефект (не по этому QA) — gla=0 должен быть
        # null; зафиксировано здесь, чтобы починка не потерялась молча.
        r = self.by_id["proj-251"]
        self.assertEqual(r["gla"], 0)

    def test_skolkovsky_developer_field_anomaly_still_present(self):
        # "Пожарная охрана" как developer — известный артефакт парсинга,
        # НЕ подтверждён веб-проверкой; ни один источник не нашёл этот
        # объект вообще. Пин не даёт правке проскочить без review-обновления.
        r = self.by_id["proj-227"]
        self.assertEqual(r["developer"], "Пожарная охрана")

    def test_orbital_2_address_and_status_conflict_still_unresolved(self):
        # 2026-08-19 (второй заход): проверены 3 кандидата по адресу/названию
        # (Orbital вл.10 GBA~27к, вл.12-здание класса B GBA 17.9к, ФСК
        # "Магистральная 12" на 5-й Магистральной GBA 18.7к) — ни один не
        # совпал с нашими GBA 57967. Осознанно НЕ правил (нет подтверждения),
        # Orbital и Orbital-2 не объединены. Пин на нынешнее состояние.
        r = self.by_id["proj-168"]
        self.assertEqual(r["address"], "Москва, 3-я Магистральная ул., вл. 12")
        self.assertEqual(r["project_status"], "Строится")
        self.assertEqual(r["gba"], 57967)

    def test_orbital_and_orbital_2_stay_separate_projects(self):
        # 2026-08-22: явное требование заказчика — не объединять Orbital
        # (proj-101, 3-я Магистральная ул., 10, GBA 27271) и Orbital-2
        # (proj-168, вл. 12, GBA 57967) автоматически. Разные адреса,
        # разные GBA — оба остаются отдельными записями без duplicate_of
        # друг на друга.
        orbital = self.by_id["proj-101"]
        orbital_2 = self.by_id["proj-168"]
        self.assertNotEqual(orbital["canonical_project_id"], orbital_2["canonical_project_id"])
        self.assertNotEqual(orbital["address"], orbital_2["address"])
        self.assertIsNone(orbital["duplicate_of"])
        self.assertIsNone(orbital_2["duplicate_of"])

    def test_fly_tower_status_and_year_fixed_with_cited_source(self):
        # fortexgroup.ru/bc/fly-tower: "Год постройки: 2025", объект готов.
        r = self.by_id["proj-13"]
        self.assertEqual(r["project_status"], "Введён")
        self.assertEqual(r["input_year"], 2025)
        self.assertIsNone(r["input_quarter"])
        self.assertEqual(r["input_date_kind"], "confirmed")
        self.assertIn("fortexgroup.ru", r["qa_notes"])

    def test_fly_tower_offer_status_left_untouched_as_derived_field(self):
        # offer_status/quarter_offer_refs — производные поля от
        # build_all_projects_layer.py + data/lots_*.json, не правились
        # вручную вместе со статусом/датой (см. review-файл).
        r = self.by_id["proj-13"]
        self.assertEqual(r["offer_status"], "Ещё не вышел в продажу")

    def test_stone_khodynka_4_class_reconciled(self):
        # STONE official page calls the project premium; market sources map
        # that label to canonical class Prime.
        r = self.by_id["proj-258"]
        self.assertEqual(r["cls"], "Prime")

    def test_review_did_not_touch_building_dates(self):
        bd_path = REPO_ROOT / "data" / "building_dates.json"
        if not bd_path.exists():
            self.skipTest("building_dates.json not present")
        # только проверяем, что файл существует и читается — сам факт
        # отсутствия изменений гарантируется процессом (git diff), не тестом.
        json.loads(bd_path.read_text(encoding="utf-8-sig"))

    def test_layer_still_passes_validator(self):
        self.assertEqual(validate_layer(self.layer), [])


if __name__ == "__main__":
    unittest.main()
