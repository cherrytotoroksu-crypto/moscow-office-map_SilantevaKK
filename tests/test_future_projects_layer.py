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
        cls.duplicates = cls.payload.get("duplicates", [])

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
        self.assertEqual(self.payload["duplicate_count"], len(self.duplicates))

    def test_confirmed_duplicates_are_not_in_active_layer(self):
        active_ids = {r["id"] for r in self.projects + self.no_coords}
        duplicate_ids = {r["id"] for r in self.duplicates}
        self.assertTrue(active_ids.isdisjoint(duplicate_ids))
        self.assertEqual(
            duplicate_ids,
            {
                "OBJ-0597", "OBJ-0624", "OBJ-0650", "OBJ-0656", "OBJ-0662",
                "OBJ-0667", "OBJ-0682", "OBJ-0685", "OBJ-0762",
                # партия 2026-08-07
                "OBJ-0687", "OBJ-0758", "OBJ-0608", "OBJ-0666",
            },
        )
        canonical_ids = active_ids
        self.assertTrue(all(r.get("duplicate_of") in canonical_ids for r in self.duplicates))

    def test_registry_matched_projects_have_traceable_coordinates(self):
        expected = {
            "OBJ-0675", "OBJ-0678", "OBJ-0683", "OBJ-0690", "OBJ-0697",
            "OBJ-0698", "OBJ-0715", "OBJ-0716", "OBJ-0745", "OBJ-0763",
        }
        records = {r["id"]: r for r in self.projects if r["id"] in expected}
        self.assertEqual(set(records), expected)
        for rec in records.values():
            self.assertTrue(rec.get("matched_existing_name"), rec["id"])
            self.assertTrue(rec.get("coordinates_source"), rec["id"])
            self.assertIn(rec.get("confidence"), {"Высокий", "Средний"})

    def test_shelepikha_coordinate_correction_is_preserved(self):
        rec = next(r for r in self.projects if r["id"] == "OBJ-0405")
        self.assertEqual((rec["lat"], rec["lng"]), (55.759587, 37.525738))
        self.assertTrue(rec["needs_review"])
        self.assertIn("77:01:0004044:3272", rec["review_notes"])

    def test_priority_entity_resolution_corrections_are_preserved(self):
        records = {r["id"]: r for r in self.projects}
        expected_points = {
            "OBJ-0113": (55.774558, 37.507519),
            "OBJ-0115": (55.789255, 37.524964),
            "OBJ-0116": (55.748916, 37.68313),
            "OBJ-0730": (55.815745, 37.601727),
            "OBJ-0732": (55.814955, 37.602988),
            "OBJ-0759": (55.78124, 37.53913),
        }
        for object_id, point in expected_points.items():
            self.assertIn(object_id, records)
            self.assertEqual((records[object_id]["lat"], records[object_id]["lng"]), point)
            self.assertTrue(records[object_id].get("coordinates_source"), object_id)

        obsidian = records["OBJ-0759"]
        self.assertEqual(obsidian["developer"], "Business Club")
        self.assertEqual(obsidian["status"], "Сданный")
        self.assertEqual(obsidian["commission_year"], 2026)
        self.assertNotEqual((obsidian["lat"], obsidian["lng"]), (55.788409, 37.544117))

        ostankino_1 = records["OBJ-0732"]
        self.assertEqual(ostankino_1["status"], "Сданный")
        self.assertEqual(ostankino_1["commission_year"], 2025)

    def test_sources_field_is_always_a_list(self):
        bad = [r["id"] for r in self.projects + self.no_coords if not isinstance(r.get("sources"), list)]
        self.assertEqual(bad, [], f"Поле sources не список: {bad}")

    def test_verified_fili_centre_is_mappable(self):
        rec = next(r for r in self.projects if r["id"] == "OBJ-0601")
        self.assertEqual((rec["lat"], rec["lng"]), (55.741059, 37.509505))
        self.assertEqual(rec["confidence"], "Средний")
        self.assertFalse(rec["needs_review"])

    def test_lomonosov_is_now_mapped_at_verified_building(self):
        """Ломоносов переведён из no_coords на карту: точка подтверждена
        контуром здания в OSM и независимо карточкой 2ГИС (расхождение ~54 м)."""
        rec = next(r for r in self.projects if r["id"] == "OBJ-0574")
        self.assertEqual(rec["address"], "Москва, Раменский бульвар, 1")
        self.assertEqual(rec["status"], "Сданный")
        self.assertEqual(rec["commission_year"], 2023)
        self.assertEqual((rec["lat"], rec["lng"]), (55.692084, 37.516467))
        self.assertTrue(rec.get("coordinates_source"))
        self.assertNotIn("OBJ-0574", {r["id"] for r in self.no_coords})

    def test_stone_towers_b_and_c_stay_separate_buildings(self):
        """Башни B и C — разные здания: их нельзя ни слить друг с другом,
        ни поставить в одну точку. Дубли из remain отведены к своим канонам."""
        by_id = {r["id"]: r for r in self.projects + self.no_coords}
        duplicates = {r["id"]: r for r in self.duplicates}

        self.assertEqual(duplicates["OBJ-0687"]["duplicate_of"], "OBJ-0570")
        self.assertEqual(duplicates["OBJ-0758"]["duplicate_of"], "OBJ-0576")

        tower_b = by_id["OBJ-0570"]
        self.assertEqual((tower_b["lat"], tower_b["lng"]), (55.789858, 37.585881))
        self.assertEqual(tower_b["status"], "Сданный")
        self.assertEqual(tower_b["commission_year"], 2024)
        self.assertTrue(tower_b.get("coordinates_source"))

        tower_c = by_id["OBJ-0576"]
        self.assertNotEqual(
            (tower_b["lat"], tower_b["lng"]),
            (tower_c.get("lat"), tower_c.get("lng")),
            "башни B и C не должны делить одну координату",
        )
        self.assertTrue(tower_c["needs_review"])

    def test_loft_skolkovo_corpuses_are_not_placed_on_quarter_point(self):
        """10 корпусов Лофт-квартала остаются без координат: адреса корпусов
        конфликтуют между источниками, а общую точку квартала наносить нельзя."""
        corpus_ids = {
            "OBJ-0750", "OBJ-0751", "OBJ-0754", "OBJ-0755", "OBJ-0760",
            "OBJ-0761", "OBJ-0764", "OBJ-0765", "OBJ-0767", "OBJ-0779",
        }
        no_coord_ids = {r["id"] for r in self.no_coords}
        self.assertTrue(corpus_ids.issubset(no_coord_ids))
        for rec in (r for r in self.no_coords if r["id"] in corpus_ids):
            self.assertTrue(rec["needs_review"], rec["id"])
            self.assertIn("КОНФЛИКТ АДРЕСОВ", rec["review_notes"], rec["id"])

    def test_stone_hodynka1_towers_are_not_merged_into_the_quarter(self):
        """H1/H2/H3 — отдельные здания (подтверждено archi.ru и STONE), а OBJ-0100 —
        агрегат квартала: их GLA совпадает в сумме, поэтому карточки нельзя
        объединять и нельзя ставить башни в точку квартала."""
        by_id = {r["id"]: r for r in self.projects + self.no_coords}
        duplicate_ids = {r["id"] for r in self.duplicates}
        towers = ["OBJ-0696", "OBJ-0722", "OBJ-0735"]

        for tower_id in towers:
            self.assertNotIn(tower_id, duplicate_ids, f"{tower_id} не дубль агрегата")
            rec = by_id[tower_id]
            self.assertIsNone(rec.get("lat"), tower_id)
            self.assertIsNone(rec.get("lng"), tower_id)
            self.assertEqual(rec["status"], "Строящийся", tower_id)
            self.assertEqual(rec["commission_year"], 2027, tower_id)
            self.assertTrue(rec["needs_review"], tower_id)

        quarter = by_id["OBJ-0100"]
        self.assertAlmostEqual(
            quarter["gla"],
            sum(by_id[t]["gla"] for t in towers),
            places=1,
            msg="GLA агрегата должна совпадать с суммой башен — иначе состав изменился",
        )
        self.assertTrue(quarter["needs_review"])

    def test_life_varshavskaya_is_working_name_of_the_same_bc(self):
        rec = next(r for r in self.duplicates if r["id"] == "OBJ-0666")
        self.assertEqual(rec["duplicate_of"], "OBJ-0262")
        self.assertEqual(rec["confidence"], "Средний")

    def test_unidentifiable_skolkovo_row_is_not_matched_by_toponym(self):
        """«сколково» — топоним, а не имя объекта: машинный аудит даёт score 97,
        но наносить и сливать такую строку нельзя."""
        rec = next(r for r in self.no_coords if r["id"] == "OBJ-0564")
        self.assertIsNone(rec.get("lat"))
        self.assertTrue(rec["needs_review"])
        self.assertIn("ОТКЛОНЕНО", rec["review_notes"])
        self.assertNotIn("OBJ-0564", {r["id"] for r in self.duplicates})

    def test_varshavskaya_does_not_claim_ostankino_commissioning(self):
        """Отклонённое ложное совпадение: ввод корпуса в сентябре 2025 относится
        к OSTANKINO, а не к БЦ «Варшавская» — статус повышать нельзя."""
        rec = next(r for r in self.projects if r["id"] == "OBJ-0262")
        self.assertEqual(rec["status"], "Строящийся")
        self.assertTrue(rec["needs_review"])
        self.assertIn("OSTANKINO", rec["review_notes"])

    def test_springs_is_flagged_as_possible_non_office(self):
        rec = next(r for r in self.no_coords if r["id"] == "OBJ-0244")
        self.assertTrue(rec["needs_review"])
        self.assertIn("исключение из офисного слоя", rec["verification_status"])


if __name__ == "__main__":
    unittest.main()
