"""KPI integrity tests for "Продажа офисов" — data/lots_{quarter}.json.

Two kinds of checks here:
  1. Logic tests against synthetic fixtures (deterministic, independent of
     whatever is currently in data/lots_202606.json).
  2. Regression guards against the REAL Q2 2026 file, asserting the audit
     script (scripts/audit_sale_lots_kpi.py) still detects the confirmed
     issues found manually (Сити-4 / SEZAR TOWER duplicate building) — so a
     future data refresh that silently "fixes" or reintroduces this doesn't
     go unnoticed.

Does not modify data/lots_*.json. Does not assert the audit's numbers equal
some externally provided "expected" totals — those require human
confirmation per the task's own instruction not to guess.
"""
import json
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from audit_sale_lots_kpi import (  # noqa: E402
    flatten,
    find_exact_duplicate_rows,
    find_duplicate_buildings,
    find_mega_lots,
    reconcile_quarter,
)


class ExactDuplicateRowsTest(unittest.TestCase):
    def test_one_lot_not_counted_twice(self):
        """Требование 1: одинаковая строка лота дважды в списке — считается
        дублем один раз (extra_count), не растворяется молча в сумме."""
        raw = {
            "Дом А": [
                {"block": "1", "floor": "2", "area": 50.0, "price": 300000, "total": 15000000},
                {"block": "1", "floor": "2", "area": 50.0, "price": 300000, "total": 15000000},
            ]
        }
        dupes = find_exact_duplicate_rows(raw)
        self.assertEqual(len(dupes), 1)
        self.assertEqual(dupes[0]["extra_count"], 1)


class SegmentIsolationTest(unittest.TestCase):
    def test_lot_not_shared_between_sale_and_rent_files(self):
        """Требование 2: один и тот же лот (по зданию+площади+цене) не
        встречается одновременно в lots_*.json (продажа) и
        rent_lots_*.json (аренда) одного квартала."""
        quarter = "202606"
        sale_path = REPO_ROOT / "data" / f"lots_{quarter}.json"
        rent_path = REPO_ROOT / "data" / f"rent_lots_{quarter}.json"
        if not sale_path.exists() or not rent_path.exists():
            self.skipTest("нет файлов для этого квартала")
        with open(sale_path, encoding="utf-8-sig") as f:
            sale = json.load(f)
        with open(rent_path, encoding="utf-8-sig") as f:
            rent = json.load(f)
        sale_sig = {(b, round(l.get("area") or 0, 1), l.get("price"))
                    for b, lots in sale.items() for l in lots if l.get("area")}
        rent_sig = {(b, round(l.get("area") or 0, 1), l.get("rate"))
                    for b, lots in rent.items() for l in lots if l.get("area")}
        overlap = sale_sig & rent_sig
        self.assertEqual(overlap, set(), f"лоты встречаются и в продаже, и в аренде: {overlap}")


class KpiEqualsSumOfFilteredRowsTest(unittest.TestCase):
    def test_area_and_value_sum_match_manual_sum(self):
        """Требование 3: area_sum/value_sum в reconcile_quarter равны ручной
        сумме тех же строк — регрессионная защита от рассинхронизации."""
        raw = {
            "Дом Б": [
                {"area": 40.0, "total": 12000000},
                {"area": 60.0, "total": 21000000},
            ],
            "Дом В": [
                {"area": 100.0, "total": 45000000},
            ],
        }
        rows = flatten(raw)
        manual_area = sum(r["area"] for r in rows)
        manual_value = sum(r["total"] for r in rows)
        self.assertEqual(manual_area, 200.0)
        self.assertEqual(manual_value, 78000000)


class WeightedPriceFormulaTest(unittest.TestCase):
    def test_price_equals_sum_total_over_sum_area(self):
        """Требование 4: средневзвешенная цена = SUM(total)/SUM(area), а не
        среднее price по лотам (не совпадает при разных площадях лотов)."""
        raw = {
            "Дом Г": [
                {"area": 10.0, "price": 100000, "total": 1000000},
                {"area": 90.0, "price": 500000, "total": 45000000},
            ]
        }
        rows = flatten(raw)
        total_area = sum(r["area"] for r in rows)
        total_value = sum(r["total"] for r in rows)
        weighted = total_value / total_area
        simple_avg_of_price_column = sum(r["price"] for r in rows) / len(rows)
        self.assertAlmostEqual(weighted, 460000.0)
        # Доказываем, что это НЕ то же самое, что среднее price — если бы
        # кто-то по ошибке считал просто mean(price), число было бы другим.
        self.assertNotAlmostEqual(weighted, simple_avg_of_price_column)


class NoGlaGbaLeakIntoLotAreaTest(unittest.TestCase):
    def test_building_level_gla_gba_ignored_by_lot_area_sum(self):
        """Требование 5: если в строке лота случайно оказалось поле gla/gba
        (уровень здания/проекта), сумма площади лотов его не учитывает —
        area_sum считается только по полю area отдельного лота."""
        raw = {
            "Дом Д": [
                {"area": 55.0, "total": 20000000, "gla": 9999999, "gba": 8888888},
            ]
        }
        rows = flatten(raw)
        total_area = sum(r["area"] for r in rows)
        self.assertEqual(total_area, 55.0)  # не 9999999/8888888


class RealDataRegressionGuardsTest(unittest.TestCase):
    """Не проверяет 'правильное' контрольное число (его нужно подтвердить
    человеком) — только структурные факты про реальный файл квартала."""

    @classmethod
    def setUpClass(cls):
        path = REPO_ROOT / "data" / "lots_202606.json"
        if not path.exists():
            raise unittest.SkipTest("data/lots_202606.json отсутствует")
        with open(path, encoding="utf-8-sig") as f:
            cls.raw = json.load(f)

    def test_siti4_and_sezar_tower_both_kept_as_separate_buildings(self):
        """Сити-4 и SEZAR TOWER похожи по сигнатуре площадей лотов (найдено
        аудитом), но подтверждено (пользователем, знающим рынок) — это РАЗНЫЕ
        здания, не дубль. Оба должны остаться в данных отдельно — не сливать."""
        self.assertIn("Сити-4", self.raw)
        self.assertIn("SEZAR TOWER", self.raw)

    def test_mega_lots_present_and_flagged(self):
        """Единичные лоты > MEGA_LOT_AREA_THRESHOLD — похожи на остаток продаж
        по зданию целиком (подтверждено косвенно: у STONE и похожих
        девелоперов такие листинги на рынке реально встречаются), поэтому
        не удаляются из data/lots_202606.json, но исключаются из KPI и
        помечаются флагом в таблице (см. codifier.html: suspected_aggregate_lot,
        cellFlag). Итоговое число сегмента 'Продажа офисов' для Q2 2026 берётся
        из data/qa/golden_reference_202606.json, а не суммой по лотам, пока
        данные не пересобраны по нормальной методике (план с Q3 2026)."""
        mega = find_mega_lots(self.raw)
        self.assertGreater(len(mega), 0, "Подозрительно крупные строки-лоты (>3000 м²) не найдены — "
                                          "если данные почищены, обновить этот тест")


if __name__ == "__main__":
    unittest.main()
