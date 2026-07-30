"""Section 10 checks from the online-tables/general-layer task (2026-07-31).

These are the DATA-level invariants that can be verified with a repeatable,
CI-friendly Python test (no JS test runner exists in this project — Node is
not installed in this environment, confirmed before writing this file). The
UI-behavior items from the same section (URL state round-trip, filtered
export) were verified interactively in-browser this session — see the
conversation report, not a repeatable automated test here.

Covered here:
  - no channel mixing (distinct schemas for lots/rent_lots/coworking; valid
    market_channel enum in the registry)
  - unique-project counting is not the same as row counting (Бадаевский)
  - empty values are not silently turned into 0
  - the quarterly map (index.html) never loads the general registry, so it
    cannot show offer-less projects
  - the general registry (data/all_projects_layer.json) keeps projects that
    have no current-quarter offer (quarter_offer_exists=false)
"""
import json
import re
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))
from validate_all_projects_layer import MARKET_CHANNELS

REGISTRY_PATH = REPO_ROOT / "data" / "all_projects_layer.json"


@unittest.skipUnless(REGISTRY_PATH.exists(), "data/all_projects_layer.json not generated yet")
class OnlineTablesInvariantTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))

    # ---- 1. channels are not mixed --------------------------------------
    def test_market_channel_values_are_valid_and_not_mixed_with_lot_schema(self):
        for r in self.registry:
            for ch in r.get("market_channel", []):
                self.assertIn(ch, MARKET_CHANNELS)
            # Общий реестр не должен тащить встроенные лоты конкретного канала —
            # это защищает от случайного смешения продажи/аренды в одном месте.
            for forbidden in ("lots", "rent_lots", "sale_lots", "deal_rows"):
                self.assertNotIn(forbidden, r)

    def test_quarterly_channel_files_have_distinct_non_overlapping_schemas(self):
        # sale (lots_*.json) has price/total/scheme; rent (rent_lots_*.json) has
        # rate/opex/nds/finish; coworking (coworking_*.json) has seats/vacancy/network.
        # None of these channel-specific fields should appear in a different
        # channel's file for the same quarter — that would be exactly the kind
        # of silent channel mixing the task prohibits.
        quarter = "202606"
        with open(REPO_ROOT / "data" / f"lots_{quarter}.json", encoding="utf-8-sig") as f:
            sale = json.load(f)
        with open(REPO_ROOT / "data" / f"rent_lots_{quarter}.json", encoding="utf-8-sig") as f:
            rent = json.load(f)
        with open(REPO_ROOT / "data" / f"coworking_{quarter}.json", encoding="utf-8-sig") as f:
            coworking = json.load(f)

        # "rate" сознательно не входит ни в один набор: оно есть и в rent_lots
        # (ставка аренды, руб/кв.м/год), и в coworking (ставка, руб/мес) —
        # совпадение имени поля при разных единицах измерения, не смешение
        # каналов (каждый канал живёт в отдельном файле/вкладке).
        sale_only_fields = {"price", "total", "scheme"}
        rent_only_fields = {"opex", "nds", "finish"}
        coworking_only_fields = {"seats", "vacancy", "network"}

        sale_fields = set()
        for lots in sale.values():
            for lot in lots:
                sale_fields.update(lot.keys())
        rent_fields = set()
        for lots in rent.values():
            for lot in lots:
                rent_fields.update(lot.keys())
        coworking_fields = set()
        for row in coworking:
            coworking_fields.update(row.keys())

        self.assertTrue(sale_only_fields.issubset(sale_fields))
        self.assertFalse(sale_only_fields & rent_fields)
        self.assertFalse(sale_only_fields & coworking_fields)

        self.assertTrue(rent_only_fields.issubset(rent_fields))
        self.assertFalse(rent_only_fields & sale_fields)
        self.assertFalse(rent_only_fields & coworking_fields)

        self.assertTrue(coworking_only_fields.issubset(coworking_fields))
        self.assertFalse(coworking_only_fields & sale_fields)
        self.assertFalse(coworking_only_fields & rent_fields)

    # ---- 2. unique project count != row count ---------------------------
    def test_unique_project_count_differs_from_row_count_for_badaevsky(self):
        # Правило "не считать проекты по числу строк лотов" — здесь конкретный,
        # уже известный случай: Бадаевский — 2 строки (корпуса), 1 уникальный проект.
        badaevsky_rows = [r for r in self.registry if r["canonical_project_id"] == "badaevsky"]
        self.assertEqual(len(badaevsky_rows), 2)
        unique_ids = {r["canonical_project_id"] for r in self.registry}
        self.assertLess(len(unique_ids), len(self.registry))

    # ---- 3. empty values are not turned into 0 ---------------------------
    def test_missing_area_stays_null_not_zero(self):
        # Записи без известной площади (коворкинг-операторы без gba/gla)
        # должны хранить null, а не 0 — 0 означало бы "площадь равна нулю",
        # что неверно (это "неизвестно").
        no_area_records = [r for r in self.registry if r["project_status"] == "Не установлен"]
        self.assertTrue(no_area_records, "expected at least one coworking-operator-style record")
        for r in no_area_records:
            self.assertIsNone(r["gba"])
            self.assertNotEqual(r["gba"], 0)

    def test_empty_quarter_offer_refs_is_empty_list_not_falsy_sentinel(self):
        no_offer = [r for r in self.registry if not r["quarter_offer_exists"]]
        self.assertTrue(no_offer)
        for r in no_offer:
            self.assertIsInstance(r["quarter_offer_refs"], list)

    # ---- 4. quarterly map cannot show offer-less projects ----------------
    def test_index_html_never_fetches_the_general_registry(self):
        # index.html (квартальная карта) должен строиться ТОЛЬКО из
        # data/buildings_{quarter}.json — если бы он когда-нибудь тоже читал
        # data/all_projects_layer.json напрямую, на карте могли бы всплыть
        # проекты без предложения в выбранном квартале. Пока такого fetch нет —
        # разделение слоёв держится структурно, а не только по соглашению.
        html = (REPO_ROOT / "index.html").read_text(encoding="utf-8")
        self.assertNotIn("all_projects_layer.json", html)

    # ---- 5. the general layer keeps offer-less projects ------------------
    def test_general_registry_keeps_projects_without_current_offer(self):
        no_offer = [r for r in self.registry if not r["quarter_offer_exists"]]
        self.assertGreater(len(no_offer), 0, "general layer should retain at least some no-offer projects")
        # И наоборот: не все записи обязаны иметь предложение (иначе реестр
        # был бы просто копией квартального слоя).
        with_offer = [r for r in self.registry if r["quarter_offer_exists"]]
        self.assertGreater(len(with_offer), 0)
        self.assertLess(len(with_offer), len(self.registry))


if __name__ == "__main__":
    unittest.main()
