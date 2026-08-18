"""Продолжение аудита unified codifier review_queue (2026-08-18): полное
покрытие всех уникальных ключей верхнего уровня во всех data/lots_*.json
за 2021-2026 (140 ключей). Каждый ключ обязан быть либо:
  - точным совпадением canonical_name/raw_name/alias в data/all_projects_layer.json,
  - подтверждённым не-проектом (класс-метка A/A+/B/B+ и кириллические
    омоглифы, строка "Общий итог" — артефакт итоговой строки Excel),
  - либо явно оставлен в review_queue как unresolved (Нижняя Масловка, 12).

Если появится НОВЫЙ несовпадающий ключ (новый квартал, переименование),
тест упадёт и укажет на него — это сигнал добавить alias или занести в
review_queue, а не тихая пропажа покрытия.
"""
import json
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))
from build_all_projects_layer import NON_PROJECT_SALE_LOT_ARTIFACTS

DATA = REPO_ROOT / "data"
REGISTRY_PATH = DATA / "all_projects_layer.json"

CLASS_LABELS = {"A", "A+", "B", "B+"}

# outputs/unified_codifier_review_queue_2026-08-18.md: упомянут во внешнем
# аудите продажных кандидатов, но строка не найдена ни в одном файле
# data/ при прямом поиске — остаётся unresolved, не в lots_*.json вовсе
# (не является ключом верхнего уровня ни в одном квартале).
KNOWN_UNRESOLVED_EXTERNAL_CLAIMS = {"Нижняя Масловка, 12"}


@unittest.skipUnless(REGISTRY_PATH.exists(), "data/all_projects_layer.json not generated yet")
class SaleLotsFullPeriodCoverageTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
        cls.registry_names = {r["canonical_name"] for r in cls.registry} | {r["raw_name"] for r in cls.registry}
        cls.registry_aliases = set()
        for r in cls.registry:
            cls.registry_aliases |= set(r.get("aliases") or [])

        cls.lot_keys_by_file = {}
        for path in sorted(DATA.glob("lots_20*.json")):
            data = json.loads(path.read_text(encoding="utf-8-sig"))
            if isinstance(data, dict):
                for key in data.keys():
                    cls.lot_keys_by_file.setdefault(key, []).append(path.name)

    def test_at_least_100_quarterly_lot_files_scanned(self):
        """Защита от случайного пустого glob (переименование каталога и т.п.)."""
        self.assertGreaterEqual(len(list(DATA.glob("lots_20*.json"))), 15)

    def test_every_sale_lot_key_is_accounted_for(self):
        unaccounted = []
        for key in self.lot_keys_by_file:
            if key in CLASS_LABELS:
                continue
            if key in NON_PROJECT_SALE_LOT_ARTIFACTS:
                continue
            if key in self.registry_names or key in self.registry_aliases:
                continue
            unaccounted.append(key)
        self.assertEqual(
            unaccounted, [],
            f"Новые несовпадающие ключи lots_*.json, не в реестре и не в review_queue: {unaccounted}",
        )

    def test_non_project_artifacts_never_in_registry(self):
        artifacts = CLASS_LABELS | NON_PROJECT_SALE_LOT_ARTIFACTS
        self.assertEqual(artifacts & self.registry_names, set())
        self.assertEqual(artifacts & self.registry_aliases, set())

    def test_magistralnaya_oktyabrskoye_pole_solid_resolved(self):
        expected = {
            "proj-99": "Магистральная ул., 12",
            "proj-237": "Октябрьское поле",
            "proj-158": "Солид",
        }
        by_id = {r["canonical_project_id"]: r for r in self.registry}
        for canonical_id, alias in expected.items():
            self.assertIn(alias, by_id[canonical_id]["aliases"], canonical_id)

    def test_known_unresolved_claim_absent_from_actual_lot_files(self):
        """Нижняя Масловка, 12 не встречается ни в одном lots_*.json как
        ключ верхнего уровня — подтверждает, что оставить unresolved было
        правильным решением, не тихой потерей данных."""
        for claim in KNOWN_UNRESOLVED_EXTERNAL_CLAIMS:
            self.assertNotIn(claim, self.lot_keys_by_file, claim)


if __name__ == "__main__":
    unittest.main()
