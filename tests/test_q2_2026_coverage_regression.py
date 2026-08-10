"""Регрессия покрытия Q2 2026: каждая запись в квартальных Q2-файлах должна
сопоставляться с data/all_projects_layer.json по canonical ID, алиасу,
адресу или подтверждённой координате.

Выросло из подтверждённого пропуска СODE Novo (data/coworking_202606.json,
id=149) — запись физически существовала в реестре (proj-149), но
quarter_offer_refs не включал 202606 из-за бага в
scripts/build_all_projects_layer.py: load_quarter_presence() сканировал
только buildings_*.json, не coworking_*.json. Это скрывало реальный пропуск
за молчаливым "не сопоставлено". Тест проверяет структурное покрытие
(есть ли сопоставление вообще), а не заполненность quarter_offer_refs
конкретной записи — для этого у отдельных ID есть точечные regression-тесты
(см. test_all_projects_layer_registry.py).
"""
import json
import math
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
REGISTRY_PATH = REPO_ROOT / "data" / "all_projects_layer.json"
BUILDINGS_PATH = REPO_ROOT / "data" / "buildings_202606.json"
RENT_LOTS_PATH = REPO_ROOT / "data" / "rent_lots_202606.json"
COWORKING_PATH = REPO_ROOT / "data" / "coworking_202606.json"

COORD_TOLERANCE_M = 150


def norm(s):
    if not s:
        return ""
    return str(s).strip().lower().replace("ё", "е")


def haversine_m(lat1, lng1, lat2, lng2):
    if lat1 is None or lng1 is None or lat2 is None or lng2 is None:
        return None
    r = 6371000
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lng2 - lng1)
    x = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(x))


@unittest.skipUnless(
    REGISTRY_PATH.exists() and BUILDINGS_PATH.exists() and RENT_LOTS_PATH.exists() and COWORKING_PATH.exists(),
    "требуемые Q2 2026 файлы или реестр отсутствуют",
)
class Q2_2026_CoverageRegressionTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry = json.loads(REGISTRY_PATH.read_text(encoding="utf-8-sig"))
        cls.buildings = json.loads(BUILDINGS_PATH.read_text(encoding="utf-8-sig"))
        cls.rent_lots = json.loads(RENT_LOTS_PATH.read_text(encoding="utf-8-sig"))
        cls.coworking = json.loads(COWORKING_PATH.read_text(encoding="utf-8-sig"))

        cls.name_index = {}
        for r in cls.registry:
            keys = [r.get("raw_name"), r.get("canonical_name")] + (r.get("aliases") or [])
            for k in keys:
                if k:
                    cls.name_index.setdefault(norm(k), []).append(r)

        cls.addr_index = {}
        for r in cls.registry:
            if r.get("address"):
                cls.addr_index.setdefault(norm(r["address"]), []).append(r)

    def _coord_matches(self, lat, lng):
        if lat is None or lng is None:
            return []
        out = []
        for r in self.registry:
            d = haversine_m(lat, lng, r.get("latitude"), r.get("longitude"))
            if d is not None and d <= COORD_TOLERANCE_M:
                out.append(r)
        return out

    def _matches(self, name=None, address=None, lat=None, lng=None):
        found = []
        if name:
            found += self.name_index.get(norm(name), [])
        if address:
            found += self.addr_index.get(norm(address), [])
        found += self._coord_matches(lat, lng)
        return found

    def test_all_buildings_202606_map_to_registry(self):
        unmatched = []
        for b in self.buildings:
            matches = self._matches(b.get("name"), b.get("address"), b.get("lat"), b.get("lng")) \
                or self._matches(b.get("name_orig"), b.get("address"), b.get("lat"), b.get("lng"))
            if not matches:
                unmatched.append(b.get("name"))
        self.assertEqual(
            unmatched, [],
            f"{len(unmatched)} из {len(self.buildings)} записей buildings_202606.json "
            f"не сопоставлены с реестром ни по имени/алиасу, ни по адресу, ни по координате "
            f"(допуск {COORD_TOLERANCE_M} м): {unmatched}",
        )

    def test_all_rent_lots_202606_keys_map_to_registry(self):
        unmatched = [key for key in self.rent_lots.keys() if not self._matches(name=key)]
        self.assertEqual(
            unmatched, [],
            f"{len(unmatched)} из {len(self.rent_lots)} ключей rent_lots_202606.json "
            f"не сопоставлены с реестром: {unmatched}",
        )

    def test_all_coworking_202606_map_to_registry(self):
        unmatched = []
        for c in self.coworking:
            matches = self._matches(c.get("name"), c.get("address") or c.get("bc"), c.get("lat"), c.get("lng"))
            if not matches:
                unmatched.append({"id": c.get("id"), "name": c.get("name")})
        self.assertEqual(
            unmatched, [],
            f"{len(unmatched)} из {len(self.coworking)} записей coworking_202606.json "
            f"не сопоставлены с реестром: {unmatched}",
        )

    def test_code_novo_confirmed_and_not_merged_with_code_novo_2(self):
        """Точечная проверка исправленного пропуска: СODE Novo сопоставляется
        и подтверждён на Q2 2026, но остаётся отдельной записью от СODE Novo 2
        (другой адрес/координаты — не корпус того же здания)."""
        by_id = {r["canonical_project_id"]: r for r in self.registry}
        novo = by_id["proj-149"]
        novo2 = by_id["proj-32"]

        self.assertEqual(novo["raw_name"], "СODE Novo")
        self.assertEqual(novo["address"], "Долгоруковская 21")
        self.assertEqual((novo["latitude"], novo["longitude"]), (55.774932, 37.599579))
        self.assertIn("202606", novo["quarter_offer_refs"])
        self.assertTrue(novo["quarter_offer_exists"])
        self.assertIsNotNone(novo["canonical_building_id"])
        for alias in ("СODE Novo", "CODE Novo", "Долгоруковская 21"):
            self.assertIn(alias, novo["aliases"], alias)

        self.assertNotEqual(novo["canonical_project_id"], novo2["canonical_project_id"])
        self.assertNotEqual(
            (novo["latitude"], novo["longitude"]),
            (novo2["latitude"], novo2["longitude"]),
            "СODE Novo и СODE Novo 2 не должны делить координату — это разные здания",
        )
        if novo.get("canonical_building_id") and novo2.get("canonical_building_id"):
            self.assertNotEqual(novo["canonical_building_id"], novo2["canonical_building_id"])

        # Запись coworking_202606.json id=149 сопоставляется именно с proj-149,
        # а не случайно с proj-32/proj-78 через общий сетевой бренд "СODE".
        cw_novo = next(c for c in self.coworking if c.get("id") == 149)
        self.assertEqual(cw_novo["name"], "СODE Novo")
        matches = self._matches(cw_novo["name"], cw_novo.get("address"), cw_novo.get("lat"), cw_novo.get("lng"))
        matched_ids = {r["canonical_project_id"] for r in matches}
        self.assertIn("proj-149", matched_ids)
        self.assertNotIn("proj-32", matched_ids)

    def test_badaevsky_towers_share_project_not_building_id(self):
        """Разные корпуса/ленты одного проекта не сливаются в одну запись —
        общий canonical_project_id, но разные canonical_building_id."""
        west = next(r for r in self.registry if r["canonical_building_id"] == "badaevsky-west")
        east = next(r for r in self.registry if r["canonical_building_id"] == "badaevsky-east")
        self.assertEqual(west["canonical_project_id"], east["canonical_project_id"])
        self.assertNotEqual(west["canonical_building_id"], east["canonical_building_id"])
        self.assertNotEqual(
            (west["latitude"], west["longitude"]),
            (east["latitude"], east["longitude"]),
        )


if __name__ == "__main__":
    unittest.main()
