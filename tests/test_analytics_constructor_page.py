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


if __name__ == "__main__":
    unittest.main()
