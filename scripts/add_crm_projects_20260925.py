"""Add three office projects found via the CRM export (2026-09-25) and verified on the web.

Idempotent: reruns replace the same unified_id / canonical_project_id rows.
Coordinates come from Yandex Geocoder (the key is not stored in the repo);
zone/submarket/district come from data/*.geojson by point-in-polygon.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AUDITED = ROOT / "data" / "unified_classifier_audited_2026-08-27.json"
LAYER = ROOT / "data" / "all_projects_layer.json"
MAPPING = ROOT / "outputs" / "classifier_registry_mapping_2026-08-30.json"
DATE = "2026-09-25"

OBJECTS = [
    {
        "unified_id": "UC-OBJ-ADD-355",
        "source_id": "manual-20260925-granard-olimpiyskiy",
        "canonical_project_id": "proj-add-granard-olimpiyskiy-20260925",
        "name": "GRANARD Олимпийский",
        "aliases": ["Олимпийский", "GRANARD на Олимпийском"],
        "address": "Олимпийский пр-т, 1",
        "developer": "GRANARD",
        "gba": 74152,
        "gla": 58000,
        "cls": "A",
        "commission_year": 2030,
        "commission_quarter": None,
        "status": "Проектный",
        "latitude": 55.784395,
        "longitude": 37.622244,
        "coordinates_status": "geocoded_approx",
        "geo_ao": "Центральный",
        "geo_raion": "Мещанский",
        "geo_zone": "СК-ТТК",
        "geo_submarket": "ТТК Север",
        "layer_status": "Строится",
        "layer_offer_status": "Ещё не вышел в продажу",
        "offer_reason": "Проектная стадия",
        "source_links": ["https://granard.ru/projects.html", "https://olimpiyskiy.office.moscow/"],
        "confidence": "medium",
        "verification_status": "Проект подтверждён сайтом девелопера GRANARD и брокерскими карточками; строка добавлена из CRM-выгрузки 25.09.2026.",
        "classification_note": "Офисная башня 34 этажа, около 178 м. granard.ru называет общую площадь 74 152 м², kf.expert — 58 000 м² к аренде (принято как GLA, один источник). Срок ввода 2030 (квартал не найден), статус «строится» принят по формулировке источников «строится или в разработке», точный не подтверждён. Не дубль GRANARD Белорусская (1-я ул. Ямского Поля, 30). Координата — ближайший геокодированный номер (Олимпийский пр-т, 5с1), точность приблизительная.",
        "review_reason": "Статус и квартал ввода не подтверждены; GLA из одного источника.",
    },
    {
        "unified_id": "UC-OBJ-ADD-356",
        "source_id": "manual-20260925-mozhayskiy-val-7",
        "canonical_project_id": "proj-add-mozhayskiy-val-7-20260925",
        "name": "Можайский Вал, вл. 7",
        "aliases": [],
        "address": "Можайский Вал ул., вл. 7",
        "developer": "ООО «Нептун-Трэйдинг»",
        "gba": 41000,
        "gla": None,
        "cls": "A",
        "commission_year": 2027,
        "commission_quarter": None,
        "status": "Строящийся",
        "latitude": 55.743765,
        "longitude": 37.557295,
        "coordinates_status": "geocoded_approx",
        "geo_ao": "Западный",
        "geo_raion": "Дорогомилово",
        "geo_zone": "СК-ТТК",
        "geo_submarket": "ТТК Запад",
        "layer_status": "Строится",
        "layer_offer_status": "Ещё не вышел в продажу",
        "offer_reason": "Нет подтверждённых лотов",
        "source_links": [
            "https://www.novostroy-m.ru/baza/biznestsentr_mojayskiy_val_vl",
            "https://investprojects.info/project-groups/29914",
        ],
        "confidence": "medium",
        "verification_status": "Текущая карточка точного объекта и независимый трекер строительства подтверждают стройку; год сдачи 2027, квартал не установлен.",
        "classification_note": "БЦ 18 этажей, более 41 000 м² общей площади (GLA не найдена). Текущая карточка точного объекта указывает статус «строится» и срок сдачи 2027; независимый трекер также относит объект к активной стройке. Квартал не переносится без подтверждения.",
        "review_reason": "Не найден подтверждённый квартал ввода и точная GLA.",
    },
    {
        "unified_id": "UC-OBJ-ADD-357",
        "source_id": "manual-20260925-luzhnetskaya-sminex",
        "canonical_project_id": "proj-add-luzhnetskaya-sminex-20260925",
        "name": "Лужнецкая наб. (Sminex)",
        "aliases": ["Лужнецкая наб., 1 (ОСЗ Sminex)", "Luzhnetskaya BC"],
        "address": "Лужнецкая наб., вл. 10А",
        "developer": "Sminex",
        "gba": None,
        "gla": None,
        "cls": "A",
        "commission_year": None,
        "commission_quarter": None,
        "status": "Анонсированный",
        "latitude": 55.715423,
        "longitude": 37.565254,
        "coordinates_status": "geocoded_approx",
        "geo_ao": "Центральный",
        "geo_raion": "Хамовники",
        "geo_zone": "ТТК-МКАД",
        "geo_submarket": "ТТК Запад",
        "layer_status": "Не установлен",
        "layer_offer_status": "Ещё не вышел в продажу",
        "offer_reason": "Проектная стадия",
        "source_links": ["https://sminex.com/luzhnetskaya-bc", "https://dvizhenie.ru/"],
        "confidence": "low",
        "verification_status": "Проект подтверждён страницей Sminex и СМИ; адрес у девелопера вл. 10А (в CRM — д. 1), срок ввода не найден.",
        "classification_note": "Офисная башня класса A, 22 этажа, офисная часть более 26 000 м² (тип площади не уточнён, в GBA/GLA не переносилась). Начало строительства и продаж планируется с 2027, CRM указывает ввод 2031 (не подтверждён).",
        "review_reason": "Нет срока ввода и точных площадей; адрес по данным девелопера отличается от CRM.",
    },
]


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write(path: Path, value) -> None:
    raw = path.read_bytes().decode("utf-8-sig")
    nl = "\r\n" if "\r\n" in raw else "\n"
    text = json.dumps(value, ensure_ascii=False, indent=2) + "\n"
    path.write_bytes(text.replace("\n", nl).encode("utf-8"))


def classifier_records():
    rows = []
    for o in OBJECTS:
        rows.append({
            "unified_id": o["unified_id"],
            "source_id": o["source_id"],
            "name": o["name"],
            "address": o["address"],
            "developer": o["developer"],
            "gba": o["gba"],
            "gla": o["gla"],
            "cls": o["cls"],
            "commission_year": o["commission_year"],
            "commission_quarter": o["commission_quarter"],
            "status": o["status"],
            "latitude": o["latitude"],
            "longitude": o["longitude"],
            "coordinates_status": o["coordinates_status"],
            "legacy_ids": [],
            "quarter_offer_refs": [],
            "market_channel": [],
            "layer_status": o["layer_status"],
            "layer_offer_status": o["layer_offer_status"],
            "layer_source": "manual_web_verification",
            "layer_source_date": DATE,
            "layer_qa_notes": o["classification_note"],
            "source_links": o["source_links"],
            "verification_status": o["verification_status"],
            "confidence": o["confidence"],
            "entity_type": "office_project",
            "classification_note": o["classification_note"],
            "needs_review": True,
            "review_reason": o["review_reason"],
            "canonical_no": None,
            "subid": "01",
            "tower_label": "",
            "canonical_project_id": o["canonical_project_id"],
            "geo_ao": o["geo_ao"],
            "geo_raion": o["geo_raion"],
            "geo_zone": o["geo_zone"],
            "geo_submarket": o["geo_submarket"],
            "geo_bizFormed": None,
            "geo_bizForming": None,
        })
    return rows


def layer_records():
    rows = []
    for o in OBJECTS:
        rows.append({
            "canonical_project_id": o["canonical_project_id"],
            "canonical_building_id": None,
            "entity_grain": "project",
            "raw_name": o["name"],
            "canonical_name": o["name"],
            "flex_site_label": None,
            "aliases": o["aliases"],
            "developer": o["developer"],
            "address": o["address"],
            "latitude": o["latitude"],
            "longitude": o["longitude"],
            "geometry_quality": o["coordinates_status"],
            "project_status": o["layer_status"],
            "offer_status": o["layer_offer_status"],
            "offer_not_started_reason": o["offer_reason"],
            "input_year": o["commission_year"],
            "input_quarter": o["commission_quarter"],
            "input_date_kind": "planned" if o["commission_year"] else "unknown",
            "cls": o["cls"],
            "gba": o["gba"],
            "gla": o["gla"],
            "office_area": o["gla"],
            "area_scope": "project",
            "zone": o["geo_zone"],
            "submarket": o["geo_submarket"],
            "bizFormed": None,
            "bizForming": None,
            "market_channel": [],
            "source": "manual_web_verification",
            "source_date": DATE,
            "verification_status": "under_review",
            "confidence": o["confidence"],
            "external_only": False,
            "quarter_offer_refs": [],
            "quarter_offer_exists": False,
            "qa_status": "ok",
            "qa_notes": "entity_role=office_project assigned 2026-09-25; entity-role contract introduced 2026-08-22; source: CRM export 2026-09-25 + web verification. " + o["classification_note"],
            "public_visibility": "public",
            "first_seen_at": "202609",
            "last_verified_at": DATE,
            "source_count": len(o["source_links"]),
            "duplicate_of": None,
            "legacy_ids": [],
            "entity_role": "office_project",
            "observed_market_channels": [],
            "construction_start_year": None,
            "construction_start_quarter": None,
            "sales_start_year": None,
            "sales_start_quarter": None,
        })
    return rows


def main() -> None:
    ids = {o["unified_id"] for o in OBJECTS}
    audited = load(AUDITED)
    audited["records"] = [r for r in audited["records"] if r.get("unified_id") not in ids]
    audited["records"].extend(classifier_records())
    write(AUDITED, audited)

    layer = load(LAYER)
    pids = {o["canonical_project_id"] for o in OBJECTS}
    layer[:] = [r for r in layer if r.get("canonical_project_id") not in pids]
    layer.extend(layer_records())
    write(LAYER, layer)

    mapping = load(MAPPING)
    mapping[:] = [r for r in mapping if r.get("unified_id") not in ids]
    for o in OBJECTS:
        mapping.append({
            "unified_id": o["unified_id"],
            "canonical_no": None,
            "name": o["name"],
            "address": o["address"],
            "status": "new_record",
            "matched_project_id": None,
            "match_basis": "CRM export 2026-09-25 + web verification (user-requested addition)",
            "coord_corroborated": False,
        })
    write(MAPPING, mapping)
    print("Added/updated:", ", ".join(sorted(ids)))


if __name__ == "__main__":
    main()
