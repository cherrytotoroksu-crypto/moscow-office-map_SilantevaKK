"""Regression test for the generated data/all_projects_layer.json registry.

Distinct from tests/test_validate_all_projects_layer.py, which only checks
the small hand-written sample fixture. This test checks the REAL registry
produced by scripts/build_all_projects_layer.py from classifier.html: right
record count, the Бадаевский shared-project-id rule, and that none of the
12 known display-name collisions got silently merged into one project.
"""
import json
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))
from validate_all_projects_layer import validate

REGISTRY_PATH = REPO_ROOT / "data" / "all_projects_layer.json"

# Same 12 names flagged by scripts/validate_classifier.py as sharing a
# display name across rows with different lat/lng/address (QUARANTINE_2026-07-29.md,
# "12 name-collision warnings"). Rule: not merged without an explicit ID scheme.
KNOWN_COLLISION_NAMES = [
    "Apollax Space (Новосущевский)",
    "Signature Столешников (Signature Столешников, 11)",
    "Smart Yard (на Волгоградском) (РТС Волгоградский)",
    "Регус (Пр. Мира, 40) (Проспект Мира, 40)",
    "Apollax Space (Технопарк)",
    "Apollax Space (Останкино)",
    "Apollax Space (Новослободская)",
    "Газетный (Газетный 17)",
    "Ходынка (Авиаконструктора Микояна)",
    "Apollax Space (Кузнецкий Мост)",
    "СODE Delegat (1-й Щемиловский 16с2)",
    "Manufaqtury Поклонка (Poklonka Place)",
]


@unittest.skipUnless(REGISTRY_PATH.exists(), "data/all_projects_layer.json not generated yet")
class AllProjectsLayerRegistryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.records = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))

    def test_registry_passes_validator(self):
        self.assertEqual(validate(self.records), [])

    def test_record_count_matches_active_raw_data(self):
        # 279 RAW_DATA rows - 2 out_of_scope (Новосибирск/Астана) = 277.
        # Считаем только classifier-производные записи: внешние источники
        # (remain_datalens и т.п.) добавляются ПОВЕРХ, а не через
        # build_all_projects_layer.py, и не должны сдвигать этот счётчик.
        classifier_records = [r for r in self.records if r["source"] == "classifier.html"]
        self.assertEqual(len(classifier_records), 277)

    def test_external_only_records_are_additive_not_mixed_into_classifier_base(self):
        external_records = [r for r in self.records if r.get("external_only")]
        for r in external_records:
            self.assertNotEqual(r["source"], "classifier.html")
            self.assertEqual(r["quarter_offer_refs"], [],
                              f"{r['canonical_project_id']}: external record must not carry quarterly offer refs")
            self.assertFalse(r["quarter_offer_exists"])
            self.assertEqual(r["market_channel"], [],
                              f"{r['canonical_project_id']}: external record must not be mixed into sale/rent/coworking channels")

    def test_remain_only_records_are_valid_and_not_duplicates_of_local_projects(self):
        remain_records = [r for r in self.records if r.get("source") == "remain_datalens"]
        self.assertGreater(len(remain_records), 0, "expected at least the confirmed only_remain candidates")
        self.assertEqual(validate(remain_records), [])

        # не дубль по имени: ни один remain-only canonical_name не совпадает
        # (без учёта регистра) с classifier-производной записью.
        classifier_names = {
            r["canonical_name"].strip().lower()
            for r in self.records if r["source"] == "classifier.html"
        }
        for r in remain_records:
            self.assertNotIn(r["canonical_name"].strip().lower(), classifier_names,
                              f"{r['canonical_name']} looks like a duplicate of an existing classifier record")

        # уникальные canonical_project_id, не пересекаются с proj-* пространством
        ids = [r["canonical_project_id"] for r in remain_records]
        self.assertEqual(len(ids), len(set(ids)), "duplicate canonical_project_id among remain-only records")
        for cid in ids:
            self.assertFalse(cid.startswith("proj-"), f"{cid} collides with the classifier proj-* id space")

    def test_badaevsky_shares_project_id_but_not_building_id(self):
        west = next(r for r in self.records if r["canonical_building_id"] == "badaevsky-west")
        east = next(r for r in self.records if r["canonical_building_id"] == "badaevsky-east")
        self.assertEqual(west["canonical_project_id"], "badaevsky")
        self.assertEqual(east["canonical_project_id"], "badaevsky")
        self.assertNotEqual(west["canonical_building_id"], east["canonical_building_id"])

    def test_shared_canonical_project_id_always_has_distinct_building_ids(self):
        """Общее правило (аудит после 840973b): canonical_project_id может
        повторяться только когда это разные здания/корпуса одного проекта
        — и тогда canonical_building_id обязан различаться. Единственная
        существующая пара — Бадаевский (West/East), проверена отдельно
        выше; этот тест ловит любую БУДУЩУЮ регрессию по всему реестру."""
        from collections import defaultdict

        by_project = defaultdict(list)
        for r in self.records:
            by_project[r["canonical_project_id"]].append(r)

        for project_id, rows in by_project.items():
            if len(rows) < 2:
                continue
            building_ids = [r.get("canonical_building_id") for r in rows]
            self.assertEqual(
                len(building_ids), len(set(building_ids)),
                f"canonical_project_id={project_id!r}: {len(rows)} rows share it but "
                f"canonical_building_id is not all-distinct ({building_ids}) — either a "
                f"duplicate or an erroneous merge"
            )

    def test_known_name_collisions_are_not_silently_merged(self):
        for name in KNOWN_COLLISION_NAMES:
            matches = [r for r in self.records if r["canonical_name"] == name]
            self.assertGreaterEqual(
                len(matches), 2,
                f"expected >=2 rows for known collision {name!r}, found {len(matches)}"
            )
            ids = {r["canonical_project_id"] for r in matches}
            self.assertEqual(
                len(ids), len(matches),
                f"{name!r}: rows were merged into a shared canonical_project_id ({ids}) — not allowed without an explicit rule"
            )

    def test_code_delegat_address_matches_its_own_shchemilovsky_name(self):
        """Аудит 2026-08-14: одна из двух строк «СODE Delegat (1-й
        Щемиловский 16с2)» в classifier.html несла адрес/координату СODE
        Novo (Долгоруковская 21) — баг копирования, подтверждённый внешними
        источниками (kf.expert, CRE.ru: CODE Delegat всегда на Щемиловском).
        Обе строки этого имени обязаны указывать на Щемиловский, не на
        Долгоруковскую."""
        matches = [r for r in self.records if r["canonical_name"] == "СODE Delegat (1-й Щемиловский 16с2)"]
        self.assertGreaterEqual(len(matches), 2)
        for r in matches:
            self.assertEqual(r["address"], "1-й Щемиловский 16с2", r["canonical_project_id"])
            self.assertEqual((r["latitude"], r["longitude"]), (55.779089, 37.607197), r["canonical_project_id"])

    def test_code_novo_manual_patch_survives_regenerate(self):
        """canonical_building_id и расширенные aliases для СODE Novo
        (proj-149) раньше применялись разовым патчом JSON и терялись при
        каждом build_all_projects_layer.py — теперь заданы в самом скрипте
        (EXTRA_BUILDING_ID/EXTRA_ALIASES) и должны переживать regenerate."""
        novo = next(r for r in self.records if r["canonical_project_id"] == "proj-149")
        self.assertEqual(novo["canonical_building_id"], "code-novo-dolgorukovskaya-21")
        for alias in ("CODE Novo", "Долгоруковская 21", "СODE Novo"):
            self.assertIn(alias, novo["aliases"], alias)

    def test_live_regeocode_batch_20260818_coordinates_corrected(self):
        """Живой повторный геокодинг 256 адресов all_projects_layer.json
        нашёл 10 записей с координатой за много км от собственного адреса
        (унаследовано из classifier.html) — все подтверждены независимо
        (2ГИС/ЦИАН/официальные сайты БЦ), не только геокодером."""
        by_id = {r["canonical_project_id"]: r for r in self.records}
        expected = {
            "proj-15": (55.728023, 37.645375),   # Рабочая Станция KW Black&White — Кожевническая 14
            "proj-235": (55.728023, 37.645375),  # KW Павелецкая — тот же адрес
            "proj-48": (55.730426, 37.634793),   # Flexity Павелецкая Плаза А
            "proj-49": (55.730426, 37.634793),
            "proj-255": (55.730426, 37.634793),
            "proj-256": (55.730426, 37.634793),
            "proj-222": (55.691963, 37.527965),  # Регус Капитолий Вернадского — тот же дом, что БЦ Капитолий
            "proj-119": (55.757131, 37.617114),  # Meeting point (Гостиница Москва) — Охотный ряд
            "proj-166": (55.788353, 37.567931),  # SOK Рыбаков Тауэр — Ленинградский пр-т у Динамо
            "proj-211": (55.696007, 37.625513),  # F2 (DM Tower) — Новоданиловская наб.
        }
        for project_id, point in expected.items():
            r = by_id[project_id]
            self.assertEqual((r["latitude"], r["longitude"]), point, project_id)


class TechnicalDuplicateMergeTest(unittest.TestCase):
    """Разметка duplicate_of/legacy_ids из решения 2026-08-18.

    Четырнадцать уверенных технических групп имеют одинаковые координаты.
    AUDIT-008 дополнительно применил мягкую project-связь Manufaqtury:
    строки и две разные координаты сохранены как building-кандидаты.
    """

    # (canonical_id, [legacy_ids])
    GROUPS = [
        ("proj-9", ["proj-60", "proj-70", "proj-186"]),
        ("proj-17", ["proj-45", "proj-242"]),
        ("proj-28", ["proj-65"]),
        ("proj-29", ["proj-131"]),
        ("proj-30", ["proj-133"]),
        ("proj-31", ["proj-41"]),
        ("proj-47", ["proj-34"]),
        ("proj-46", ["proj-219"]),
        ("proj-50", ["proj-110"]),
        ("proj-63", ["proj-162"]),
        ("proj-64", ["proj-66"]),
        ("proj-68", ["proj-198"]),
        ("proj-75", ["proj-137"]),
        ("proj-78", ["proj-151"]),
        ("proj-83", ["proj-84", "proj-174"]),
    ]

    # Группы из раздела "Уточнение после сопоставления с историческими
    # файлами коворкингов" — координаты расходятся на 110-160м или нужна
    # проверка building/площадки; НЕ объединять до отдельного подтверждения.
    NOT_MERGED_GROUPS = [
        ["proj-27", "proj-76"],
        ["proj-193", "proj-69"],
        ["proj-190", "proj-59", "proj-67"],
        ["proj-195", "proj-61", "proj-71"],
    ]

    @classmethod
    def setUpClass(cls):
        if not REGISTRY_PATH.exists():
            raise unittest.SkipTest("data/all_projects_layer.json not generated yet")
        cls.records = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
        cls.by_id = {r["canonical_project_id"]: r for r in cls.records}

    def test_record_count_unchanged_nothing_deleted(self):
        """Слияние — это разметка полей, не удаление строк: 277 classifier-
        производных записей до и после (внешние source добавляются поверх,
        см. AllProjectsLayerRegistryTests.test_record_count_matches_active_raw_data)."""
        classifier_records = [r for r in self.records if r["source"] == "classifier.html"]
        self.assertEqual(len(classifier_records), 277)

    def test_canonical_project_ids_are_globally_unique(self):
        """canonical_project_id не должен повторяться — кроме badaevsky
        (два corpus'а с разными canonical_building_id, отдельное правило)."""
        ids = [r["canonical_project_id"] for r in self.records]
        dupes = {i for i in ids if ids.count(i) > 1} - {"badaevsky"}
        self.assertEqual(dupes, set(), f"canonical_project_id повторяется: {sorted(dupes)}")

    def test_each_group_canonical_has_duplicate_of_none_and_legacy_ids(self):
        for canonical_id, legacy_ids in self.GROUPS:
            canonical = self.by_id[canonical_id]
            self.assertIsNone(canonical["duplicate_of"], canonical_id)
            self.assertEqual(
                sorted(canonical["legacy_ids"], key=lambda x: int(x.split("-")[1])),
                sorted(legacy_ids, key=lambda x: int(x.split("-")[1])),
                canonical_id,
            )

    def test_each_legacy_row_points_to_its_canonical_and_still_exists(self):
        for canonical_id, legacy_ids in self.GROUPS:
            for legacy_id in legacy_ids:
                self.assertIn(legacy_id, self.by_id, legacy_id)
                legacy = self.by_id[legacy_id]
                self.assertEqual(legacy["duplicate_of"], canonical_id, legacy_id)
                # raw_name/источники не потеряны
                self.assertTrue(legacy["raw_name"], legacy_id)
                self.assertEqual(legacy["source"], "classifier.html", legacy_id)

    def test_no_duplicate_of_points_to_another_duplicate_of_row(self):
        """duplicate_of должен указывать на каноническую (не-легаси) запись,
        а не на другую legacy-строку — цепочек дублей быть не должно."""
        canonical_ids = {cid for cid, _ in self.GROUPS}
        for r in self.records:
            if r["duplicate_of"]:
                self.assertIn(r["duplicate_of"], canonical_ids, r["canonical_project_id"])

    def test_four_remaining_uncertain_groups_left_unmerged(self):
        """Координаты внутри этих групп расходятся на 110-160м или требуют
        проверки building/площадки — duplicate_of должен остаться None,
        legacy_ids пустым у всех участников."""
        for group in self.NOT_MERGED_GROUPS:
            for project_id in group:
                self.assertIn(project_id, self.by_id, project_id)
                r = self.by_id[project_id]
                self.assertIsNone(r["duplicate_of"], project_id)
                self.assertEqual(r["legacy_ids"], [], project_id)


class SaleCandidateLinkingTest(unittest.TestCase):
    """outputs/sale_coverage_candidate_classification_2026-08-18.md: 3
    подтверждённых по адресу/данным связки получили alias на существующий
    canonical_project_id/canonical_building_id; ничего не добавлено как
    новый проект. Нижняя Масловка/proj-99 не подтвердилась текстовым
    поиском — оставлена в review_queue, alias не добавлен."""

    CLASS_LABELS = {"A", "A+", "B", "B+"}

    @classmethod
    def setUpClass(cls):
        if not REGISTRY_PATH.exists():
            raise unittest.SkipTest("data/all_projects_layer.json not generated yet")
        cls.records = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))

    def test_twist_and_a101_prokshino_aliases_linked(self):
        by_id = {r["canonical_project_id"]: r for r in self.records}
        self.assertIn("БЦ Twist", by_id["proj-205"]["aliases"])
        self.assertIn("БЦ А101 Прокшино", by_id["proj-216"]["aliases"])

    def test_badaevsky_lента_variants_linked_to_correct_building(self):
        badaevsky_rows = {r["canonical_building_id"]: r for r in self.records if r["canonical_project_id"] == "badaevsky"}
        self.assertIn("Бадаевский Западная", badaevsky_rows["badaevsky-west"]["aliases"])
        self.assertIn("Бадаевский Восточная", badaevsky_rows["badaevsky-east"]["aliases"])

    def test_workplace_republic_forma_linked_to_porta_forma(self):
        """Дополнение к аудиту: Workplace REPUBLIC Forma подтверждён по
        исходным Excel-файлам как историческое название Porta Forma —
        alias на proj-86, новый project ID не создан."""
        by_id = {r["canonical_project_id"]: r for r in self.records}
        proj86 = by_id["proj-86"]
        self.assertEqual(proj86["canonical_name"], "Porta Forma")
        self.assertIn("Workplace REPUBLIC Forma", proj86["aliases"])
        self.assertIsNone(proj86["duplicate_of"])
        ids = {r["canonical_project_id"] for r in self.records}
        self.assertNotIn("Workplace REPUBLIC Forma", ids)

    def test_nizhnyaya_maslovka_not_linked_unconfirmed(self):
        """proj-99 — «Магистральная 12», другой адрес, чем предложенная
        связка «Нижняя Масловка, 12»; строка не найдена ни в одном файле
        data/ — alias НЕ добавлен без текстового подтверждения."""
        by_id = {r["canonical_project_id"]: r for r in self.records}
        proj99 = by_id["proj-99"]
        self.assertNotIn("Нижняя Масловка, 12", proj99["aliases"])
        self.assertNotIn("Нижняя Масловка", proj99["address"])


class ClassLabelsNotProjectsTest(unittest.TestCase):
    """Классы объектов (A/A+/B/B+ из lots_202305/202308/202311.json) — не
    проекты; никогда не должны порождать canonical_project_id или
    попадать в canonical_name/raw_name/aliases как самостоятельный проект."""

    CLASS_LABELS = {"A", "A+", "B", "B+"}

    @classmethod
    def setUpClass(cls):
        if not REGISTRY_PATH.exists():
            raise unittest.SkipTest("data/all_projects_layer.json not generated yet")
        cls.records = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))

    def test_class_labels_are_not_canonical_project_ids(self):
        ids = {r["canonical_project_id"] for r in self.records}
        self.assertEqual(ids & self.CLASS_LABELS, set())

    def test_class_labels_are_not_canonical_or_raw_names(self):
        names = {r["canonical_name"] for r in self.records} | {r["raw_name"] for r in self.records}
        self.assertEqual(names & self.CLASS_LABELS, set())

    def test_class_labels_are_not_standalone_aliases(self):
        for r in self.records:
            self.assertEqual(set(r.get("aliases") or []) & self.CLASS_LABELS, set(), r["canonical_project_id"])


if __name__ == "__main__":
    unittest.main()
