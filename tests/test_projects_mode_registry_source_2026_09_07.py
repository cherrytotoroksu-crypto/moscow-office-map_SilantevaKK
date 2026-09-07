"""Regression for switching index.html's «Все проекты» mode from the legacy
data/future_projects.json to the canonical data/all_projects_layer.json
(2026-09-07, explicit user decision — see conversation).

The map render pipeline (renderFuture/fpPopupHtml/getFilteredFuture) is kept
unchanged and instead fed a translated shape via mapAllProjectsLayerRecord().
These tests lock in the translation contract: every project_status/confidence
value actually present in the registry must map to something the existing
render pipeline understands (APL_STATUS_MAP / APL_CONFIDENCE_MAP / the
flt-fp-status checkboxes / FP_STATUS_COLOR), and the new channel filter must
be wired up.
"""
import json
import os
import re
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INDEX_HTML = os.path.join(ROOT, "index.html")
REGISTRY = os.path.join(ROOT, "data", "all_projects_layer.json")


def load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


@unittest.skipUnless(os.path.isfile(REGISTRY), "data/all_projects_layer.json not generated yet")
class ProjectsModeRegistrySourceTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.records = load_json(REGISTRY)
        with open(INDEX_HTML, encoding="utf-8") as f:
            cls.html = f.read()

    def _extract_map(self, var_name):
        m = re.search(var_name + r"\s*=\s*\{(.*?)\};", self.html, re.S)
        self.assertIsNotNone(m, f"{var_name} not found in index.html")
        pairs = re.findall(r"'([^']+)':\s*'([^']+)'", m.group(1))
        return dict(pairs)

    def test_every_project_status_value_is_mapped(self):
        status_map = self._extract_map("APL_STATUS_MAP")
        seen = {r.get("project_status") for r in self.records}
        for value in seen:
            self.assertIn(value, status_map, f"project_status {value!r} has no APL_STATUS_MAP entry")

    def test_mapped_statuses_all_have_a_filter_checkbox(self):
        status_map = self._extract_map("APL_STATUS_MAP")
        for mapped in set(status_map.values()):
            self.assertIn(
                f'class="flt-fp-status" value="{mapped}"', self.html,
                f"no flt-fp-status checkbox for mapped status {mapped!r}",
            )

    def test_mapped_statuses_all_have_a_legend_color(self):
        color_map_block = re.search(r"FP_STATUS_COLOR\s*=\s*\{(.*?)\};", self.html, re.S)
        self.assertIsNotNone(color_map_block)
        colors = dict(re.findall(r"'([^']+)':\s*'(#[0-9a-fA-F]+)'", color_map_block.group(1)))
        status_map = self._extract_map("APL_STATUS_MAP")
        for mapped in set(status_map.values()):
            self.assertIn(mapped, colors, f"no FP_STATUS_COLOR entry for {mapped!r}")

    def test_confidence_values_are_mapped(self):
        conf_map_block = re.search(r"APL_CONFIDENCE_MAP\s*=\s*\{([^}]*)\};", self.html, re.S)
        self.assertIsNotNone(conf_map_block)
        pairs = dict(re.findall(r"(\w+):\s*'([^']+)'", conf_map_block.group(1)))
        seen = {r.get("confidence") for r in self.records}
        for value in seen:
            self.assertIn(value, pairs, f"confidence {value!r} has no APL_CONFIDENCE_MAP entry")

    def test_market_channel_values_are_mapped_for_popup_labels(self):
        label_block = re.search(r"MARKET_CHANNEL_LABEL\s*=\s*\{([^}]*)\};", self.html, re.S)
        self.assertIsNotNone(label_block)
        pairs = dict(re.findall(r"(\w+):\s*'([^']+)'", label_block.group(1)))
        seen = set()
        for r in self.records:
            seen.update(r.get("market_channel") or [])
        for value in seen:
            self.assertIn(value, pairs, f"market_channel {value!r} has no MARKET_CHANNEL_LABEL entry")

    def test_channel_filter_checkboxes_cover_every_channel_plus_none(self):
        for value in ("sale", "rent", "coworking", "__none__"):
            self.assertIn(f'class="flt-fp-channel" value="{value}"', self.html)

    def test_geometry_quality_values_have_labels(self):
        label_block = re.search(r"GEOMETRY_QUALITY_LABEL\s*=\s*\{(.*?)\};", self.html, re.S)
        self.assertIsNotNone(label_block)
        pairs = dict(re.findall(r"'([^']+)':\s*'([^']+)'", label_block.group(1)))
        seen = {r.get("geometry_quality") for r in self.records if r.get("geometry_quality")}
        for value in seen:
            self.assertIn(value, pairs, f"geometry_quality {value!r} has no GEOMETRY_QUALITY_LABEL entry")

    def test_records_marked_duplicate_of_are_excluded_from_the_map(self):
        # loadFutureProjects() filters out `duplicate_of` rows before mapping —
        # this locks in that a duplicate row's canonical target still exists
        # among the live (non-duplicate) records, so nothing is silently lost.
        live_ids = {r["canonical_project_id"] for r in self.records if not r.get("duplicate_of")}
        for r in self.records:
            dup_of = r.get("duplicate_of")
            if dup_of:
                self.assertIn(dup_of, live_ids, f"{r['canonical_project_id']} points to a missing canonical row")


if __name__ == "__main__":
    unittest.main()
