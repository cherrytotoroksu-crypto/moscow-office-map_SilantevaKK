"""Regression pins for outputs/classifier_11_records_review_2026-08-19.md.

Separate QA track, not Remain. Data was NOT changed by this review — these
tests snapshot the current state of the 11 records plus the specific facts
found during web verification, so a silent edit (e.g. someone "fixing" the
Пожарная охрана developer without going through the review) shows up as a
test failure instead of disappearing quietly. Does not touch PRJ
architecture and does not touch data/building_dates.json.
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
        # "Orbital" (без -2) на 3-я Магистральная 10 уже сдан в 2023/2024 —
        # наша запись "Orbital-2" на вл.12 в статусе "Строится" им противоречит.
        # Пин на нынешнее состояние — ручной разбор (PRJ-вопрос) вне этого QA.
        r = self.by_id["proj-168"]
        self.assertEqual(r["address"], "Москва, 3-я Магистральная ул., вл. 12")
        self.assertEqual(r["project_status"], "Строится")

    def test_stone_khodynka_4_class_mismatch_still_unresolved(self):
        # stone.ru/commercial/hodinka4: класс Прайм — наша запись хранит A.
        # Пин на текущее (неверное) значение, чтобы правка была осознанной.
        r = self.by_id["proj-258"]
        self.assertEqual(r["cls"], "A")

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
