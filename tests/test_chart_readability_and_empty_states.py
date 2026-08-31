"""Regression checks for analytical chart readability and feedback states."""

import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent


class ChartReadabilityAndEmptyStateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.index = (REPO_ROOT / "index.html").read_text(encoding="utf-8")
        cls.analytics = (REPO_ROOT / "analytics.html").read_text(encoding="utf-8")

    def test_missing_periods_are_not_connected_as_continuous_lines(self):
        self.assertNotIn("spanGaps:true", self.index)
        self.assertNotIn("spanGaps: true", self.analytics)
        self.assertIn("spanGaps:false", self.index)
        self.assertIn("spanGaps: false", self.analytics)

    def test_dynamics_and_comparison_have_actionable_empty_states(self):
        self.assertIn('id="dynEmpty"', self.index)
        self.assertIn("Для выбранного здания и показателя данных нет", self.index)
        self.assertIn("Для выбранных периодов и показателя данных нет", self.index)
        self.assertIn("download.disabled = !hasData", self.index)

    def test_analytics_uses_horizontal_bars_and_compact_numeric_ticks(self):
        self.assertIn("indexAxis: type === 'bar' ? 'y' : 'x'", self.analytics)
        self.assertIn("callback:anaCompactNumber", self.analytics)
        self.assertIn("anaShortLabel(this.getLabelForValue(value))", self.analytics)

    def test_line_chart_opens_with_enough_periods_to_show_a_trend(self):
        self.assertIn("toIndex - fromIndex + 1 < 8", self.analytics)
        self.assertIn("fromSel.value = qs[Math.max(0, toIndex - 7)].id", self.analytics)

    def test_single_series_stacked_chart_is_removed(self):
        self.assertNotIn('<option value="stacked">', self.analytics)
        self.assertNotIn("isStacked", self.analytics)

    def test_doughnut_is_limited_to_additive_metrics(self):
        self.assertIn("ANA_COMPOSITION_METRICS", self.analytics)
        self.assertIn("doughnutOption.disabled = !compositionAllowed", self.analytics)
        self.assertIn("не образуют доли целого", self.analytics)

    def test_analytics_has_chart_and_table_empty_states(self):
        self.assertIn('id="anaEmpty"', self.analytics)
        self.assertIn("По выбранным фильтрам данных нет", self.analytics)

    def test_clearing_all_statuses_produces_an_empty_selection(self):
        self.assertNotIn("statusFilter && statusFilter.length", self.analytics)
        self.assertIn("statusFilter && !statusFilter.includes(r.project_status)", self.analytics)


if __name__ == "__main__":
    unittest.main()
