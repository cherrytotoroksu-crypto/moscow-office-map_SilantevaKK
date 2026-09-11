"""Конструктор аналитики (analytics.html) — свободный выбор метрики/
группировки/типа графика поверх data/all_projects_layer.json (снимок) и
data/buildings_{quarter}.json + rent_lots_{quarter}.json + coworking_{quarter}.json
(предложение по кварталам).

Изначально был вкладкой-оверлеем внутри index.html поверх карты, но легенда
картограммы/зум-контролы/подпись автора визуально просвечивали через
оверлей — вынесен на отдельную страницу (как classifier.html/codifier.html).
Эти тесты фиксируют получившуюся архитектуру и главную находку при
проверке в браузере: агрегация коворкингов "по зданиям" через
geo-привязку занижала охват (79 реальных площадок в data/coworking_202606.json
сводились всего к 1 зданию с данными) — исправлено прямой агрегацией по
самим площадкам.
"""
import re
import json
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
ANALYTICS_PATH = REPO_ROOT / "analytics.html"
INDEX_PATH = REPO_ROOT / "index.html"


@unittest.skipUnless(ANALYTICS_PATH.exists(), "analytics.html not created yet")
class AnalyticsConstructorPageTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = ANALYTICS_PATH.read_text(encoding="utf-8")
        cls.index_html = INDEX_PATH.read_text(encoding="utf-8")

    def test_linked_from_index_html(self):
        self.assertIn('href="analytics.html"', self.index_html)

    def test_index_html_has_no_leftover_analytics_mode_code(self):
        for token in ("analyticsMode", "modeAnalytics", "analyticsControls",
                      "analyticsView", "initAnalyticsConstructor"):
            self.assertNotIn(token, self.index_html, token)

    def test_published_by_build_public_site(self):
        build_script = (REPO_ROOT / "scripts" / "build_public_site.py").read_text(encoding="utf-8")
        self.assertIn(r'^analytics\.html$', build_script,
                       "analytics.html must be in ROOT_ALLOW_PATTERNS or it won't survive the public-site build/deploy")

    def test_coworking_channel_aggregates_directly_not_via_building_geomatch(self):
        """Регрессия на найденный в браузере баг: агрегация коворкингов
        через привязку площадки к зданию (bldCoworkVal) занижала охват —
        должна идти напрямую по allCoworking[qid], без geo-matching."""
        self.assertIn("function aggregateCoworkingDirect", self.html)
        self.assertNotIn("bldCoworkVal", self.html)
        # groupBy для коворкингов — network/bc, не cls/developer/submarket
        # (этих полей нет в data/coworking_{quarter}.json)
        self.assertIn("ANA_GROUPBY_QUARTERLY_COWORKING", self.html)

    def test_general_registry_fetch_guarded_by_projects_domain(self):
        occurrences = [m.start() for m in re.finditer(r"fetchJSON\([^)]*all_projects_layer\.json", self.html)]
        self.assertGreater(len(occurrences), 0)
        for idx in occurrences:
            window = self.html[max(0, idx - 400):idx]
            self.assertTrue("domain === 'quarterly'" in window and "} else {" in window, window)

    def test_csp_keeps_scripts_and_styles_local(self):
        csp = re.search(r'Content-Security-Policy" content="([^"]+)"', self.html).group(1)
        self.assertIn("script-src 'self' 'unsafe-inline'", csp)
        self.assertIn("style-src 'self' 'unsafe-inline'", csp)
        self.assertNotIn("https://cdn.jsdelivr.net", csp)
        self.assertNotIn("https://unpkg.com", csp)

    def test_na_label_used_for_missing_groupby_values(self):
        """Записи без значения по оси группировки не должны отбрасываться
        и не должны считаться нулём — помечаются отдельной категорией."""
        self.assertIn("ANA_NA_LABEL", self.html)
        self.assertIn("Не определено", self.html)

    def test_developer_options_refresh_when_end_quarter_changes(self):
        """Селектор девелопера не должен оставаться от квартала инициализации."""
        self.assertIn(
            "document.getElementById('anaQuarterTo').addEventListener('change', onAnaQuarterToChange)",
            self.html,
        )
        self.assertIn("function onAnaQuarterToChange()", self.html)
        self.assertIn("refreshAnaDeveloperOptions();", self.html)

    def test_developer_options_are_limited_to_selected_channel_data(self):
        """Аренда не должна показывать девелоперов только из файла продаж."""
        self.assertIn(
            "(allBuildings[qid] || []).filter(row => anaHasData(row, qid, channel))",
            self.html,
        )
        buildings = json.loads(
            (REPO_ROOT / "data" / "buildings_202606.json").read_text(encoding="utf-8-sig")
        )
        rent = json.loads(
            (REPO_ROOT / "data" / "rent_lots_202606.json").read_text(encoding="utf-8-sig")
        )
        all_developers = {row.get("developer") for row in buildings if row.get("developer")}
        rent_developers = {
            row.get("developer")
            for row in buildings
            if row.get("developer") and (rent.get(row.get("name")) or rent.get(row.get("name_orig")))
        }
        self.assertEqual(len(all_developers), 55)
        self.assertEqual(len(rent_developers), 14)
        self.assertLess(rent_developers, all_developers)

    def test_developer_selector_discloses_available_count(self):
        self.assertIn('`<option value="">Все (${devs.length})</option>`', self.html)

    def test_admin_division_groupby_available_in_all_three_domains(self):
        """2026-09-11: раньше в конструкторе не было группировки по
        административному округу/району — только зона/субрынок/деловой
        район. Ни один файл данных не несёт эти поля готовыми (проверено:
        data/unified_classifier.json 'district' — 0/705 заполнено), поэтому
        считаем сами через point-in-polygon по data/mo.geojson (146 районов,
        поля NAME/NAME_AO), как это уже делает index.html для zone/submarket."""
        for token in ("ANA_GROUPBY_QUARTERLY_SALE_RENT", "ANA_GROUPBY_QUARTERLY_COWORKING",
                      "ANA_GROUPBY_PROJECTS"):
            match = re.search(rf"const {token} = (\[.*?\]);", self.html, re.S)
            self.assertIsNotNone(match, token)
            self.assertIn("'admOkrug'", match.group(1), f"{token} missing admOkrug")
            self.assertIn("'admDistrict'", match.group(1), f"{token} missing admDistrict")

    def test_admin_division_computed_via_point_in_polygon_not_baked_field(self):
        """Округ/район не читаются как готовое поле из JSON (его там нет) —
        вычисляются на лету по координатам через mo.geojson."""
        self.assertIn("function pointInFeature(", self.html)
        self.assertIn("function assignAdminDivision(", self.html)
        self.assertIn("loadMoGeojson", self.html)
        self.assertIn("data/mo.geojson", self.html)
        self.assertIn("properties.NAME_AO", self.html)

    def test_admin_division_assigned_for_all_three_row_sources(self):
        """Здания/лоты, коворкинги и снимок реестра проектов используют
        разные ключи координат (lat/lng vs latitude/longitude) — каждый
        источник должен быть явно прогнан через assignAdminDivision."""
        calls = re.findall(r"assignAdminDivision\(([^,]+),\s*'(\w+)',\s*'(\w+)'\)", self.html)
        targets = {c[0].strip() for c in calls}
        self.assertIn("blds", targets)
        self.assertIn("coworking", targets)
        self.assertIn("analyticsProjectsData", targets)
        by_target = {c[0].strip(): (c[1], c[2]) for c in calls}
        self.assertEqual(by_target["analyticsProjectsData"], ("latitude", "longitude"))
        self.assertEqual(by_target["blds"], ("lat", "lng"))
        self.assertEqual(by_target["coworking"], ("lat", "lng"))


if __name__ == "__main__":
    unittest.main()
