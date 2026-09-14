"""2026-09-14: для многокорпусных проектов (общий canonical_project_id,
разные canonical_building_id) сумма GBA по корпусам должна сходиться с
известной агрегатной площадью проекта — с допуском на округление между
источниками. Тест фиксирует известные многокорпусные проекты и не даёт
будущим правкам тихо разъехаться (добавить корпус без изменения суммы,
опечататься в одном из чисел и т.п.).

Пока покрывает только data/all_projects_layer.json (реестр/карта «Все
проекты»/кодификатор). data/buildings_{quarter}.json проверяется
отдельно ниже на структурную синхронизацию (общий canonical_project_id,
уникальные subid) — сумма GBA туда сознательно не дублируется, реестр
остаётся источником истины.
"""
import json
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
REGISTRY_PATH = REPO_ROOT / "data" / "all_projects_layer.json"
BUILDINGS_PATH = REPO_ROOT / "data" / "buildings_202606.json"

# (canonical_project_id, поле для сверки, ожидаемая сумма/значение, допуск)
# "gba"/"gla" — суммируются по корпусам и сверяются с известной агрегатной
# площадью. "Поле" — особый случай: у обеих башен GBA указана одинаковой
# (210000 — общая площадь участка/проекта из источника, НЕ сумма по
# корпусам), а вот GLA у каждой башни своя (72778 и 43809) — сверяем GLA,
# не GBA.
KNOWN_MULTI_CORPUS_PROJECTS = [
    ("badaevsky", "gba", 11145 + 7713, 0),  # Восточная 11145 + Западная 7713, оба числа подтверждены отдельно
    ("pole", "gla", 72778 + 43809, 0),  # GLA действительно разная по башням и суммируется; GBA у обеих одинаковая (210000, площадь участка) — не суммируется
    ("proj-274", "gba", 133754, 5),  # Останкино: 5 записей (К2+К3 объединены — в классификаторе есть только их суммарная площадь), точные цифры из classifier.html (UC-OBJ-0055/0005/0007/0029/0610)
    ("proj-129", "gba", 91397 + 119429, 0),  # iCITY Space+Time; GLA НЕ сверяется — конфликт источников с прежней проектной GLA, см. qa_notes
    ("proj-112", "gba", 141728, 0),  # Air, 3 башни; разделено пропорционально этажности (14/20/34), оценка
    ("proj-261", "gba", 130873, 0),  # Set, 2 башни; разделено пропорционально этажности (20/38), оценка
    ("proj-134", "gba", 118000, 0),  # JOIS CREDO/MAST, пропорция этажности не установлена — поровну 50/50
    ("proj-244", "gba", 105355, 0),  # Рублево Бизнес-Парк, 2 равные башни (12/12 этажей) — поровну 50/50
    ("proj-180", "gba", 83000, 0),  # STONE Калужская, 3 башни K1/K2/K3 (23/13/20 этажей), пропорционально этажности
    ("proj-194", "gla", 30000 + 40000, 2000),  # STONE Савеловская — офисные площади по башням подтверждены источником напрямую; GBA не сверяется отдельно (та же пропорция 30:40)
]


@unittest.skipUnless(REGISTRY_PATH.exists(), "data/all_projects_layer.json not generated yet")
class MultiCorpusAreaReconciliationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.records = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
        cls.by_project = {}
        for r in cls.records:
            cls.by_project.setdefault(r["canonical_project_id"], []).append(r)

    def test_known_multi_corpus_projects_have_at_least_two_building_rows(self):
        for project_id, _, _, _ in KNOWN_MULTI_CORPUS_PROJECTS:
            rows = self.by_project.get(project_id, [])
            self.assertGreaterEqual(len(rows), 2, f"{project_id}: expected >=2 corpus rows")
            for r in rows:
                self.assertEqual(r["entity_grain"], "building", f"{project_id}/{r.get('canonical_building_id')}")
                self.assertIsNotNone(r["canonical_building_id"], project_id)

    def test_corpus_canonical_building_ids_are_unique_within_project(self):
        for project_id, _, _, _ in KNOWN_MULTI_CORPUS_PROJECTS:
            rows = self.by_project.get(project_id, [])
            bids = [r["canonical_building_id"] for r in rows]
            self.assertEqual(len(bids), len(set(bids)), f"{project_id}: duplicate canonical_building_id {bids}")

    def test_corpus_area_sums_match_known_project_total_within_tolerance(self):
        for project_id, field, expected_total, tolerance in KNOWN_MULTI_CORPUS_PROJECTS:
            rows = self.by_project.get(project_id, [])
            values = [r.get(field) for r in rows]
            self.assertNotIn(None, values, f"{project_id}: a corpus row is missing {field} — cannot reconcile")
            actual_total = sum(values)
            self.assertLessEqual(
                abs(actual_total - expected_total), tolerance,
                f"{project_id}: sum({field})={actual_total} vs expected {expected_total} (tolerance {tolerance})",
            )


@unittest.skipUnless(BUILDINGS_PATH.exists(), "data/buildings_202606.json not generated yet")
class MultiCorpusBuildingsFileSyncTest(unittest.TestCase):
    """Проверяет, что data/buildings_202606.json (режим «Продажа») структурно
    согласован с реестром для известных многокорпусных проектов: общий
    canonical_project_id, уникальные subid, число строк совпадает."""

    @classmethod
    def setUpClass(cls):
        cls.buildings = json.loads(BUILDINGS_PATH.read_text(encoding="utf-8-sig"))
        cls.registry = json.loads(REGISTRY_PATH.read_text(encoding="utf-8")) if REGISTRY_PATH.exists() else []

    # buildings_202606.json хранит свою нумерацию (обычно числовую строку
    # canonical_project_id вроде "274", не "proj-274"/"badaevsky"/"pole") —
    # см. codifier.html:unifiedProjectId(), кроссвок строится по имени.
    KNOWN_BUILDINGS_PROJECT_IDS = ["274"]

    def test_known_projects_share_project_id_with_unique_subid(self):
        for pid in self.KNOWN_BUILDINGS_PROJECT_IDS:
            rows = [r for r in self.buildings if r.get("canonical_project_id") == pid]
            self.assertGreaterEqual(len(rows), 2, f"buildings canonical_project_id={pid}: expected >=2 rows")
            subids = [r.get("subid") for r in rows]
            self.assertEqual(len(subids), len(set(subids)), f"canonical_project_id={pid}: duplicate subid {subids}")
            self.assertNotIn(None, subids, f"canonical_project_id={pid}: a row is missing subid")

    def test_ostankino_buildings_row_count_matches_registry_corpus_count(self):
        buildings_rows = [r for r in self.buildings if r.get("canonical_project_id") == "274"]
        registry_rows = [r for r in self.registry if r.get("canonical_project_id") == "proj-274"]
        self.assertEqual(
            len(buildings_rows), len(registry_rows),
            "data/buildings_202606.json and all_projects_layer.json disagree on corpus count for Останкино",
        )


if __name__ == "__main__":
    unittest.main()
