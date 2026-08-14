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
                # партия 2026-08-14: внутрибазовые дубли (совпадение
                # девелопера и GBA с точностью до 3%, та же запись под
                # другим именем из другого исходного листа)
                "OBJ-0020", "OBJ-0031", "OBJ-0032", "OBJ-0040", "OBJ-0065",
                "OBJ-0067", "OBJ-0069", "OBJ-0107", "OBJ-0138", "OBJ-0179",
                "OBJ-0187", "OBJ-0226", "OBJ-0235", "OBJ-0291", "OBJ-0314",
                "OBJ-0340", "OBJ-0347", "OBJ-0350", "OBJ-0371", "OBJ-0372",
                "OBJ-0377", "OBJ-0379", "OBJ-0384", "OBJ-0390", "OBJ-0478",
                "OBJ-0485", "OBJ-0520", "OBJ-0535", "OBJ-0548", "OBJ-0572",
                "OBJ-0573", "OBJ-0577", "OBJ-0604", "OBJ-0614", "OBJ-0615",
                "OBJ-0616", "OBJ-0756",
                # партия 2026-08-14, вторая волна (слабый сигнал: GBA
                # совпадает, но развёрнутое имя девелопера отличается от
                # сокращения/уверенности той же компании — проверено вручную)
                "OBJ-0611", "OBJ-0619", "OBJ-0617", "OBJ-0498", "OBJ-0511",
                "OBJ-0139", "OBJ-0363", "OBJ-0357", "OBJ-0578", "OBJ-0392",
                "OBJ-0391", "OBJ-0665", "OBJ-0283",
                # партия 2026-08-14, живой повторный геокодинг ~700 адресов
                "OBJ-0689",
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

        # OBJ-0665 объединён 2026-08-14 в OBJ-0278 «Вперед» (тот же адрес,
        # GBA расходится на 0.001%) — координата сохранена на канонической записи.
        dup_by_id = {r["id"]: r for r in self.duplicates}
        self.assertEqual(dup_by_id["OBJ-0665"]["duplicate_of"], "OBJ-0278")
        canonical = by_id["OBJ-0278"]
        self.assertEqual((canonical["lat"], canonical["lng"]), (55.7844, 37.58464))

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
            "OBJ-0501", "OBJ-0567", "OBJ-0587",
            "OBJ-0637", "OBJ-0645", "OBJ-0652", "OBJ-0672", "OBJ-0693",
        ]
        # FRAME WORKPLACE (OBJ-0548) и "17-й проезд Марьиной Рощи, 9"
        # (OBJ-0485) — те же здания, что OBJ-0103/OBJ-0193 — объединены
        # через duplicate_of (см. Batch20260814InternalDuplicateMergeTest),
        # больше не отдельные активные записи, делить с ними точку не с кем.
        points = []
        for object_id in exact_ids:
            self.assertIn(object_id, by_id, object_id)
            rec = by_id[object_id]
            self.assertEqual(rec["geometry_quality"], "exact", object_id)
            points.append((round(rec["lat"], 6), round(rec["lng"], 6)))
        dupes = {p for p in points if points.count(p) > 1}
        self.assertEqual(dupes, set(), f"неожиданные общие точки: {dupes}")

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

    def test_sbercity_prokshino_stay_unresolved(self):
        """СберСити (kind=district у всех кандидатов) и Прокшино БК (адрес
        без улицы/дома, ни один из 3 корпусов не найден живым запросом по
        отдельности 2026-08-14) не прошли строгие критерии — координаты не
        присвоены/не изменены по догадке. СберСити уже был на centroid с
        прошлой сессии (data/future_projects.json), поэтому остаётся в
        projects без изменений; Прокшино БК никогда не имел координаты и
        остаётся в no_coords. Ривер Парк проверен отдельно (см.
        Batch20260814FullGeoCoverageAuditTest) — в отличие от Прокшино, для
        него нашлась общая точка дома на ул. Речников."""
        no_coords_ids = {r["id"] for r in self.no_coords}
        must_stay_no_coords = ["OBJ-0691", "OBJ-0694", "OBJ-0710"]
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
        rejected = ["OBJ-0469", "OBJ-0599", "OBJ-0605", "OBJ-0625"]
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


class Batch20260813RegistryAuditTest(unittest.TestCase):
    """Аудит после 840973b: структурная целостность future_projects.json
    и отдельная проверка проектов, где похожее название/близкий адрес
    мог бы спровоцировать ошибочное слияние (Lakes/Lakes 2, Link/Link
    NEO-RUNE), но не должен, так как это разные физические объекты."""

    @classmethod
    def setUpClass(cls):
        if not DATA.exists():
            raise unittest.SkipTest("data/future_projects.json отсутствует")
        with DATA.open(encoding="utf-8") as f:
            cls.payload = json.load(f)
        cls.projects = cls.payload["projects"]
        cls.no_coords = cls.payload["no_coords"]
        cls.duplicates = cls.payload["duplicates"]

    def test_total_equals_projects_plus_no_coords(self):
        self.assertEqual(
            self.payload["total"], len(self.projects) + len(self.no_coords)
        )

    def test_duplicate_count_matches_duplicates_length(self):
        self.assertEqual(self.payload["duplicate_count"], len(self.duplicates))

    def test_with_coords_and_without_coords_counters_match(self):
        self.assertEqual(self.payload["with_coords"], len(self.projects))
        self.assertEqual(self.payload["without_coords"], len(self.no_coords))

    def test_ids_globally_unique_across_all_three_lists(self):
        all_ids = [r["id"] for r in self.projects + self.no_coords + self.duplicates]
        self.assertEqual(len(all_ids), len(set(all_ids)))

    def test_no_coords_records_have_no_lat_lng(self):
        for r in self.no_coords:
            self.assertIsNone(r.get("lat"), r["id"])
            self.assertIsNone(r.get("lng"), r["id"])

    def test_confirmed_duplicates_absent_from_active_projects_layer(self):
        proj_ids = {r["id"] for r in self.projects}
        dup_ids = {r["id"] for r in self.duplicates}
        self.assertEqual(proj_ids & dup_ids, set())

    def test_project_coordinates_within_moscow_region_bounds(self):
        for r in self.projects:
            lat, lng = r["lat"], r["lng"]
            self.assertTrue(55.0 <= lat <= 56.1, f"{r['id']}: lat {lat} outside Moscow region")
            self.assertTrue(36.5 <= lng <= 38.5, f"{r['id']}: lng {lng} outside Moscow region")

    def test_lakes_and_lakes2_remain_separate_projects(self):
        """Lakes (OBJ-0054) и Lakes 2 (OBJ-0202) — разные корпуса на
        ул. Озёрная, не сливаются в один объект по совпадению префикса
        названия."""
        proj_by_id = {r["id"]: r for r in self.projects}
        lakes = proj_by_id["OBJ-0054"]
        lakes2 = proj_by_id["OBJ-0202"]
        self.assertIsNone(lakes.get("duplicate_of"))
        self.assertIsNone(lakes2.get("duplicate_of"))
        self.assertNotEqual((lakes["lat"], lakes["lng"]), (lakes2["lat"], lakes2["lng"]))

    def test_link_and_link_neo_rune_remain_separate_projects(self):
        """Link (OBJ-0150) и Link (Башня NEO и Башня RUNE) (OBJ-0663) —
        разные башни одного девелопера MR Office, не сливаются по
        совпадению общего названия «Link»."""
        proj_by_id = {r["id"]: r for r in self.projects}
        link = proj_by_id["OBJ-0150"]
        link_neo_rune = proj_by_id["OBJ-0663"]
        self.assertIsNone(link.get("duplicate_of"))
        self.assertIsNone(link_neo_rune.get("duplicate_of"))
        self.assertNotEqual(
            (link["lat"], link["lng"]), (link_neo_rune["lat"], link_neo_rune["lng"])
        )


class Batch20260814FullGeoCoverageAuditTest(unittest.TestCase):
    """Задача «чтобы зданий без геопривязки на карте не осталось»: полный
    повторный проход по всем 58 no_coords после feb1792, затем ещё один
    проход поиском по названию внутри самой базы (7caac88). Всего закрыто
    33 из 58 честными координатами (12 — баг сравнения адресов в
    предыдущем аудите отклонял exact-совпадения только из-за порядка слов/
    аббревиатур/префикса «вл.»; 3 — уточнены веб-поиском и подтверждены
    независимо; 3 — живой геокодинг по отдельному корпусу ЮПорт; 5 — Ривер
    Парк, общая точка дома на ул. Речников с пояснением; 3 — адрес найден
    в вебе; 1 — восстановлен номер дома из собственных источников записи;
    6 — та же запись под другим именем уже была в базе с координатой:
    МФК Электролитный, БЦ на Гончарной, Технопарк ЗИЛ А, 3 корпуса ЮПорта
    через project-уровневый centroid). 25 остаётся без координат —
    доказательств недостаточно, включая случаи с отброшенными кандидатами
    из-за резкого расхождения GBA (Крост/Самолет АДЦ Коммунарка)."""

    @classmethod
    def setUpClass(cls):
        if not DATA.exists():
            raise unittest.SkipTest("data/future_projects.json отсутствует")
        with DATA.open(encoding="utf-8") as f:
            cls.payload = json.load(f)
        cls.projects = cls.payload["projects"]
        cls.no_coords = cls.payload["no_coords"]

    def test_normalization_bug_fixed_exact_matches_moved_to_projects(self):
        """12 записей были ошибочно отклонены багом сравнения строк адреса
        (порядок слов, аббревиатуры «пр-кт»/«б-р»/«пр-д», префикс «вл.»/
        «владение» перед номером дома) — Yandex Geocoder на самом деле уже
        возвращал kind=house precision=exact для запрошенного адреса."""
        by_id = {r["id"]: r for r in self.projects}
        no_coord_ids = {r["id"] for r in self.no_coords}
        expected = {
            "OBJ-0627": (55.748599, 37.497701),
            "OBJ-0628": (55.629028, 37.640120),
            "OBJ-0629": (55.692495, 37.533095),
            "OBJ-0639": (55.792108, 37.540757),
            "OBJ-0670": (55.756639, 37.528109),
            "OBJ-0673": (55.698391, 37.658248),
            "OBJ-0681": (55.800494, 37.581424),
            "OBJ-0712": (55.701298, 37.633976),
            "OBJ-0747": (55.704007, 37.580849),
            "OBJ-0768": (55.787427, 37.545896),
            "OBJ-0769": (55.779646, 37.571246),
            "OBJ-0728": (55.691917, 37.532232),
        }
        for object_id, point in expected.items():
            self.assertNotIn(object_id, no_coord_ids, object_id)
            rec = by_id[object_id]
            self.assertEqual((rec["lat"], rec["lng"]), point, object_id)
            self.assertEqual(rec["geometry_quality"], "exact", object_id)

    def test_web_verified_candidates_moved_to_projects(self):
        """3 записи (Башня в Сити, ЗИЛАРТ GRAND, БЦ на Шмитовском 32)
        уточнены независимым веб-поиском (сайт девелопера/ЦИАН/справочники
        БЦ), затем сверены с Yandex Geocoder."""
        by_id = {r["id"]: r for r in self.projects}
        no_coord_ids = {r["id"] for r in self.no_coords}
        for object_id in ("OBJ-0635", "OBJ-0638", "OBJ-0640"):
            self.assertNotIn(object_id, no_coord_ids, object_id)
            self.assertIn(object_id, by_id, object_id)
        self.assertEqual(by_id["OBJ-0638"]["geometry_quality"], "approximate")
        self.assertEqual(by_id["OBJ-0635"]["geometry_quality"], "exact")
        self.assertEqual(by_id["OBJ-0640"]["geometry_quality"], "exact")

    def test_yuport_per_corpus_geocoding_partial_success(self):
        """ЮПорт (пр-кт Андропова, 11): раздельный запрос по каждому
        корпусу вместо одного общего — 3 из 6 корпусов (1, 2, 7) имеют
        собственную запись в базе геокодера и приняты как exact; ещё 3
        (4, 5, 6) не имеют собственной записи, но в этой же базе уже есть
        project-уровневая запись «Юпорт» (OBJ-0365) с координатой в том же
        кластере — присвоена им как centroid, а не подставлена наугад."""
        by_id = {r["id"]: r for r in self.projects}
        no_coord_ids = {r["id"] for r in self.no_coords}
        for object_id in ("OBJ-0770", "OBJ-0772", "OBJ-0775"):
            self.assertNotIn(object_id, no_coord_ids, object_id)
            self.assertEqual(by_id[object_id]["geometry_quality"], "exact", object_id)
        centroid = (55.690336, 37.678141)
        for object_id in ("OBJ-0771", "OBJ-0774", "OBJ-0776"):
            self.assertNotIn(object_id, no_coord_ids, object_id)
            rec = by_id[object_id]
            self.assertEqual((rec["lat"], rec["lng"]), centroid, object_id)
            self.assertEqual(rec["geometry_quality"], "centroid", object_id)

    def test_cross_database_name_match_recovers_coordinates(self):
        """Поиск по названию внутри самой базы (та же запись под другим
        именем/из другого листа уже с координатой) нашёл 3 честных
        exact/approximate совпадения без единого нового запроса к геокодеру:
        МФК Электролитный (= OBJ-0139/OBJ-0363, GBA расходится на 0.2%),
        БЦ на Гончарной 20/1с2 (= OBJ-0283, GBA расходится на 0.01%),
        Технопарк ЗИЛ А (= OBJ-0057, тот же девелопер, соседний корпус —
        approximate, не exact)."""
        by_id = {r["id"]: r for r in self.projects}
        no_coord_ids = {r["id"] for r in self.no_coords}

        self.assertNotIn("OBJ-0725", no_coord_ids)
        rec = by_id["OBJ-0725"]
        self.assertEqual((rec["lat"], rec["lng"]), (55.673641, 37.617204))
        self.assertEqual(rec["geometry_quality"], "exact")

        self.assertNotIn("OBJ-0777", no_coord_ids)
        rec = by_id["OBJ-0777"]
        self.assertEqual((rec["lat"], rec["lng"]), (55.744075, 37.647899))
        self.assertEqual(rec["geometry_quality"], "exact")

        self.assertNotIn("OBJ-0657", no_coord_ids)
        rec = by_id["OBJ-0657"]
        self.assertEqual((rec["lat"], rec["lng"]), (55.702688, 37.634389))
        self.assertEqual(rec["geometry_quality"], "approximate")

    def test_cross_database_search_does_not_force_mismatched_gba_candidates(self):
        """Кандидаты с тем же именем-топонимом, но резко отличающейся GBA
        (Крост АДЦ Коммунарка 190000 vs БЦ Крост 24000 — в 8 раз; Самолет
        АДЦ Коммунарка 299000 vs БЦ Самолет 25400 — в 11 раз) — НЕ приняты
        как совпадение, остаются в no_coords: разная GBA означает разные
        физические объекты одного девелопера, не один и тот же."""
        no_coord_ids = {r["id"] for r in self.no_coords}
        for object_id in ("OBJ-0255", "OBJ-0271", "OBJ-0246"):
            self.assertIn(object_id, no_coord_ids, object_id)

    def test_river_park_kolomenskoye_shares_explained_centroid(self):
        """Ривер Парк Коломенское: 5 секций/корпусов (зу 7/3, 7/7, 7/8) не
        различаются геокодером — им присвоена ОБЩАЯ точка дома 7 на
        ул. Речников с explicit geometry_quality=centroid (не exact),
        по аналогии с ранее принятым решением для СберСити."""
        by_id = {r["id"]: r for r in self.projects}
        no_coord_ids = {r["id"] for r in self.no_coords}
        river_park_ids = ["OBJ-0713", "OBJ-0714", "OBJ-0723", "OBJ-0724", "OBJ-0753"]
        centroid = (55.681712, 37.693848)
        for object_id in river_park_ids:
            self.assertNotIn(object_id, no_coord_ids, object_id)
            rec = by_id[object_id]
            self.assertEqual((rec["lat"], rec["lng"]), centroid, object_id)
            self.assertEqual(rec["geometry_quality"], "centroid", object_id)

    def test_addresses_found_via_websearch_then_geocoded(self):
        """3 записи вообще не имели адреса в исходных данных — реальный
        адрес найден веб-поиском (официальные источники: mos.ru, сайт
        застройщика/БЦ) и затем геокодирован."""
        by_id = {r["id"]: r for r in self.projects}
        no_coord_ids = {r["id"] for r in self.no_coords}
        expected = {
            "OBJ-0397": (55.691318, 37.476519),
            "OBJ-0703": (55.729777, 37.442446),
            "OBJ-0296": (55.569169, 37.479717),
        }
        for object_id, point in expected.items():
            self.assertNotIn(object_id, no_coord_ids, object_id)
            rec = by_id[object_id]
            self.assertEqual((rec["lat"], rec["lng"]), point, object_id)
            self.assertEqual(rec["geometry_quality"], "exact", object_id)

    def test_obj0264_house_number_recovered_from_own_sources(self):
        """OBJ-0264 (БЦ на Текстильщиков): в исходном адресе не было номера
        дома, но в поле sources этой же записи уже было 4 источника
        (включая URL CIAN), однозначно указывающих дом 8 — номер
        восстановлен из собственных данных записи, не угадан."""
        by_id = {r["id"]: r for r in self.projects}
        no_coord_ids = {r["id"] for r in self.no_coords}
        self.assertNotIn("OBJ-0264", no_coord_ids)
        rec = by_id["OBJ-0264"]
        self.assertEqual((rec["lat"], rec["lng"]), (55.704052, 37.740498))
        self.assertEqual(rec["geometry_quality"], "exact")

    def test_remaining_no_coords_are_evidence_blocked_not_arbitrary(self):
        """31 запись остаётся без координат после полного аудита — у каждой
        нет ни адреса, ни exact/near-совпадения в границах Москвы. Ни одна
        не содержит lat/lng — сокращение no_coords не сделано ценой точности."""
        by_id = {r["id"]: r for r in self.no_coords}
        self.assertEqual(len(self.no_coords), 25)
        for r in self.no_coords:
            self.assertIsNone(r.get("lat"), r["id"])
            self.assertIsNone(r.get("lng"), r["id"])

    def test_yandex_api_key_not_leaked_into_data_files(self):
        """API-ключ использовался только в памяти процесса геокодинга —
        убеждаемся, что он не осел ни в overrides, ни в future_projects.json."""
        text = json.dumps(self.payload, ensure_ascii=False)
        self.assertNotIn("bec42ad9", text)
        ovr_path = REPO_ROOT / "data" / "future_projects_verification_overrides.json"
        ovr_text = ovr_path.read_text(encoding="utf-8")
        self.assertNotIn("bec42ad9", ovr_text)


class Batch20260814InternalDuplicateMergeTest(unittest.TestCase):
    """По запросу «проверяй всё»: поиск по всей базе projects (731 записей)
    выявил 31 группу (68 записей), где один физический объект был записан
    несколько раз под разными именами из разных исходных листов
    (будущие/будущие (old)/сданы/remain/Анонсы) — с точным совпадением
    девелопера и GBA (расхождение <=3%), но БЕЗ duplicate_of. Объединено
    через duplicate_of; исходные записи не удалены, источники/алиасы
    перенесены на канонический объект."""

    @classmethod
    def setUpClass(cls):
        if not DATA.exists():
            raise unittest.SkipTest("data/future_projects.json отсутствует")
        with DATA.open(encoding="utf-8") as f:
            cls.payload = json.load(f)
        cls.projects = cls.payload["projects"]
        cls.duplicates = cls.payload["duplicates"]

    def test_lucky_corpus1_merged_into_lucky_bldg2(self):
        """Lucky (корпус 1) и Lucky, bldg 2 — один и тот же дом (2-я
        Звенигородская, 28; VESPER; GBA 4470 vs 4469.6) — не два разных
        корпуса одного комплекса, а одна и та же запись дважды."""
        dup_by_id = {r["id"]: r for r in self.duplicates}
        proj_by_id = {r["id"]: r for r in self.projects}
        self.assertEqual(dup_by_id["OBJ-0020"]["duplicate_of"], "OBJ-0579")
        canonical = proj_by_id["OBJ-0579"]
        self.assertIn("Lucky (корпус 1)", canonical.get("aliases") or [])

    def test_skolkovo_park_four_phase_rows_merged_to_one(self):
        """Сколково парк, фазы I/II/III + корп. 2/4/6 + корп. 3/5 — все
        пять строк несут идентичный дублированный GBA (70666.67, целый
        проект поделённый на фазы с одинаковым числом) — артефакт исходной
        выгрузки, не пять разных зданий. Объединены в OBJ-0026."""
        dup_by_id = {r["id"]: r for r in self.duplicates}
        proj_by_id = {r["id"]: r for r in self.projects}
        for object_id in ("OBJ-0067", "OBJ-0069", "OBJ-0614", "OBJ-0615"):
            self.assertEqual(dup_by_id[object_id]["duplicate_of"], "OBJ-0026", object_id)
        self.assertIn("OBJ-0026", proj_by_id)

    def test_merged_records_kept_not_deleted_with_sources_preserved(self):
        """Ни одна объединённая запись не удалена — все 37 присутствуют в
        duplicates с непустым duplicate_of, указывающим на запись в
        активном слое projects."""
        proj_ids = {r["id"] for r in self.projects}
        merged_ids = {
            "OBJ-0020", "OBJ-0031", "OBJ-0032", "OBJ-0040", "OBJ-0065",
            "OBJ-0067", "OBJ-0069", "OBJ-0107", "OBJ-0138", "OBJ-0179",
            "OBJ-0187", "OBJ-0226", "OBJ-0235", "OBJ-0291", "OBJ-0314",
            "OBJ-0340", "OBJ-0347", "OBJ-0350", "OBJ-0371", "OBJ-0372",
            "OBJ-0377", "OBJ-0379", "OBJ-0384", "OBJ-0390", "OBJ-0478",
            "OBJ-0485", "OBJ-0520", "OBJ-0535", "OBJ-0548", "OBJ-0572",
            "OBJ-0573", "OBJ-0577", "OBJ-0604", "OBJ-0614", "OBJ-0615",
            "OBJ-0616", "OBJ-0756",
        }
        dup_by_id = {r["id"]: r for r in self.duplicates}
        self.assertEqual(merged_ids, merged_ids & dup_by_id.keys())
        for object_id in merged_ids:
            rec = dup_by_id[object_id]
            self.assertIn(rec["duplicate_of"], proj_ids, object_id)

    def test_weak_signal_pairs_not_auto_merged(self):
        """Пары, где совпадает только GBA, а девелопер различается/не
        указан (14 пар, включая Aurus/Страна.Сити), НЕ объединены
        автоматически — разбираются вручную по одной, не по формальному
        совпадению площади."""
        proj_ids = {r["id"] for r in self.projects}
        for object_id in ("OBJ-0345", "OBJ-0374"):
            self.assertIn(object_id, proj_ids, object_id)
            rec = next(r for r in self.projects if r["id"] == object_id)
            self.assertIsNone(rec.get("duplicate_of"), object_id)

    def test_weak_signal_pairs_manually_confirmed_and_merged(self):
        """Вторая волна: 12 пар/групп, где совпадал только GBA, а строка
        девелопера отличалась — проверены вручную (аббревиатура/неуверенная
        пометка «?»/транслитерация одной и той же компании, не разные
        компании) и объединены через duplicate_of."""
        dup_by_id = {r["id"]: r for r in self.duplicates}
        proj_ids = {r["id"] for r in self.projects}
        expected = {
            "OBJ-0611": "OBJ-0044", "OBJ-0619": "OBJ-0056", "OBJ-0617": "OBJ-0082",
            "OBJ-0498": "OBJ-0095", "OBJ-0511": "OBJ-0132", "OBJ-0139": "OBJ-0725",
            "OBJ-0363": "OBJ-0725", "OBJ-0357": "OBJ-0155", "OBJ-0578": "OBJ-0017",
            "OBJ-0392": "OBJ-0237", "OBJ-0391": "OBJ-0267", "OBJ-0283": "OBJ-0777",
        }
        for dup_id, canonical_id in expected.items():
            self.assertEqual(dup_by_id[dup_id]["duplicate_of"], canonical_id, dup_id)
            self.assertIn(canonical_id, proj_ids, canonical_id)

    def test_genuinely_different_developer_pairs_stay_unmerged(self):
        """October Group vs MR Group (OBJ-0266/OBJ-0393) — реальные разные
        компании, не варианты написания одной; совпадение адреса и GBA
        одно, без независимого источника, недостаточно — НЕ объединено,
        только задокументировано в review_notes."""
        proj_ids = {r["id"] for r in self.projects}
        for object_id in ("OBJ-0266", "OBJ-0393"):
            self.assertIn(object_id, proj_ids, object_id)
            rec = next(r for r in self.projects if r["id"] == object_id)
            self.assertIsNone(rec.get("duplicate_of"), object_id)
            self.assertIn("НЕ объединено", rec.get("review_notes") or "", object_id)


class Batch20260814LiveRegeocodeAuditTest(unittest.TestCase):
    """Продолжение аудита «проверяй адреса»: живой повторный геокодинг
    ~700 адресов projects против уже проставленных точек нашёл 6 записей,
    унаследованных из исходного xlsx с координатой за много км от
    реального адреса — все подтверждены независимо (2ГИС/ЦИАН/официальные
    сайты/госреестр), не только геокодером."""

    @classmethod
    def setUpClass(cls):
        if not DATA.exists():
            raise unittest.SkipTest("data/future_projects.json отсутствует")
        with DATA.open(encoding="utf-8") as f:
            cls.payload = json.load(f)
        cls.projects = cls.payload["projects"]
        cls.duplicates = cls.payload["duplicates"]

    def test_fili_and_nice_tower_and_meshchersky_coordinates_corrected(self):
        by_id = {r["id"]: r for r in self.projects}
        expected = {
            "OBJ-0647": (55.741059, 37.509505),   # Фили — та же уехавшая точка, что OBJ-0729
            "OBJ-0704": (55.728271, 37.701637),   # N'ICE TOWER — была на 21+ км севернее
            "OBJ-0701": (55.663212, 37.428073),   # БЦ Мещерский — была на ~16.6 км юго-западнее
            "OBJ-0035": (55.780608, 37.574309),   # ГБУ Мосгоргеотрест — была на ~11.9 км
            "OBJ-0154": (55.720545, 37.67528),    # MYPRIORITY Дубровка — была на ~8.8 км севернее
        }
        for object_id, point in expected.items():
            rec = by_id[object_id]
            self.assertEqual((rec["lat"], rec["lng"]), point, object_id)
            self.assertEqual(rec["geometry_quality"], "exact", object_id)
            self.assertTrue(rec.get("coordinates_source"), object_id)

    def test_porta_obj0689_merged_into_confirmed_obj0044(self):
        """PORTA (OBJ-0689) и PORTA Workplace (OBJ-0044) — один и тот же
        БЦ у метро Фили; OBJ-0689 нёс неподтверждённую координату
        (~30 км от Филёвского парка) — объединён, не координата слита."""
        dup_by_id = {r["id"]: r for r in self.duplicates}
        proj_by_id = {r["id"]: r for r in self.projects}
        self.assertEqual(dup_by_id["OBJ-0689"]["duplicate_of"], "OBJ-0044")
        canonical = proj_by_id["OBJ-0044"]
        self.assertEqual((canonical["lat"], canonical["lng"]), (55.751624, 37.514733))
        self.assertIn("PORTA", canonical.get("aliases") or [])


if __name__ == "__main__":
    unittest.main()
