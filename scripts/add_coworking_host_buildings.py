"""Добавляет здания-хосты коворкингов в общий слой (только для заполнения cls).

Контекст: 78 из 79 записей в data/coworking_202606.json не имеют класса
здания, потому что index.html резолвит cls джойном `bc` (имя здания) против
buildingsData (продажа) по точному совпадению строки, а для большинства
сетевых коворкингов здание-хост вообще не зарегистрировано ни там, ни в
data/all_projects_layer.json. См. outputs/coworking_missing_class_qa_2026-08-19.md.

Этот скрипт добавляет building-level записи в общий слой для зданий,
класс которых подтверждён веб-проверкой (офиц. сайт/2ГИС/ЦИАН — источник в
qa_notes каждой записи). Не архитектура PRJ/сделки — source="coworking_host_lookup",
market_channel=[], quarter_offer_refs=[] — эти записи НИКОГДА не попадают в
квартальные продажи/аренду/коворкинг-объёмы и не читаются квартальными
loader'ами index.html (см. tests/test_online_tables_invariants.py).

⚠️ ОГРАНИЧЕНИЕ: эти записи видны только через общий слой/аналитику
(«Конструктор» → «Реестр проектов»). Они НЕ чинят цвет/класс маркера
коворкинга на самой карте — тот джойн (index.html, buildingsData) не читает
all_projects_layer.json и не должен (см. вышеупомянутый инвариант). Чтобы
класс появился в реальном коворкинг-режиме карты, понадобится отдельная
правка data/coworking_*.json или JS-джойна — вне рамок этого скрипта.

Usage: python scripts/add_coworking_host_buildings.py
"""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LAYER_PATH = ROOT / "data" / "all_projects_layer.json"
TODAY = "2026-08-19"

# bc -> (cls, address, evidence)
HOSTS = [
    ("Империя", "A", "Пресненская наб., 6с2 (Москва-Сити)",
     "bashnya-imperiya.ru / themoscowcity.com: Башня Империя, класс A"),
    ("Федерация (Сити)", "A", "Пресненская наб., 12 (Москва-Сити)",
     "fedtower.ru / cian.ru: Башня Федерация, класс A"),
    ("Башня на набережной (В)", "A", "Пресненская наб., 10 (Москва-Сити)",
     "moscow-city-towers.ru: Башня на Набережной, класс A"),
    ("Никольская", "B+", "Ветошный пер., 13",
     "of.ru/bc/2727: БЦ Ветошный пер. 13 (ASpace Никольская), класс B+"),
    ("Цветной бульвар", "B", "Цветной бул., 30с1",
     "tsvetnoy-30.ru: БЦ Цветной 30, класс B"),
    ("Новослободская", "B+", "Новослободская ул., 16",
     "of.ru/bc/873: БЦ Новослободская 16, класс B+"),
    ("Технопарк", "A", "просп. Андропова, 10",
     "cian.ru: Technopark Plaza, класс A"),
    ("Бригантина", "B+", "Новолесная ул., 2",
     "of.ru/bc/49: Бригантина Холл, класс B+"),
    ("Кузнецкий Мост", "A", "Кузнецкий Мост ул., 13",
     "amo.ru: БЦ Кузнецкий Мост 13/9с1, класс A"),
    ("Балчуг", "B", "Садовническая наб., 9",
     "of.ru/bc/1058: БЦ Садовническая наб. 9 (Балчуг), класс B"),
    ("Симонов", "B+", "Ленинская Слобода ул., 26с5",
     "cian.ru/of.ru: Симонов Плаза, класс B+"),
    ("Арма", "B+", "Нижний Сусальный пер., 5",
     "arma-bc.ru: бизнес-парк АРМА, класс B+"),
]


def build_record(bc: str, cls: str, address: str, evidence: str, seq: int) -> dict:
    return {
        "canonical_project_id": f"cwhost-{seq:04d}",
        "canonical_building_id": f"cwhost-{seq:04d}-bld",
        "entity_grain": "building",
        "raw_name": bc,
        "canonical_name": bc,
        "flex_site_label": None,
        "aliases": [],
        "developer": None,
        "address": address,
        "latitude": None,
        "longitude": None,
        "geometry_quality": "unknown",
        "project_status": "Введён",
        "offer_status": "Не применяется",
        "offer_not_started_reason": None,
        "input_year": None,
        "input_quarter": None,
        "input_date_kind": "unknown",
        "cls": cls,
        "gba": None,
        "gla": None,
        "office_area": None,
        "area_scope": "building",
        "zone": None,
        "submarket": None,
        "bizFormed": None,
        "bizForming": None,
        "market_channel": [],
        "source": "coworking_host_lookup",
        "source_date": TODAY,
        "verification_status": "accepted",
        "confidence": "medium",
        "external_only": False,
        "quarter_offer_refs": [],
        "quarter_offer_exists": False,
        "qa_status": "ok",
        "qa_notes": f"Здание-хост для коворкинга, добавлено 2026-08-19 только для заполнения cls у "
                    f"coworking_202606.json записей с bc={bc!r}; НЕ отслеживается NF по каналам "
                    f"продажи/аренды/коворкинга. Источник: {evidence}.",
        "public_visibility": "public",
        "first_seen_at": TODAY,
        "last_verified_at": TODAY,
        "source_count": 1,
        "duplicate_of": None,
        "legacy_ids": [],
    }


def main() -> int:
    with open(LAYER_PATH, encoding="utf-8") as f:
        layer = json.load(f)

    existing_names = {r["canonical_name"] for r in layer if r.get("source") == "coworking_host_lookup"}
    seq = sum(1 for r in layer if r.get("source") == "coworking_host_lookup") + 1
    added = []
    for bc, cls, address, evidence in HOSTS:
        if bc in existing_names:
            continue
        layer.append(build_record(bc, cls, address, evidence, seq))
        added.append(f"cwhost-{seq:04d}")
        seq += 1

    with open(LAYER_PATH, "w", encoding="utf-8") as f:
        json.dump(layer, f, ensure_ascii=False, indent=2)
    print(f"added {len(added)}: {added}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
