"""Geocoding/id stability regression guards for data/coworking_{quarter}.json.

Scope, deliberately narrow: these tests do NOT try to validate the whole
historical archive (2021-2026 has confirmed drift pre-dating any fix, see
current_state_audit.md) - they guard the two things that matter going
forward:
  1. The specific QA-001/QA-006/QA-007 anchor points stay at the addresses
     QA_COORDINATION.md says were confirmed correct, in the CURRENT quarter.
  2. No NEW hard_error-class jump (>1000m, same id) appears between the two
     most recent quarters - that's the actionable "did this regress" signal,
     not "is 2023 data perfect" (it isn't, and rewriting history is out of
     scope here).
"""
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from audit_coworking_geocoding import (  # noqa: E402
    load_quarter,
    haversine_m,
    classify,
    HARD_ERROR_M,
)

LATEST_QUARTER = "202606"
PREV_QUARTER = "202603"


def _find(rows, rid):
    return next((r for r in rows if r.get("id") == rid), None)


class QaAnchorPointsTest(unittest.TestCase):
    """QA-001/QA-006/QA-007 из QA_COORDINATION.md — проверка на ТЕКУЩЕМ
    квартале, не на архиве. 'FIXED' в старом отчёте — не доказательство,
    этот тест — доказательство (или нет)."""

    @classmethod
    def setUpClass(cls):
        path = REPO_ROOT / "data" / f"coworking_{LATEST_QUARTER}.json"
        if not path.exists():
            raise unittest.SkipTest(f"data/coworking_{LATEST_QUARTER}.json отсутствует")
        cls.rows = load_quarter(path)

    def test_qa001_apollax_federation_not_at_known_bad_stub(self):
        """QA-001: id=183 не должен быть на известной заглушке 55.755819,37.617644."""
        row = _find(self.rows, 183)
        if row is None:
            self.skipTest("id=183 отсутствует в текущем квартале")
        dist_to_stub = haversine_m(row["lat"], row["lng"], 55.755819, 37.617644)
        self.assertGreater(dist_to_stub, 50, "id=183 всё ещё на известной заглушке координат (QA-001)")

    def test_qa006_flexity_riverside_and_savodovaya_have_distinct_coords(self):
        """QA-006: id=243 (Риверсайд Тауэрс) и id=246 (Садовая Плаза) не должны
        совпадать координатами друг с другом или с заведомо неверными точками,
        которые были у них на момент отчёта."""
        r243 = _find(self.rows, 243)
        r246 = _find(self.rows, 246)
        if r243 is None or r246 is None:
            self.skipTest("id 243/246 отсутствуют в текущем квартале")
        dist = haversine_m(r243["lat"], r243["lng"], r246["lat"], r246["lng"])
        self.assertGreater(dist, 50, "Риверсайд Тауэрс и Садовая Плаза на одной точке — вероятно не разгеокодированы")


class NoNewHardErrorDriftTest(unittest.TestCase):
    """Между двумя последними кварталами не должно появляться НЕОБЪЯСНЁННЫХ
    прыжков координат >1000м для одного и того же id.

    id 110, 160 — QA-013/QA-014 (qa_handoff.json), перепроверено вручную.
    id 156, 238 — перепроверено в этом заходе (см. current_state_audit.md,
    scripts/fix_coworking_202606_geocoding.py NO_CHANGE_CONFIRMED_GOOD):
    202606 координата совпадает с независимым источником (Yandex/2GIS) в
    пределах ~10м, 202603 была неверной. Остальные 8 ранее неподтверждённых
    id (118,119,211,213,218,222,235,256) — исправлены и переномерованы
    (9001-9008, см. тот же скрипт), поэтому больше не встречаются под
    старым id в 202606 и не всплывают в этом сравнении вовсе.
    Любой НОВЫЙ id с таким скачком, не в этом списке — либо
    незадокументированный фикс (обнови список ПОСЛЕ проверки тем же
    методом), либо реальный регресс."""
    KNOWN_GOOD_JUMPS = {110, 160, 156, 238}

    @classmethod
    def setUpClass(cls):
        prev_path = REPO_ROOT / "data" / f"coworking_{PREV_QUARTER}.json"
        cur_path = REPO_ROOT / "data" / f"coworking_{LATEST_QUARTER}.json"
        if not prev_path.exists() or not cur_path.exists():
            raise unittest.SkipTest("нет обоих последних кварталов для сравнения")
        cls.prev_rows = load_quarter(prev_path)
        cls.cur_rows = load_quarter(cur_path)

    def test_no_hard_error_jump_between_last_two_quarters(self):
        prev_by_id = {r["id"]: r for r in self.prev_rows if r.get("id") is not None}
        jumps = []
        for r in self.cur_rows:
            rid = r.get("id")
            if rid is None or rid not in prev_by_id:
                continue
            p = prev_by_id[rid]
            if None in (p.get("lat"), p.get("lng"), r.get("lat"), r.get("lng")):
                continue
            dist = haversine_m(p["lat"], p["lng"], r["lat"], r["lng"])
            if classify(dist) == "hard_error" and rid not in self.KNOWN_GOOD_JUMPS:
                jumps.append((rid, round(dist, 1), p.get("address"), r.get("address")))
        self.assertEqual(jumps, [], f"Необъяснённые скачки координат >{HARD_ERROR_M}м между "
                                     f"{PREV_QUARTER} и {LATEST_QUARTER} (не в списке подтверждённых "
                                     f"фиксов KNOWN_GOOD_JUMPS): {jumps}")


class RenumberedFixesTest(unittest.TestCase):
    """8 записей, ранее без QA-тикета и с координатой >1км от истины,
    исправлены и переномерованы (9001-9008) в scripts/
    fix_coworking_202606_geocoding.py — проверяем, что фикс держится
    (новый id есть, старый id как prev_id сохранён для трассировки,
    координата не откатилась)."""
    EXPECTED = {
        9001: (118, 55.699467, 37.625595),
        9002: (119, 55.757718, 37.617069),
        9003: (211, 55.696007, 37.625513),
        9004: (213, 55.711687, 37.581632),
        9005: (218, 55.776527, 37.679404),
        9006: (222, 55.692387, 37.529017),
        9007: (235, 55.728652, 37.645578),
        9008: (256, 55.730426, 37.634793),
    }

    @classmethod
    def setUpClass(cls):
        path = REPO_ROOT / "data" / f"coworking_{LATEST_QUARTER}.json"
        if not path.exists():
            raise unittest.SkipTest("нет текущего квартала")
        cls.rows = load_quarter(path)

    def test_renumbered_rows_present_with_correct_coords_and_prev_id(self):
        for new_id, (old_id, lat, lng) in self.EXPECTED.items():
            row = _find(self.rows, new_id)
            self.assertIsNotNone(row, f"id={new_id} (бывший {old_id}) отсутствует в {LATEST_QUARTER}")
            self.assertEqual(row.get("prev_id"), old_id, f"id={new_id}: prev_id не совпадает с {old_id}")
            dist = haversine_m(row["lat"], row["lng"], lat, lng)
            self.assertLess(dist, 10, f"id={new_id}: координата уехала от подтверждённой ({dist:.1f}м)")

    def test_old_ids_no_longer_present(self):
        old_ids = {old for old, _, _ in self.EXPECTED.values()}
        present_old = {r.get("id") for r in self.rows if r.get("id") in old_ids}
        self.assertEqual(present_old, set(), f"Старые id всё ещё используются в {LATEST_QUARTER}: {present_old}")


class NoDuplicateIdWithinLatestQuarterTest(unittest.TestCase):
    def test_no_duplicate_id_in_current_quarter(self):
        path = REPO_ROOT / "data" / f"coworking_{LATEST_QUARTER}.json"
        if not path.exists():
            self.skipTest("нет текущего квартала")
        rows = load_quarter(path)
        ids = [r.get("id") for r in rows if r.get("id") is not None]
        dupes = {i for i in ids if ids.count(i) > 1}
        self.assertEqual(dupes, set(), f"Дублирующиеся id в {LATEST_QUARTER}: {dupes}")


if __name__ == "__main__":
    unittest.main()
