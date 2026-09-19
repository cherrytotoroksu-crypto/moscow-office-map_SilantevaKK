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

    def test_q2_under_construction_baseline_is_101_buildings_and_53_developers(self):
        # 2026-09-14: было 83/47 — выросло на 8 зданий из-за коммитов b948753/
        # a5d1fb5/e111839 (Поле x2 башни, Мираполис, БЦ Север, БЦ Северный
        # Порт, БЦ РЕ:ПОРТ, STONE Tower E, БЦ «ПОРТА»), все получили записи
        # в реестре data/all_projects_layer.json (см. commit fixing
        # test_all_buildings_202606_map_to_registry). Затем 91: Останкино
        # разбит на 5 корпус-строк (К2+К3 объединены — в классификаторе есть
        # только их суммарная площадь), все "Сдан" — не попадают в этот
        # список. Затем 93: Air разбит на 3 башни (proj-112), все "Строится"
        # — +2 строки к списку; developers не изменилось — Tekta уже
        # учитывался через агрегатную строку "Air".
        rows = [row for row in self.buildings if row.get("status") == "Строится"]
        developers = {row.get("developer") or "—" for row in rows}
        self.assertEqual(len(rows), 101)
        # 2026-09-19: 53 -> 49 — слиты разные написания одного девелопера
        # (Forma/FORMA, Гранель/ГК Гранель, Основа/ГК Основа).
        self.assertEqual(len(developers), 49)

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
