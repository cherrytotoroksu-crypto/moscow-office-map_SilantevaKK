"""Регрессия на слой «Все офисные проекты — свод» (data/future_projects.json).

Гарантии, которые задал промпт пользователя (лист «Промпт для Клода» в
Будущие_проекты_очищено_с_памятью.xlsx) и которые легко сломать при
следующем перегоне свода:
  1. ID уникален — записи не склеиваются и не дублируются повторно.
  2. Ни один объект без полной пары координат не попал в projects (то есть
     координаты не додуманы) — такие записи только в no_coords.
  3. Статусы — только из утверждённого справочника, без новых вариантов.
  4. Счётчики в шапке файла совпадают с фактической длиной массивов.
"""
import json
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA = REPO_ROOT / "data" / "future_projects.json"

ALLOWED_STATUSES = {
    "Анонсированный", "Проектный", "Замороженный",
    "Строящийся", "Сданный", "Не определён",
}
ALLOWED_CONFIDENCE = {"Высокий", "Средний", "Низкий"}

# Санити-рамка Москвы с областью — не точная граница, а защита от мусорной
# координаты (0,0 / перепутанные lat-lng / чужой город).
LAT_RANGE = (54.9, 56.5)
LNG_RANGE = (36.3, 38.6)


class FutureProjectsLayerTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not DATA.exists():
            raise unittest.SkipTest("data/future_projects.json отсутствует")
        with DATA.open(encoding="utf-8") as f:
            cls.payload = json.load(f)
        cls.projects = cls.payload["projects"]
        cls.no_coords = cls.payload["no_coords"]

    def test_ids_are_unique_across_both_lists(self):
        ids = [r["id"] for r in self.projects + self.no_coords]
        dupes = {i for i in ids if ids.count(i) > 1}
        self.assertEqual(dupes, set(), f"Дублирующиеся ID в своде: {sorted(dupes)}")

    def test_no_project_on_map_without_real_coordinates(self):
        bad = [r["id"] for r in self.projects if r.get("lat") is None or r.get("lng") is None]
        self.assertEqual(bad, [], f"В projects попали записи без координат: {bad}")

    def test_no_coords_list_really_has_no_coords(self):
        bad = [r["id"] for r in self.no_coords if r.get("lat") is not None and r.get("lng") is not None]
        self.assertEqual(bad, [], f"В no_coords попали записи С координатами: {bad}")

    def test_coordinates_within_moscow_sanity_range(self):
        bad = []
        for r in self.projects:
            if not (LAT_RANGE[0] <= r["lat"] <= LAT_RANGE[1]) or not (LNG_RANGE[0] <= r["lng"] <= LNG_RANGE[1]):
                bad.append((r["id"], r["lat"], r["lng"]))
        self.assertEqual(bad, [], f"Координаты вне санити-рамки Москвы: {bad}")

    def test_statuses_are_from_reference(self):
        seen = {r.get("status") for r in self.projects + self.no_coords}
        unknown = seen - ALLOWED_STATUSES
        self.assertEqual(unknown, set(), f"Неизвестные статусы (справочник не обновлён?): {unknown}")

    def test_confidence_levels_are_from_reference(self):
        seen = {r.get("confidence") for r in self.projects + self.no_coords}
        unknown = seen - ALLOWED_CONFIDENCE
        self.assertEqual(unknown, set(), f"Неизвестные уровни доверия: {unknown}")

    def test_header_counters_match_actual_lengths(self):
        self.assertEqual(self.payload["with_coords"], len(self.projects))
        self.assertEqual(self.payload["without_coords"], len(self.no_coords))
        self.assertEqual(self.payload["total"], len(self.projects) + len(self.no_coords))

    def test_sources_field_is_always_a_list(self):
        bad = [r["id"] for r in self.projects + self.no_coords if not isinstance(r.get("sources"), list)]
        self.assertEqual(bad, [], f"Поле sources не список: {bad}")


if __name__ == "__main__":
    unittest.main()
