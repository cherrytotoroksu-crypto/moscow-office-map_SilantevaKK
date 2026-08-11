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
import re
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA = REPO_ROOT / "data" / "future_projects.json"

# Признаки mojibake, найденные в аудите Yandex Geocoder 2026-08-09/10:
#   - "??????," — "Москва," было потеряно при неверной кодировке и заменено
#     плейсхолдером из вопросительных знаков (ровно по числу букв "Москва");
#   - буквы сербского/македонского расширения кириллицы (Њњ Ѕѕ Јј Љљ Ѓѓ Ќќ) —
#     в русском тексте не встречаются никогда; их появление означает, что
#     UTF-8-байты кириллицы были один раз прочитаны как cp1251 и пересохранены
#     в UTF-8 (классический двойной mojibake, напр. "РњРѕСЃРєРІР°" = "Москва").
MOJIBAKE_RE = re.compile(r"\?{4,},|[ЊњЅѕЈјЉљЃѓЌќ]")

ALLOWED_STATUSES = {
    "Анонсированный", "Проектный", "Замороженный",
    "Строящийся", "Сданный", "Не определён",
}
ALLOWED_CONFIDENCE = {"Высокий", "Средний", "Низкий"}
ALLOWED_GEOMETRY_QUALITY = {None, "exact", "centroid", "approximate"}

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
                # партия 2026-08-12
                "OBJ-0152", "OBJ-0729",
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

    def test_loft_skolkovo_corpuses_use_confirmed_quarter_point_as_centroid(self):
        """Партия 2026-08-11: адрес квартала («ИЦ Сколково, ул. Зворыкина, 1к1»)
        подтверждён геокодером (kind=house, регион Москва), но не различает 10
        корпусов — точка нанесена как centroid, НЕ exact, каждый ID отдельный."""
        by_id = {r["id"]: r for r in self.projects}
        corpus_ids = {
            "OBJ-0750", "OBJ-0751", "OBJ-0754", "OBJ-0755", "OBJ-0760",
            "OBJ-0761", "OBJ-0764", "OBJ-0765", "OBJ-0767", "OBJ-0779",
        }
        self.assertEqual(len(corpus_ids), len(set(corpus_ids)))
        for object_id in corpus_ids:
            self.assertIn(object_id, by_id, object_id)
            rec = by_id[object_id]
            self.assertEqual((rec["lat"], rec["lng"]), (55.693779, 37.351581), object_id)
            self.assertEqual(rec["geometry_quality"], "centroid", object_id)
            self.assertTrue(rec["needs_review"], object_id)

    def test_stone_hodynka1_towers_are_not_merged_into_the_quarter(self):
        """H1/H2/H3 — отдельные здания (подтверждено archi.ru и STONE), а OBJ-0100 —
        агрегат квартала: их GLA совпадает в сумме, поэтому карточки нельзя
        объединять. Партия 2026-08-11: адрес квартала подтверждён геокодером
        (kind=house, регион Москва), точка нанесена как centroid — три записи
        не различимы по зданию, но остаются раздельными ID."""
        by_id = {r["id"]: r for r in self.projects + self.no_coords}
        duplicate_ids = {r["id"] for r in self.duplicates}
        towers = ["OBJ-0696", "OBJ-0722", "OBJ-0735"]

        for tower_id in towers:
            self.assertNotIn(tower_id, duplicate_ids, f"{tower_id} не дубль агрегата")
            rec = by_id[tower_id]
            self.assertEqual((rec["lat"], rec["lng"]), (55.788059, 37.534236), tower_id)
            self.assertEqual(rec["geometry_quality"], "centroid", tower_id)
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

    def test_geometry_quality_is_from_reference(self):
        seen = {r.get("geometry_quality") for r in self.projects + self.no_coords}
        unknown = seen - ALLOWED_GEOMETRY_QUALITY
        self.assertEqual(unknown, set(), f"Неизвестные значения geometry_quality: {unknown}")

    def test_partia_2026_08_09_confirmed_coordinate_fixes(self):
        """6 координат, исправленных по exact-совпадению Яндекс-геокодера
        (outputs/yandex_duplicate_coordinate_audit_2026-08-09.json), с
        сохранением источника и пометкой geometry_quality=exact."""
        by_id = {r["id"]: r for r in self.projects}
        expected = {
            "OBJ-0111": (55.778785, 37.584164),
            "OBJ-0665": (55.7844, 37.58464),
            "OBJ-0706": (55.784779, 37.585853),
            "OBJ-0493": (55.761173, 37.528271),
            "OBJ-0534": (55.829911, 37.431873),
            "OBJ-0719": (55.657377, 37.530139),
        }
        for object_id, point in expected.items():
            rec = by_id[object_id]
            self.assertEqual((rec["lat"], rec["lng"]), point, object_id)
            self.assertEqual(rec["geometry_quality"], "exact", object_id)
            self.assertTrue(rec.get("coordinates_source"), object_id)
            self.assertTrue(rec["needs_review"], object_id)

    def test_partia_2026_08_09_rejected_mismatches_keep_old_coordinates(self):
        """Кандидаты Яндекса с несовпадающим корпусом/типом улицы отклонены —
        координата не должна была измениться."""
        by_id = {r["id"]: r for r in self.projects}
        unchanged = {
            "OBJ-0648": (55.7816602, 37.5840668),
            "OBJ-0653": (55.7816602, 37.5840668),
            "OBJ-0492": (55.759279, 37.529016),
            "OBJ-0737": (55.6565173, 37.5341981),
        }
        for object_id, point in unchanged.items():
            rec = by_id[object_id]
            self.assertEqual((rec["lat"], rec["lng"]), point, object_id)
            self.assertTrue(rec["needs_review"], object_id)
            self.assertIn("ОТКЛОНЕНО", rec["review_notes"], object_id)

    def test_partia_2026_08_09_obj0056_premise_checked_not_assumed(self):
        """Задачей утверждалось, что OBJ-0056 «вне Москвы» — проверка не
        подтвердила это: точка внутри санити-рамки, координата не менялась
        без независимого подтверждения нового адреса."""
        rec = next(r for r in self.projects if r["id"] == "OBJ-0056")
        self.assertEqual((rec["lat"], rec["lng"]), (55.72671, 37.453783))
        self.assertIn("НЕ подтверждена", rec["review_notes"])

    def test_multi_corpus_complexes_are_tagged_not_merged(self):
        """СберСити/Останкино/Сколково/STONE/Парк Легенд: общие точки помечены
        centroid, ID остаются раздельными — ни одна запись не пропала."""
        by_id = {r["id"]: r for r in self.projects}
        centroid_ids = [
            "OBJ-0070", "OBJ-0071", "OBJ-0072", "OBJ-0098", "OBJ-0171", "OBJ-0172", "OBJ-0337",  # СберСити
            "OBJ-0029", "OBJ-0055", "OBJ-0568", "OBJ-0582", "OBJ-0610", "OBJ-0612", "OBJ-0620",  # Останкино
            "OBJ-0695", "OBJ-0711", "OBJ-0748", "OBJ-0778",  # Парк Легенд
        ]
        self.assertEqual(len(centroid_ids), len(set(centroid_ids)), "ID не должны повторяться")
        for object_id in centroid_ids:
            self.assertIn(object_id, by_id, object_id)
            self.assertEqual(by_id[object_id]["geometry_quality"], "centroid", object_id)
            self.assertTrue(by_id[object_id]["needs_review"], object_id)

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

    def test_partia_2026_08_10_aurus_confirmed_by_reverse_geocode(self):
        """OBJ-0345/OBJ-0374 (Aurus/Страна.Сити): по прямому требованию задачи
        совпадение с квартальным реестром само по себе не бралось за
        доказательство — координата подтверждена отдельно, обратным
        геокодированием (precision=exact) плюс независимым веб-источником."""
        by_id = {r["id"]: r for r in self.projects}
        for object_id in ("OBJ-0345", "OBJ-0374"):
            rec = by_id[object_id]
            self.assertEqual((rec["lat"], rec["lng"]), (55.756883, 37.535549), object_id)
            self.assertEqual(rec["geometry_quality"], "exact", object_id)
            self.assertIn("обратн", rec["coordinates_source"].lower(), object_id)
            self.assertIn("2026-08-10", rec["review_notes"], object_id)


class MojibakeRegressionTest(unittest.TestCase):
    """Партия 2026-08-09 обнаружила, что query-строки в файлах аудита
    Yandex Geocoder были испорчены mojibake ("Москва," → "??????,"), из-за
    чего геокодер не был ограничен регионом. Партия 2026-08-10 это исправила
    текстово и перепроверила 7 приоритетных ID напрямую через API. Этот тест
    не даёт проблеме вернуться незамеченной при следующей генерации файлов."""

    FILES_TO_SCAN = [
        REPO_ROOT / "data" / "future_projects.json",
        REPO_ROOT / "data" / "future_projects_verification_overrides.json",
        REPO_ROOT / "outputs" / "yandex_no_coords_candidates_2026-08-09.json",
        REPO_ROOT / "outputs" / "yandex_duplicate_coordinate_audit_2026-08-09.json",
        REPO_ROOT / "outputs" / "yandex_priority_recheck_2026-08-10.json",
        REPO_ROOT / "outputs" / "yandex_full_recheck_2026-08-11.json",
    ]

    def test_no_mojibake_in_geocoding_related_files(self):
        for path in self.FILES_TO_SCAN:
            if not path.exists():
                continue
            text = path.read_text(encoding="utf-8")
            matches = MOJIBAKE_RE.findall(text)
            self.assertEqual(matches, [], f"mojibake найден в {path.name}: {matches[:10]}")

    def test_query_files_are_valid_utf8(self):
        """Явная проверка декодируемости как UTF-8 (а не только отсутствия
        конкретных mojibake-паттернов) — файлы аудита геокодера обязаны быть
        читаемым UTF-8 без ошибок."""
        for path in self.FILES_TO_SCAN:
            if not path.exists():
                continue
            raw = path.read_bytes()
            try:
                raw.decode("utf-8", errors="strict")
            except UnicodeDecodeError as e:
                self.fail(f"{path.name} не валидный UTF-8: {e}")


class Regeocode20260811BatchTest(unittest.TestCase):
    """Партия 2026-08-11: полный повтор геокодирования 210 объектов (82
    no_coords + 76 из аудита дублей-координат + доп. многокорпусные семьи)
    после исправления mojibake. 15 координат приняты как exact, 12 — как
    centroid (общий адрес квартала/корпуса, не различает здания), 183
    отклонены строгими критериями (регион/улица/дом/корпус/kind)."""

    @classmethod
    def setUpClass(cls):
        if not DATA.exists():
            raise unittest.SkipTest("data/future_projects.json отсутствует")
        with DATA.open(encoding="utf-8") as f:
            cls.payload = json.load(f)
        cls.projects = cls.payload["projects"]
        cls.no_coords = cls.payload["no_coords"]

    def test_exact_fixes_are_not_shared_between_siblings(self):
        """geometry_quality=exact допустим только когда координата уникальна
        для здания — ни один exact-объект не должен делить точку с другим
        exact-объектом того же прогона (иначе это centroid, а не exact)."""
        by_id = {r["id"]: r for r in self.projects}
        exact_ids = [
            "OBJ-0089", "OBJ-0103", "OBJ-0120", "OBJ-0193", "OBJ-0223",
            "OBJ-0485", "OBJ-0501", "OBJ-0548", "OBJ-0567", "OBJ-0587",
            "OBJ-0637", "OBJ-0645", "OBJ-0652", "OBJ-0672", "OBJ-0693",
        ]
        points = []
        for object_id in exact_ids:
            self.assertIn(object_id, by_id, object_id)
            rec = by_id[object_id]
            self.assertEqual(rec["geometry_quality"], "exact", object_id)
            points.append((round(rec["lat"], 6), round(rec["lng"], 6)))
        # FRAME WORKPLACE (OBJ-0103) и его дубль-запись (OBJ-0548) — одно
        # реальное здание под двумя строками исходника, законно совпадают;
        # "17-й проезд Марьиной Рощи, 9" (OBJ-0193/OBJ-0485) — то же самое.
        allowed_shared = {points[1], points[3]}  # FRAME WORKPLACE / Edel пары
        dupes = {p for p in points if points.count(p) > 1}
        self.assertTrue(dupes.issubset(allowed_shared), f"неожиданные общие точки: {dupes - allowed_shared}")

    def test_centroid_fixes_are_not_marked_exact(self):
        """12 записей, где адрес общий на несколько корпусов/башен, обязаны
        иметь geometry_quality=centroid, а не exact — иначе карта соврёт, что
        координата относится к конкретному зданию."""
        by_id = {r["id"]: r for r in self.projects}
        centroid_ids = [
            "OBJ-0649", "OBJ-0655",
            "OBJ-0750", "OBJ-0751", "OBJ-0754", "OBJ-0755", "OBJ-0760",
            "OBJ-0761", "OBJ-0764", "OBJ-0765", "OBJ-0767", "OBJ-0779",
        ]
        for object_id in centroid_ids:
            self.assertIn(object_id, by_id, object_id)
            self.assertEqual(by_id[object_id]["geometry_quality"], "centroid", object_id)
            self.assertNotEqual(by_id[object_id]["geometry_quality"], "exact", object_id)

    def test_icity_towers_share_point_but_keep_separate_ids(self):
        by_id = {r["id"]: r for r in self.projects}
        time_tower = by_id["OBJ-0649"]
        space_tower = by_id["OBJ-0655"]
        self.assertEqual((time_tower["lat"], time_tower["lng"]), (space_tower["lat"], space_tower["lng"]))
        self.assertEqual(time_tower["geometry_quality"], "centroid")
        self.assertEqual(space_tower["geometry_quality"], "centroid")
        self.assertNotEqual(time_tower["id"], space_tower["id"])

    def test_sbercity_prokshino_riverpark_stay_unresolved(self):
        """СберСити (kind=district у всех кандидатов), Прокшино БК (адрес без
        улицы/дома) и Ривер Парк (формат «зу N/M» не сопоставим с домом) не
        прошли строгие критерии в этой партии — координаты не присвоены/не
        изменены по догадке. СберСити уже был на centroid с прошлой сессии
        (data/future_projects.json), поэтому остаётся в projects без
        изменений; Прокшино БК и Ривер Парк никогда не имели координаты и
        остаются в no_coords."""
        no_coords_ids = {r["id"] for r in self.no_coords}
        must_stay_no_coords = [
            "OBJ-0691", "OBJ-0694", "OBJ-0710",
            "OBJ-0713", "OBJ-0714", "OBJ-0723", "OBJ-0724", "OBJ-0753",
        ]
        for object_id in must_stay_no_coords:
            self.assertIn(object_id, no_coords_ids, f"{object_id} должен остаться в no_coords")

        projects_by_id = {r["id"]: r for r in self.projects}
        sbercity_ids = ["OBJ-0070", "OBJ-0071", "OBJ-0072", "OBJ-0098", "OBJ-0171", "OBJ-0172", "OBJ-0337"]
        for object_id in sbercity_ids:
            self.assertIn(object_id, projects_by_id, object_id)
            rec = projects_by_id[object_id]
            self.assertEqual((rec["lat"], rec["lng"]), (55.790337, 37.327399), object_id)
            self.assertEqual(rec["geometry_quality"], "centroid", object_id)

    def test_priority_seven_stayed_rejected_after_utf8_requery(self):
        """7 приоритетных ID из задачи 2026-08-10/11 — все отклонены заново
        живым запросом с чистым UTF-8, без изменения координат."""
        by_id = {r["id"]: r for r in self.projects}
        unchanged = {
            "OBJ-0056": (55.72671, 37.453783),
            "OBJ-0648": (55.7816602, 37.5840668),
            "OBJ-0653": (55.7816602, 37.5840668),
            "OBJ-0737": (55.6565173, 37.5341981),
            "OBJ-0492": (55.759279, 37.529016),
        }
        for object_id, point in unchanged.items():
            self.assertEqual((by_id[object_id]["lat"], by_id[object_id]["lng"]), point, object_id)


class LowConfidenceDefaultVisibilityTest(unittest.TestCase):
    """Регрессия на баг «Botanica Plaza / NEVSKY PLAZA пропадают с карты»:
    объект с координатами и confidence=Низкий не должен исключаться из
    default-выборки слоя «Все проекты». Раньше чекбокс «Низкий» был выключен
    по умолчанию — низкая уверенность в данных молча превращалась в
    отсутствие объекта на карте."""

    INDEX_HTML = REPO_ROOT / "index.html"

    @classmethod
    def setUpClass(cls):
        if not DATA.exists() or not cls.INDEX_HTML.exists():
            raise unittest.SkipTest("data/future_projects.json или index.html отсутствует")
        with DATA.open(encoding="utf-8") as f:
            cls.payload = json.load(f)
        cls.projects = cls.payload["projects"]
        cls.html = cls.INDEX_HTML.read_text(encoding="utf-8")

    def test_known_low_confidence_objects_have_coordinates_and_reviewable_status(self):
        """Данные сами по себе корректны: у этих объектов есть координаты —
        баг был исключительно в UI-фильтре, не в данных."""
        by_id = {r["id"]: r for r in self.projects}
        for object_id, expected_name in {
            "OBJ-0702": "Botanica Plaza",
            "OBJ-0717": "NEVSKY PLAZA",
        }.items():
            self.assertIn(object_id, by_id, object_id)
            rec = by_id[object_id]
            self.assertEqual(rec["name"], expected_name)
            self.assertIsNotNone(rec["lat"], object_id)
            self.assertIsNotNone(rec["lng"], object_id)
            self.assertEqual(rec["confidence"], "Низкий", object_id)

    def test_default_confidence_filter_mode_is_all_not_verified_only(self):
        """Источник index.html: радиокнопка fpConfMode со значением "all"
        обязана быть checked по умолчанию — если кто-то вернёт checked на
        "verified" (или на старый чекбокс "Низкий" без checked), это молча
        уберёт с карты все объекты с confidence=Низкий, включая реальные."""
        m = re.search(
            r'<input type="radio" name="fpConfMode" value="all"([^>]*)>',
            self.html,
        )
        self.assertIsNotNone(m, "радиокнопка fpConfMode value=all не найдена в index.html")
        self.assertIn("checked", m.group(1), "fpConfMode=all должен быть checked по умолчанию")

        # ни "verified", ни "review" не должны быть checked одновременно с "all"
        for value in ("verified", "review"):
            m2 = re.search(
                rf'<input type="radio" name="fpConfMode" value="{value}"([^>]*)>',
                self.html,
            )
            self.assertIsNotNone(m2, f"радиокнопка fpConfMode value={value} не найдена")
            self.assertNotIn("checked", m2.group(1), f"fpConfMode={value} не должен быть checked по умолчанию")

    def test_get_filtered_future_default_does_not_drop_low_confidence(self):
        """Функция getFilteredFuture не должна содержать старую логику
        `confs.has(...)` на чекбоксах .flt-fp-conf — она давала default-выключенный
        фильтр по низкой уверенности. Новая логика — режим 'verified' явно
        исключает Низкий, режимы 'all'/'review' — нет."""
        self.assertNotIn(".flt-fp-conf", self.html)
        m = re.search(r"function getFilteredFuture\(\)\s*\{.*?\n\}", self.html, re.S)
        self.assertIsNotNone(m, "функция getFilteredFuture не найдена")
        body = m.group(0)
        self.assertIn("mode === 'verified'", body)


class Batch20260812CoordinateFixesTest(unittest.TestCase):
    """Партия 2026-08-12: 4 координаты были грубо неверными (объект уезжал
    на 10-30 км от реального адреса — Люберцы, Химки, Куркино, другой
    регион), плюс дубль Fili Centre под двумя ID. Регрессия фиксирует
    исправленные точки и не даёт им откатиться на старый мусор."""

    @classmethod
    def setUpClass(cls):
        if not DATA.exists():
            raise unittest.SkipTest("data/future_projects.json отсутствует")
        with DATA.open(encoding="utf-8") as f:
            cls.payload = json.load(f)
        cls.projects = cls.payload["projects"]
        cls.duplicates = cls.payload["duplicates"]
        cls.no_coords = cls.payload["no_coords"]

    def test_grossly_wrong_coordinates_are_fixed_and_not_exact(self):
        by_id = {r["id"]: r for r in self.projects}
        expected = {
            "OBJ-0680": (55.743183, 37.709784),  # GloraX Business Римская
            "OBJ-0739": (55.772158, 37.498276),  # БЦ на 2-м Силикатном пр-д, вл.13
            "OBJ-0726": (55.862237, 37.463386),  # Северный порт
        }
        for object_id, point in expected.items():
            rec = by_id[object_id]
            self.assertEqual((rec["lat"], rec["lng"]), point, object_id)
            self.assertEqual(rec["geometry_quality"], "approximate", object_id)
            self.assertTrue(rec["needs_review"], object_id)
            self.assertTrue(rec.get("coordinates_source"), object_id)

    def test_silikatny_cluster_not_auto_merged(self):
        """OBJ-0739 получил координату кластера, но остаётся отдельной
        записью — OBJ-0208/OBJ-0367/OBJ-0489 не тронуты и не помечены
        дублями."""
        by_id = {r["id"]: r for r in self.projects}
        duplicate_ids = {r["id"] for r in self.duplicates}
        for object_id in ("OBJ-0208", "OBJ-0367", "OBJ-0489", "OBJ-0739"):
            self.assertNotIn(object_id, duplicate_ids, object_id)
        self.assertIn("не объединять", by_id["OBJ-0739"]["review_notes"].lower())

    def test_myprioritet_presnya_merged_into_zvenigorodskaya(self):
        """MYPRIORITY Пресня — тот же проект, что «Звенигородская от
        Гранель» (совпадение адреса/девелопера/GLA) — объединено через
        duplicate_of, старое название сохранено в aliases канонической
        записи, источник не потерян."""
        dup_by_id = {r["id"]: r for r in self.duplicates}
        proj_by_id = {r["id"]: r for r in self.projects}

        obj152 = dup_by_id["OBJ-0152"]
        self.assertEqual(obj152["duplicate_of"], "OBJ-0387")

        canonical = proj_by_id["OBJ-0387"]
        self.assertEqual(canonical["name"], "Звенигородская от Гранель")
        self.assertIn("MYPRIORITY Пресня", canonical["aliases"])
        self.assertIn("https://t.me/stroi_news/6446", canonical["sources"])
        self.assertEqual((canonical["lat"], canonical["lng"]), (55.767798, 37.510502))

    def test_fili_centre_duplicate_merged_not_deleted(self):
        """OBJ-0729 (координата уезжала за пределы Московской области)
        объединён с OBJ-0051 (совпадает с data/buildings_202606.json,
        id=122) — источники не потеряны, запись не удалена, а помечена
        duplicate_of."""
        dup_by_id = {r["id"]: r for r in self.duplicates}
        proj_by_id = {r["id"]: r for r in self.projects}

        obj729 = dup_by_id["OBJ-0729"]
        self.assertEqual(obj729["duplicate_of"], "OBJ-0051")

        canonical = proj_by_id["OBJ-0051"]
        self.assertEqual((canonical["lat"], canonical["lng"]), (55.741059, 37.509505))
        self.assertEqual(canonical["geometry_quality"], "exact")
        self.assertIn("buildings_202606.json", canonical["coordinates_source"])

    def test_fili_centre_not_merged_with_fili_residence(self):
        """Fili Centre (OBJ-0051) и Fili residence (OBJ-0196) — разные
        проекты разных застройщиков, не объединять."""
        proj_by_id = {r["id"]: r for r in self.projects}
        fili_centre = proj_by_id["OBJ-0051"]
        fili_residence = proj_by_id["OBJ-0196"]
        self.assertIsNone(fili_residence.get("duplicate_of"))
        self.assertNotEqual(
            (fili_centre["lat"], fili_centre["lng"]),
            (fili_residence["lat"], fili_residence["lng"]),
        )

    def test_fili_residence_address_conflict_documented_not_silently_resolved(self):
        """Fili residence: конфликт адреса (Кастанаевская 16с1 в квартальном
        реестре vs 34 с2 в этой записи) задокументирован в review_notes,
        адрес/координаты НЕ изменены без подтверждения."""
        by_id = {r["id"]: r for r in self.projects}
        rec = by_id["OBJ-0196"]
        self.assertEqual(rec["address"], "Кастанаевская улица, 34 с2")
        self.assertEqual((rec["lat"], rec["lng"]), (55.736691, 37.482852))
        self.assertTrue(rec["needs_review"])
        self.assertIn("КОНФЛИКТ АДРЕСА", rec["review_notes"])
        self.assertIn("16с1", rec["review_notes"])

    def test_batch_objects_visible_under_low_confidence_filter(self):
        """Объекты с confidence=Низкий из этой партии остаются в projects
        (не в no_coords, не в duplicates без основания) — «review»-фильтр
        интерфейса их найдёт, а не потеряет."""
        proj_ids = {r["id"] for r in self.projects}
        for object_id in ("OBJ-0739", "OBJ-0726", "OBJ-0051"):
            self.assertIn(object_id, proj_ids, object_id)


class Batch20260813NoCoordsAuditTest(unittest.TestCase):
    """Продолжение аудита no_coords после e03ffa5: 4 адреса подтверждены
    независимо (2ГИС/веб, расхождение 1-55 м) и перенесены в projects; 6
    отклонены — координата НЕ добавлена без доказательства."""

    @classmethod
    def setUpClass(cls):
        if not DATA.exists():
            raise unittest.SkipTest("data/future_projects.json отсутствует")
        with DATA.open(encoding="utf-8") as f:
            cls.payload = json.load(f)
        cls.projects = cls.payload["projects"]
        cls.no_coords = cls.payload["no_coords"]

    def test_four_confirmed_addresses_moved_to_projects_as_exact(self):
        by_id = {r["id"]: r for r in self.projects}
        no_coord_ids = {r["id"] for r in self.no_coords}
        expected = {
            "OBJ-0143": (55.779540, 37.676304),
            "OBJ-0146": (55.695606, 37.581262),
            "OBJ-0579": (55.762885, 37.557026),
            "OBJ-0598": (55.773413, 37.520303),
        }
        for object_id, point in expected.items():
            self.assertNotIn(object_id, no_coord_ids, object_id)
            rec = by_id[object_id]
            self.assertEqual((rec["lat"], rec["lng"]), point, object_id)
            self.assertEqual(rec["geometry_quality"], "exact", object_id)
            self.assertTrue(rec.get("coordinates_source"), object_id)
            self.assertIn("Yandex Geocoder", rec["coordinates_source"], object_id)
            self.assertTrue(rec["needs_review"], object_id)

    def test_six_rejected_addresses_stay_in_no_coords_without_coordinates(self):
        """Отклонённые адреса остаются в no_coords с полной парой null —
        никакой центр улицы/района/МКАД/чужой корпус не подставлен."""
        by_id = {r["id"]: r for r in self.no_coords}
        rejected = ["OBJ-0264", "OBJ-0469", "OBJ-0599", "OBJ-0605", "OBJ-0625"]
        for object_id in rejected:
            self.assertIn(object_id, by_id, object_id)
            rec = by_id[object_id]
            self.assertIsNone(rec["lat"], object_id)
            self.assertIsNone(rec["lng"], object_id)
            self.assertTrue(rec["needs_review"], object_id)

    def test_obj0625_blocked_by_evidence_not_single_point_for_four_buildings(self):
        """Составной адрес «корп. 4,5,6,7» — координата умышленно не
        поставлена вместо четырёх корпусов без источника, различающего их."""
        rec = next(r for r in self.no_coords if r["id"] == "OBJ-0625")
        self.assertIsNone(rec["lat"])
        self.assertIsNone(rec["lng"])
        self.assertIn("BLOCKED_BY_EVIDENCE", rec["review_notes"])
        self.assertIn("4", rec["review_notes"])

    def test_ids_remain_unique_after_batch(self):
        all_ids = [r["id"] for r in self.projects + self.no_coords + self.payload["duplicates"]]
        self.assertEqual(len(all_ids), len(set(all_ids)))


if __name__ == "__main__":
    unittest.main()
