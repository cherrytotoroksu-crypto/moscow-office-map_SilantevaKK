"""Regression checks for filtered developer aggregation in online tables."""
import json
import re
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
CODIFIER = REPO_ROOT / "codifier.html"
Q2_BUILDINGS = REPO_ROOT / "data" / "buildings_202606.json"


class SaleDeveloperFilterRegressionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = CODIFIER.read_text(encoding="utf-8")
        cls.buildings = json.loads(Q2_BUILDINGS.read_text(encoding="utf-8-sig"))

    def test_q2_under_construction_baseline_is_83_buildings_and_47_developers(self):
        rows = [row for row in self.buildings if row.get("status") == "Строится"]
        developers = {row.get("developer") or "—" for row in rows}
        self.assertEqual(len(rows), 83)
        self.assertEqual(len(developers), 47)

    def test_developer_loader_filters_source_buildings_before_grouping(self):
        match = re.search(
            r"async function loadSaleDevelopers\(quarterId\)\s*\{(.*?)\n\}",
            self.html,
            re.S,
        )
        self.assertIsNotNone(match, "loadSaleDevelopers not found")
        body = match.group(1)
        filter_pos = body.find("getFilteredRows(state.sale_buildings, 'sale_buildings')")
        grouping_pos = body.find("for (const b of buildings)")
        self.assertGreaterEqual(filter_pos, 0)
        self.assertGreater(grouping_pos, filter_pos)

    def test_developer_presets_target_the_source_building_state(self):
        self.assertIn(
            "const presetTs = currentView === 'sale_developers' ? state.sale_buildings : ts;",
            self.html,
        )
        self.assertIn("loadSaleDevelopers(currentQuarterId);", self.html)
        self.assertIn("findKey('status', 'project_status', 'reg_project_status')", self.html)

    def test_developer_view_discloses_source_building_count(self):
        self.assertIn("зданий в агрегате: ${meta.sourceCount} из ${meta.totalSourceCount}", self.html)


if __name__ == "__main__":
    unittest.main()
