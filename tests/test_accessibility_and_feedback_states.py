"""Regression checks for keyboard accessibility and asynchronous feedback."""

import re
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent


class AccessibilityAndFeedbackStateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.index = (REPO_ROOT / "index.html").read_text(encoding="utf-8")
        cls.analytics = (REPO_ROOT / "analytics.html").read_text(encoding="utf-8")
        cls.codifier = (REPO_ROOT / "codifier.html").read_text(encoding="utf-8")
        cls.classifier = (REPO_ROOT / "classifier.html").read_text(encoding="utf-8")

    def test_all_primary_pages_have_visible_keyboard_focus(self):
        for source in (self.index, self.analytics, self.codifier, self.classifier):
            self.assertIn(":focus-visible", source)

    def test_map_modals_expose_dialog_semantics_and_close_labels(self):
        self.assertGreaterEqual(self.index.count('role="dialog" aria-modal="true"'), 5)
        self.assertGreaterEqual(self.index.count('class="modal-x"'), 5)
        self.assertGreaterEqual(self.index.count('class="modal-x" id='), 5)
        modal_close_tags = re.findall(r'<button class="modal-x"[^>]+>', self.index)
        self.assertTrue(modal_close_tags)
        self.assertTrue(all('aria-label=' in tag for tag in modal_close_tags))

    def test_map_modals_manage_focus_escape_and_tab_cycle(self):
        self.assertIn("const modalReturnFocus = new WeakMap()", self.index)
        self.assertIn("if (e.key === 'Escape')", self.index)
        self.assertIn("if (e.key !== 'Tab') return", self.index)
        self.assertIn("returnTo.focus()", self.index)

    def test_required_map_data_does_not_silently_fall_back_to_empty(self):
        self.assertIn("function fetchJSONRequired", self.index)
        self.assertIn("fetchJSONRequired(currentQuarter.file)", self.index)
        self.assertIn("Обновите страницу", self.index)

    def test_analytics_announces_loading_failures_and_empty_exports(self):
        self.assertIn('id="anaStatus" role="status" aria-live="polite"', self.analytics)
        self.assertIn("const analyticsLoadFailures = new Set()", self.analytics)
        self.assertIn("content.setAttribute('aria-busy', 'true')", self.analytics)
        self.assertIn("content.setAttribute('aria-busy', 'false')", self.analytics)
        self.assertIn("setTimeout(fail, 10000)", self.analytics)
        self.assertIn("выберите вид «Таблица»", self.analytics)
        self.assertIn("exportButton.disabled = !hasData", self.analytics)

    def test_dynamics_dialog_opens_before_heavy_quarter_calculation(self):
        start = self.index.index("async function openDynamics()")
        opened = self.index.index("bg.classList.add('open');", start)
        calculation = self.index.index("await precomputeAll();", start)
        self.assertLess(opened, calculation)
        self.assertIn("Загрузка и расчёт данных по кварталам", self.index)
        self.assertIn("setTimeout(fail, 10000)", self.index)

    def test_codifier_tabs_are_native_buttons_with_aria_state(self):
        self.assertIn('<button class="tab" type="button" role="tab" aria-selected="true"', self.codifier)
        self.assertIn('return `<button class="subtab', self.codifier)
        self.assertIn('id="statusRow" role="status" aria-live="polite"', self.codifier)

    def test_classifier_sort_and_filter_work_from_keyboard(self):
        self.assertIn('<button class="th-label"', self.classifier)
        self.assertIn('panel.setAttribute("role", "dialog")', self.classifier)
        self.assertIn('if (e.key === "Escape")', self.classifier)
        self.assertIn('aria-sort=', self.classifier)

    def test_classifier_loading_error_gives_next_action(self):
        self.assertIn("Загрузка классификатора…", self.classifier)
        self.assertIn("Не удалось загрузить классификатор. Обновите страницу", self.classifier)


if __name__ == "__main__":
    unittest.main()
