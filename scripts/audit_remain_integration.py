"""Аудит полноты и интеграции Remain/Remapp во внешний слой карты.

Не меняет PRJ-логику и архитектуру all_projects_layer.json — только
классифицирует записи Remain против текущего слоя и (для подтверждённых
only_remain) добавляет новые записи с external_only=true, source
"remain_datalens", verification_status="under_review".

Источник Remain: полного 336-строчного дампа DataLens в репозитории нет
(см. REMAIN_GAP_ANALYSIS_2026-07-29.md) — решение пользователя 2026-08-18:
работать по уже собранному gap-анализу (153 продажных объекта, частичный
охват). REMAIN_RECORDS ниже — структурированная выжимка из этого файла
плюс data/test_fixtures/remain_observations.sample.json. При появлении
полного экспорта Remain — заменить REMAIN_RECORDS реальной загрузкой.

Usage:
  python scripts/audit_remain_integration.py [--apply]

Без --apply — только печатает счётчики и список конфликтов (dry run).
С --apply — дописывает подтверждённые only_remain записи в
data/all_projects_layer.json и сохраняет outputs/remain_integration_audit_<date>.md.
"""

from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LAYER_PATH = ROOT / "data" / "all_projects_layer.json"
TODAY = date.today().isoformat()

# category: exact_match (A) / probable_match (B) / only_remain (C)
# extracted from REMAIN_GAP_ANALYSIS_2026-07-29.md — see file for full evidence.
REMAIN_RECORDS = [
    # --- A: exact_match — есть у нас, выпало из Q2 2026 по причине отсутствия лотов, не пробел
    {"external_name": "Обсидиан", "category": "exact_match", "local_match": "Обсидиан (бывший BusinessClass Ходынка)"},
    {"external_name": "LUNAR (Module B)", "category": "exact_match", "local_match": "Lunar модуль В"},
    {"external_name": "STONE Towers (Tower A/C)", "category": "exact_match", "local_match": "STONE Towers. Tower A"},
    {"external_name": "Парк Легенд (корпуса 1-4)", "category": "exact_match", "local_match": "Парк Легенд класс А / класс В+"},
    {"external_name": "Серебряный фонтан", "category": "exact_match", "local_match": "БЦ Серебряный Фонтан"},
    {"external_name": "БЦ на 2-м Силикатном пр-д, вл.13", "category": "exact_match", "local_match": "Бизнес-центр SEZAR", "note": "GBA 15862 / GLA 11246 совпадают точно"},
    {"external_name": "Лофт Квартал Сколково", "category": "exact_match", "local_match": "БЦ Сколково (частично)"},
    # --- B: probable_match — под другим именем, координаты/GBA почти сходятся
    # 2026-08-18: Botanica Plaza и Rail.A перепроверены (developer + офиц. адрес
    # через commercial-сайты застройщиков) и переведены в exact_match — расхождение
    # координат было ошибкой геокодирования на нашей стороне, исправлено в
    # data/all_projects_layer.json (proj-170, proj-173). Не только_remain.
    {"external_name": "Botanica Plaza", "category": "exact_match", "local_match": "Plaza Botanica", "resolution_note": "координаты/адрес исправлены на офиц. ул. Вильгельма Пика, д. 11 (proj-170)"},
    {"external_name": "Rail.A", "category": "exact_match", "local_match": "Rail.A", "resolution_note": "координаты уточнены по rail-a.ru (proj-173), адрес и девелопер совпадали изначально"},
    {"external_name": "Kobzon City (K-City) I+II оч.", "category": "probable_match", "local_match": "K-city", "note": "GBA 17700+42139=59839 ~= наши 59800"},
    {"external_name": "Деловой Центр Ликова", "category": "probable_match", "local_match": "LIKOVA", "note": "GBA 53500 vs 53293"},
    # 2026-08-18: остаётся conflict — не ошибка, а разница масштаба (у нас 1 корпус
    # из 5, у Remain сумма по кварталу); см. qa_notes proj-216. GBA/GLA не менять
    # без разбивки по building.
    {"external_name": "Бизнес-квартал Прокшино Башни 1/2/3", "category": "probable_match", "local_match": "А101 Прокшино", "conflict_note": "наши GBA 42000 покрывают один корпус из 5; сумма Remain 113029 — весь квартал (>177 тыс. кв.м по офиц. данным А101) — resolved_scope_difference, не пробел данных"},
    {"external_name": "МАУНТ", "category": "probable_match", "local_match": "Mount"},
    # --- C: only_remain — введены, должны попасть в Q2 2026 если есть лоты (высокая уверенность по вводу)
    # 2026-08-18 web-проверка по офиц. сайтам девелоперов (не NF-подтверждение,
    # только сигнал "лоты реально существуют"):
    {"external_name": "МФК Центральный Телеграф", "category": "only_remain", "developer": "VOS'HOD", "completion": "2026-Q2", "gba": 64824, "office_area": 28121, "confidence": "low", "note": "REJECTED 2026-08-18: здание целиком куплено Т-Банком под корп. университет (voshodmoscow.ru), продажи лотов отменены — не добавлять в квартальные срезы"},
    {"external_name": "ЗИЛАРТ GRAND (Дом 18)", "category": "only_remain", "developer": "ЛСР", "completion": "2026-Q2", "gba": 35600, "office_area": 18950, "confidence": "medium", "note": "лоты подтверждены на lsr.ru, остаётся internal_only до NF-подтверждения"},
    {"external_name": "Sydney City", "category": "only_remain", "developer": "ГК ФСК", "completion": "2026-Q2", "gba": 75105, "office_area": 27840, "confidence": "medium", "note": "REJECTED 2026-08-19: подтверждён дубль data/future_projects.json OBJ-0668 'Sydney City' (тот же адрес ул. Шеногина 2, тот же девелопер ГК ФСК, GBA 70000 совпадает точно как с OBJ-0668, так и с независимым подтверждением stroi.mos.ru) — не пробел, other-registry duplicate. remain-only-0003 в data/ уже вручную помечен verification_status=blocked/qa_status=duplicate_suspect."},
    {"external_name": "Moscow Towers", "category": "only_remain", "developer": "ООО «Гранд Сити»", "completion": "2024-Q2", "gba": 411147, "office_area": 262800, "confidence": "medium", "note": "REJECTED 2026-08-19: подтверждён дубль data/future_projects.json OBJ-0021 'Moscow Towers' (тот же девелопер Гранд Сити, GLA 262800 совпадает точно, source_sheets OBJ-0021 уже включает 'remain') — не пробел, other-registry duplicate. remain-only-0004 в data/ уже вручную помечен verification_status=blocked/qa_status=duplicate_suspect — идемпотентная проверка existing_remain_ids ниже не создаст его заново."},
    {"external_name": "Офисно-торговый центр Нагатинская", "category": "only_remain", "developer": "Трэйд Инвестментс", "completion": "2028-Q3", "gba": 228742, "office_area": 45000, "confidence": "low", "note": "лоты не ожидаются (ранняя стадия, ввод 2028); подтверждено stroi.mos.ru — часть ТПУ Нагатинская, офисно-торговый центр с кинозалами и бассейном; не найден ни в all_projects_layer.json, ни в future_projects.json — реальный пробел"},
]


def load_layer() -> list[dict]:
    return json.loads(LAYER_PATH.read_text(encoding="utf-8-sig"))


def classify() -> dict:
    result = {"exact_match": [], "probable_match": [], "only_remain": [], "conflict": []}
    for rec in REMAIN_RECORDS:
        cat = rec["category"]
        if rec.get("conflict_note"):
            result["conflict"].append(rec)
        result[cat].append(rec)
    return result


def build_only_remain_entry(rec: dict, next_seq: int) -> dict:
    return {
        "canonical_project_id": f"remain-only-{next_seq:04d}",
        "canonical_name": rec["external_name"],
        "raw_name": rec["external_name"],
        "address": None,
        "developer": rec.get("developer"),
        "gba": rec.get("gba"),
        "gla": None,
        "office_area": rec.get("office_area"),
        "cls": None,
        "zone": None,
        "submarket": None,
        "latitude": None,
        "longitude": None,
        "geometry_quality": "unknown",
        "entity_grain": "project",
        "area_scope": "project",
        "project_status": "Введён" if rec.get("completion") else "Не установлен",
        "offer_status": "Ещё не вышел в продажу",
        "offer_not_started_reason": "Нет подтверждённых лотов",
        "quarter_offer_exists": False,
        "quarter_offer_refs": [],
        "market_channel": [],
        "input_quarter": None,
        "input_year": None,
        "input_date_kind": "unknown",
        "first_seen_at": TODAY,
        "last_verified_at": TODAY,
        "source": "remain_datalens",
        "source_date": "2026-07-29",
        "source_count": 1,
        "external_only": True,
        "confidence": rec.get("confidence", "low"),
        "verification_status": "under_review",
        "public_visibility": "internal_only",
        "duplicate_of": None,
        "legacy_ids": [],
        "aliases": [],
        "canonical_building_id": None,
        "bizFormed": None,
        "bizForming": None,
        "flex_site_label": None,
        "qa_status": "quarantine",
        "qa_notes": f"only_remain кандидат из REMAIN_GAP_ANALYSIS_2026-07-29.md (раздел C, {rec.get('completion', 'дата не указана')}); "
                    "перед public_visibility нужна проверка реальных лотов на продажу/аренду.",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    grouped = classify()
    layer = load_layer()
    existing_remain_ids = {r["canonical_project_id"] for r in layer if r.get("source") == "remain_datalens"}

    print(f"exact_match: {len(grouped['exact_match'])}")
    print(f"probable_match: {len(grouped['probable_match'])}")
    print(f"only_remain: {len(grouped['only_remain'])}")
    print(f"only_local: n/a (требует полного дампа Remain — не оценивается по частичному gap-анализу)")
    print(f"conflict: {len(grouped['conflict'])}")
    if grouped["conflict"]:
        print("\nКонфликты:")
        for c in grouped["conflict"]:
            print(f"  - {c['external_name']} <-> {c['local_match']}: {c['conflict_note']}")

    new_entries = []
    seq = 1
    for rec in grouped["only_remain"]:
        candidate_id = f"remain-only-{seq:04d}"
        if candidate_id in existing_remain_ids:
            seq += 1
            continue
        new_entries.append(build_only_remain_entry(rec, seq))
        seq += 1

    if args.apply:
        layer.extend(new_entries)
        LAYER_PATH.write_text(json.dumps(layer, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"\nApplied: added {len(new_entries)} only_remain record(s) to {LAYER_PATH.relative_to(ROOT)}")
    else:
        print(f"\nDry run: would add {len(new_entries)} only_remain record(s). Re-run with --apply to write.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
