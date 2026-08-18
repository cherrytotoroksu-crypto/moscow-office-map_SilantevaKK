"""Мультивыбор фильтра по классу во всех 4 режимах index.html (Продажа/
Аренда/Коворкинги/Все проекты). Раньше фильтра по классу не было вовсе на
карте зданий/коворкингов, а «Все проекты» имел одиночный select — заменён
на чекбоксы.

Заодно найдена и учтена та же проблема, что раньше в lots_*.json:
кириллические омографы класса ("А"/"В"/"В+" вместо латинских A/B/B+) в
data/future_projects.json — normalizeCls() приводит их к латинице перед
сравнением/показом чекбоксов.
"""
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
INDEX_PATH = REPO_ROOT / "index.html"


class ClassFilterMultiselectTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = INDEX_PATH.read_text(encoding="utf-8")

    def test_sale_rent_class_checkboxes_present(self):
        for value in ("Prime", "A", "B+", "B"):
            self.assertIn(f'class="flt-cls" value="{value}"', self.html, value)
        self.assertIn('class="flt-cls" value=""', self.html, "missing 'не указан' bucket")

    def test_coworking_class_checkboxes_present(self):
        for value in ("Prime", "A", "B+", "B"):
            self.assertIn(f'class="flt-cw-cls" value="{value}"', self.html, value)
        self.assertIn('class="flt-cw-cls" value=""', self.html, "missing 'без здания' bucket")

    def test_projects_mode_no_longer_has_single_select_class(self):
        self.assertNotIn('id="fpClass"', self.html)
        self.assertIn('id="fpClassWrap"', self.html)
        self.assertIn('flt-fp-cls', self.html)

    def test_cyrillic_class_homoglyphs_normalized(self):
        self.assertIn("function normalizeCls", self.html)
        for cyr in ("'А': 'A'", "'В': 'B'", "'В+': 'B+'"):
            self.assertIn(cyr, self.html, cyr)

    def test_filter_state_sets_wired_into_filter_functions(self):
        self.assertIn("let filterClass", self.html)
        self.assertIn("let filterCwClass", self.html)
        self.assertIn("filterClass.has(b.cls || '')", self.html)
        self.assertIn("filterCwClass.has(cls)", self.html)
        self.assertIn("clsSet.has(normalizeCls(p.cls))", self.html)

    def test_coworking_class_derived_from_nearest_building_not_own_field(self):
        """Площадки коворкинга не имеют своего класса — берётся у ближайшего
        здания через уже существующий buildingIndexForCoworking (радиус 80 м)."""
        self.assertIn("buildingIndexForCoworking(c)", self.html)


if __name__ == "__main__":
    unittest.main()
