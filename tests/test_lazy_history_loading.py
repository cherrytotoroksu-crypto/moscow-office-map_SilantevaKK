import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class LazyHistoryLoadingTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = (ROOT / "index.html").read_text(encoding="utf-8")

    def test_history_has_shared_building_and_per_mode_caches(self):
        self.assertIn("let historicalBuildingsPromise = null", self.source)
        self.assertIn("const precomputedModes = new Set()", self.source)
        self.assertIn("const precomputeModePromises = {}", self.source)
        self.assertIn("async function ensureHistoricalBuildings()", self.source)
        self.assertIn("async function precomputeHistoryMode(mode)", self.source)

    def test_sale_history_does_not_eagerly_fetch_rent_or_coworking(self):
        start = self.source.index("async function precomputeHistoryMode(mode)")
        end = self.source.index("async function precomputeAll()", start)
        body = self.source[start:end]
        self.assertIn("if (historyMode === 'rent')", body)
        self.assertIn("else if (historyMode === 'coworking')", body)
        self.assertNotIn("Promise.all([\n      fetchJSON(q.file", body)

    def test_current_quarter_data_is_reused(self):
        self.assertIn("q.id === currentQuarter.id && !projectsMode && buildingsData.length", self.source)
        self.assertIn("q.id === currentQuarter.id && !projectsMode\n        ? rentLotsData", self.source)
        self.assertIn("q.id === currentQuarter.id && !projectsMode\n        ? coworkingData", self.source)

    def test_mode_switches_request_their_own_history(self):
        self.assertIn("await precomputeHistoryMode(mode)", self.source)
        self.assertIn("await precomputeHistoryMode(this.value)", self.source)

    def test_compare_dialog_opens_before_history_calculation(self):
        start = self.source.index("async function openCompare()")
        opened = self.source.index("bg.classList.add('open')", start)
        calculation = self.source.index("await precomputeAll()", start)
        self.assertLess(opened, calculation)
        self.assertIn("Загрузка и расчёт сравнения", self.source)
        self.assertIn('id="cmpBody" role="status" aria-live="polite"', self.source)

    def test_empty_comparison_disables_export(self):
        self.assertIn("document.getElementById('cmpDownload').disabled = rows.length === 0", self.source)


if __name__ == "__main__":
    unittest.main()
