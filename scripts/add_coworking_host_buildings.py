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

import hashlib
import json
from pathlib import Path

from all_projects_entity_roles import role_assignment_note
from unified_building_identity import link_coworking_sites, link_note, normalize_label

ROOT = Path(__file__).resolve().parents[1]
LAYER_PATH = ROOT / "data" / "all_projects_layer.json"
TODAY = "2026-08-19"
COORDINATE_RECHECK_DATE = "2026-08-22"

# Единственный bc в текущем срезе, который относится к двум соседним домам:
# Space Балчуг — Садовническая 9А, KW Балчуг — Садовническая 9. Запись-хост
# ниже описывает именно дом 9, поэтому выбор сделан по адресу, не по ближайшей
# точке. Остальные HOSTS имеют одну уникальную текущую координату на bc.
HOST_COORDINATE_OVERRIDES = {
    "Балчуг": (55.746441, 37.629053, "coworking_202606.json id=233, Садовническая наб., 9"),
}

# Two-source identity decision: the Multispace Porta announcement names BC
# Porta, while the official project site and a second market source place that
# building at Заречная 2/1. Keep operator sites separate, share one building id.
BC_CANONICAL_LABELS = {
    "porta": "Заречная 2/1",
}
HOST_ALIASES = {
    "Заречная 2/1": ["Porta"],
}
PREFERRED_BUILDING_IDS = {
    "Долгоруковская 21": "code-novo-dolgorukovskaya-21",
}
HISTORICAL_HOST_OVERRIDES = {
    "Онегин": {
        "address": "Москва, улица Малая Полянка, 2",
        "latitude": 55.728358,
        "longitude": 37.615048,
        "evidence": (
            "pmg-office.ru (official operator site) and cian.ru/coworking-servisnyj-ofis-pmg-onegin-71739; "
            "checked 2026-08-22"
        ),
    },
}

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
    # --- вторая партия, 2026-08-19 (продолжение)
    ("Новосущевский", "B+", "Сущевский вал ул., 18",
     "cian.ru: БЦ Новосущевский, класс B+"),
    ("Риверсайд Тауэрс", "A", "Космодамианская наб., 52",
     "of.ru/bc/1359, cian.ru: Riverside Towers, класс A"),
    ("Садовая Плаза", "A", "Долгоруковская ул., 7",
     "kf.expert, cian.ru: Садовая Плаза, класс A"),
    ("Павелецкая Плаза (А)", "A", "Павелецкая пл., 2с1",
     "of.ru/bc/paveletckaya-plaza, restate.ru: Павелецкая Плаза, класс A"),
    ("Павелецкая Плаза (В)", "A", "Павелецкая пл., 2",
     "of.ru/bc/paveletckaya-plaza, restate.ru: Павелецкая Плаза, класс A"),
    ("Black&White", "A", "Кожевническая ул., 14",
     "cian.ru, blackandwhite-bc.ru: Black and White, класс A"),
    ("Долгоруковская 21", "B+", "Долгоруковская ул., 21с1",
     "of.ru/bc/1016, cian.ru: БЦ Долгоруковская 21с1, класс B+"),
    ("МФК Савеловский сити", "B+", "Новодмитровская ул., 2к2",
     "cian.ru, savelovsky.city: Савёловский Сити, класс B+"),
    ("Зубовский 17", "B", "Зубовский б-р, 17 стр.1",
     "fortexgroup.ru: БЦ Зубовский бульвар 17, класс B"),
    ("Остоженка", "B+", "Остоженка ул., 25",
     "apex-realty.ru: БЦ Остоженка 25, класс B+"),
    ("Сретенка", "B+", "Сретенский бул., 5",
     "of.ru/bc/10742, fortexgroup.ru: БЦ Сретенский 5, класс B+"),
    ("КМ19", "B", "Кузнецкий Мост ул., 19с1",
     "brightrich.moscow, wikimetria.ru: БЦ Кузнецкий Мост 19с1, класс B"),
    ("Авион", "B", "Ленинградский просп., 47 стр.2",
     "avion-center.ru: БЦ Авион, класс B"),
    ("Капитолий Вернадского", "A", "просп. Вернадского, 6",
     "cian.ru, bc-kapitoliy.ru: БЦ Капитолий Вернадского, класс A"),
    # --- третья партия, 2026-08-19 (продолжение)
    ("Композиторская", "B", "Композиторская ул., 17",
     "cian.ru, fortexgroup.ru: БЦ Композиторская 17, класс B"),
    ("Меркурий", "A", "1-й Красногвардейский пр-д, 15",
     "kf.expert, fortexgroup.ru: Меркурий Сити, класс A"),
    ("Citydel", "A", "ул. Земляной Вал, 9",
     "citydel-bc.ru, cian.ru: БЦ Ситидел, класс A"),
    ("Workki Комсомольская", "B", "Новорязанская ул., 8",
     "kf.expert: Workki Комсомольская, класс B"),
    ("Нео Гео", "B+", "ул. Бутлерова, 17",
     "neogeo-centre.ru, restate.ru: БЦ Neo Geo, класс B+"),
    ("На Тульской", "B+", "Б. Тульская ул., 19",
     "of.ru/bc/10258, fortexgroup.ru: БЦ Большая Тульская 19, класс B+"),
    ("Галерея Актер", "B+", "Тверская ул., 16с1",
     "of.ru/bc/1296, cian.ru: БЦ Галерея Актер, класс B+"),
    ("Милютинский", "B+", "Милютинский пер., 13с1",
     "brightrich.moscow: БЦ Милютинский 13с1, класс B+"),
    ("Даниловская Мануфактура", "B+", "Варшавское ш., 9",
     "danilovskaya-manufactura.ru, icx.ru: Даниловская Мануфактура, класс B+"),
    ("Гостиница Москва", "A", "ул. Охотный Ряд, 2",
     "cian.ru, of.ru/bc/1112: БЦ Гостиница Москва, класс A"),
    ("SOK Земляной Вал", "B+", "ул. Земляной Вал, 8",
     "of.ru/bc/483, move.ru: БЦ Земляной Вал 8, класс B+"),
    ("SOK Сады Пекина", "A", "Большая Садовая ул., 5к1",
     "kf.expert, sady-pekina.ru: Сады Пекина, класс A"),
    ("Refolio Достоевский", "B", "Институтский пер., 2",
     "cian.ru, mega-realty.ru: БЦ Институтский пер. 2/1, класс B"),
    ("Deworkacy Савинский", "B+", "Б. Саввинский пер., 8с1",
     "kf.expert, brightrich.moscow: Deworkacy Саввинский, класс B+"),
    ("DM Tower", "A", "Новоданиловская наб., 10А",
     "kf.expert, dm-tower.moscow: БЦ DM Tower, класс A"),
    ("Фили Град", "A", "Береговой пр-д, 5Ак1",
     "kf.expert, cian.ru: БЦ Фили Град, класс A"),
    ("ул. Воронцовская, д. 49/28", "B", "Воронцовская ул., 49/28с1",
     "of.ru/bc/841: БЦ Воронцовская 49/28с1, класс B"),
    ("Парк Горького", "B", "Ленинский просп., 30А",
     "amo.ru, fortexgroup.ru: БЦ Ленинский 30А, класс B"),
    ("White Stone", "A", "4-й Лесной пер., 4",
     "kf.expert, of.ru/bc/white-stone: БЦ White Stone, класс A"),
    ("Проспект Мира, 40", "A", "просп. Мира, 40",
     "fortexgroup.ru/bc/garden-mir: Garden Mir, класс A"),
    ("Signature Столешников, 11", "B+", "Столешников пер., 11",
     "kf.expert, fortexgroup.ru: БЦ Столешников 11 (Signature), класс B+"),
    ("на Басманной", "B", "Спартаковская пл., 16/15с6",
     "cian.ru, wikimetria.ru: БЦ На Спартаковской, класс B"),
    # --- четвёртая партия, 2026-08-19 (продолжение)
    ("Фабрика Станиславского", "B+", "ул. Станиславского, 21с1",
     "cian.ru, fortexgroup.ru: БЦ Фабрика Станиславского, класс B+"),
    ("Большая Якиманка 26", "A", "Б. Якиманка ул., 26",
     "kf.expert, brightrich.moscow: БЦ Якиманка 26, класс A"),
    ("Poklonka Place", "A", "Поклонная ул., 3",
     "manufaqtury.com: БЦ Поклонка под управлением MANUFAQTURY, класс A (MRF 2024)"),
    ("Ролл Холл", "B", "Холодильный пер., 3",
     "cian.ru: ТРЦ Ролл Холл, офисные помещения классов B/B+, класс B"),
    ("Аркус 3", "A", "Ленинградский просп., 37А стр.4",
     "kf.expert: БЦ Аркус III, класс A"),
    # --- пятая партия, 2026-08-19 (финальный проход по надёжным источникам)
    ("ФОК", "B", "Новорязанская ул., 8Ас2",
     "cremap.pro, 2gis.ru: Workki ФОК (Union Center), класс B"),
    ("ВТБ Арена стр 8", "A", "Ленинградский просп., 36с41",
     "kf.expert, of.ru/bc/3295: ВТБ Арена Парк, корп.8, класс A"),
    ("SOK Рыбаков Тауэр", "A", "Ленинградский пр-т, вл. 36 стр. 11",
     "2gis.ru, mega-realty.ru: SOK Рыбаков Тауэр, класс A (тот же адрес, что и подтверждённый ранее SOK Южный блок)"),
    ("SOK Арена Парк", "A", "Ленинградский пр-т, вл. 36 стр. 10",
     "kf.expert: та же территория ВТБ Арена Парк класса A, что и корп.8/стр.11 — единый девелопмент"),
    # --- шестая партия, 2026-08-19 (продолжение по 13 оставшимся)
    ("Вивальди", "A", "Летниковская ул., 2 стр.1",
     "kovorkingi.ru, officenavigator.ru: Вивальди Плаза, класс A"),
    ("Дубинин Скай", "Prime", "Дубининская ул., 39-41",
     "brightrich.moscow, dubinin-sky-bc.ru: БЦ Dubinin'Sky, класс Prime (строится, год постройки 2026)"),
    ("Газетный 17", "A", "Газетный пер., 17",
     "kf.expert, gazetniy-17.ru: БЦ Газетный 17, класс A"),
    ("Кадашевская наб., 6", "B", "Кадашевская наб., 6",
     "kf.expert, ayle.ru: CODE Якиманка, класс B"),
]


def current_host_coordinates() -> dict:
    rows = json.loads((ROOT / "data" / "coworking_202606.json").read_text(encoding="utf-8-sig"))
    grouped = {}
    for row in rows:
        if row.get("bc") and row.get("lat") is not None and row.get("lng") is not None:
            grouped.setdefault(row["bc"], []).append(row)
    result = {}
    for bc, matches in grouped.items():
        points = {(r["lat"], r["lng"]) for r in matches}
        if len(points) == 1:
            lat, lng = next(iter(points))
            ids = ",".join(str(r.get("id")) for r in matches)
            result[bc] = (lat, lng, f"coworking_202606.json id={ids}")
    result.update(HOST_COORDINATE_OVERRIDES)
    return result


def coordinate_note(bc: str, evidence: str) -> str:
    return (
        f"Координаты проверены {COORDINATE_RECHECK_DATE}: "
        f"data/{evidence}, точное совпадение здания-хоста по bc={bc!r}; "
        "адрес независимо подтверждён источниками класса, указанными выше. "
        "Не использовался поиск ближайшей точки."
    )


def all_coworking_observations():
    observations = []
    for path in sorted((ROOT / "data").glob("coworking_20*.json")):
        rows = json.loads(path.read_text(encoding="utf-8-sig"))
        for row in rows:
            item = dict(row)
            item["_source_file"] = path.name
            observations.append(item)
    return observations


def stable_historical_id(label):
    digest = hashlib.sha1(normalize_label(label).encode("utf-8")).hexdigest()[:10]
    return f"cwhost-hist-{digest}"


def historical_host_record(label, observations):
    override = HISTORICAL_HOST_OVERRIDES.get(label)
    usable = [
        row for row in observations
        if row.get("address") and row.get("lat") is not None and row.get("lng") is not None
    ]
    if override:
        address = override["address"]
        lat = override["latitude"]
        lng = override["longitude"]
        evidence = override["evidence"]
    elif usable:
        latest = max(usable, key=lambda row: (row["_source_file"], str(row.get("id"))))
        address, lat, lng = latest["address"], latest["lat"], latest["lng"]
        evidence = f"data/{latest['_source_file']} id={latest.get('id')}, exact bc={label!r}"
    else:
        return None

    project_id = stable_historical_id(label)
    return {
        "canonical_project_id": project_id,
        "canonical_building_id": f"{project_id}-bld",
        "entity_grain": "building",
        "entity_role": "host_building",
        "raw_name": label,
        "canonical_name": label,
        "flex_site_label": None,
        "aliases": HOST_ALIASES.get(label, []),
        "developer": None,
        "address": address,
        "latitude": lat,
        "longitude": lng,
        "geometry_quality": "geocoded_approx",
        "project_status": "Введён",
        "offer_status": "Не применяется",
        "offer_not_started_reason": None,
        "input_year": None,
        "input_quarter": None,
        "construction_start_year": None,
        "construction_start_quarter": None,
        "sales_start_year": None,
        "sales_start_quarter": None,
        "input_date_kind": "unknown",
        "cls": None,
        "gba": None,
        "gla": None,
        "office_area": None,
        "area_scope": "building",
        "zone": None,
        "submarket": None,
        "bizFormed": None,
        "bizForming": None,
        "market_channel": [],
        "observed_market_channels": ["coworking"],
        "source": "coworking_host_lookup",
        "source_date": COORDINATE_RECHECK_DATE,
        "verification_status": "under_review",
        "confidence": "medium",
        "external_only": False,
        "quarter_offer_refs": [],
        "quarter_offer_exists": False,
        "qa_status": "missing_required",
        "qa_notes": (
            f"Historical coworking host restored {COORDINATE_RECHECK_DATE}; source: {evidence}. "
            "Identity is based on exact bc, not nearest coordinates. Class/areas/dates remain missing until "
            f"two-source verification. {role_assignment_note('host_building')}"
        ),
        "public_visibility": "public",
        "first_seen_at": min(row["_source_file"][10:16] for row in observations),
        "last_verified_at": COORDINATE_RECHECK_DATE,
        "source_count": 1,
        "duplicate_of": None,
        "legacy_ids": [],
    }


def build_record(bc: str, cls: str, address: str, evidence: str, seq: int,
                 coordinates: tuple) -> dict:
    lat, lng, coordinate_evidence = coordinates
    return {
        "canonical_project_id": f"cwhost-{seq:04d}",
        "canonical_building_id": f"cwhost-{seq:04d}-bld",
        "entity_grain": "building",
        "entity_role": "host_building",
        "raw_name": bc,
        "canonical_name": bc,
        "flex_site_label": None,
        "aliases": [],
        "developer": None,
        "address": address,
        "latitude": lat,
        "longitude": lng,
        "geometry_quality": "geocoded_approx",
        "project_status": "Введён",
        "offer_status": "Не применяется",
        "offer_not_started_reason": None,
        "input_year": None,
        "input_quarter": None,
        "construction_start_year": None,
        "construction_start_quarter": None,
        "sales_start_year": None,
        "sales_start_quarter": None,
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
        "observed_market_channels": ["coworking"],
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
                    f"продажи/аренды/коворкинга. Источник: {evidence}. "
                    f"{role_assignment_note('host_building')}",
        "public_visibility": "public",
        "first_seen_at": TODAY,
        "last_verified_at": TODAY,
        "source_count": 2,
        "duplicate_of": None,
        "legacy_ids": [],
    }


def main() -> int:
    with open(LAYER_PATH, encoding="utf-8") as f:
        layer = json.load(f)

    existing = {
        r["canonical_name"]: r for r in layer if r.get("source") == "coworking_host_lookup"
    }
    seq = sum(1 for r in layer if r.get("source") == "coworking_host_lookup") + 1
    coordinates = current_host_coordinates()
    observations = all_coworking_observations()
    added = []
    updated = []
    for bc, cls, address, evidence in HOSTS:
        if bc not in coordinates:
            raise ValueError(f"No unique current coordinate for coworking host {bc!r}")
        if bc in existing:
            record = existing[bc]
            record["entity_role"] = "host_building"
            role_note = role_assignment_note("host_building")
            if role_note not in (record.get("qa_notes") or ""):
                record["qa_notes"] = (record.get("qa_notes") or "").rstrip() + " " + role_note
            lat, lng, coordinate_evidence = coordinates[bc]
            record["latitude"] = lat
            record["longitude"] = lng
            record["geometry_quality"] = "geocoded_approx"
            record["last_verified_at"] = COORDINATE_RECHECK_DATE
            record["source_count"] = max(2, record.get("source_count") or 0)
            note = coordinate_note(bc, coordinate_evidence)
            if note not in (record.get("qa_notes") or ""):
                record["qa_notes"] = (record.get("qa_notes") or "").rstrip() + " " + note
            updated.append(record["canonical_project_id"])
        else:
            record = build_record(bc, cls, address, evidence, seq, coordinates[bc])
            record["qa_notes"] += " " + coordinate_note(bc, coordinates[bc][2])
            record["last_verified_at"] = COORDINATE_RECHECK_DATE
            layer.append(record)
            added.append(f"cwhost-{seq:04d}")
            seq += 1

    # Restore every historical Moscow host that has an address+coordinate
    # observation. Labels explicitly proven to be aliases are canonicalized
    # before grouping, so Porta is one building rather than two nearest points.
    existing_labels = {
        normalize_label(value)
        for record in layer if record.get("entity_role") == "host_building"
        for value in [record.get("canonical_name"), *(record.get("aliases") or [])]
        if value
    }
    grouped = {}
    for observation in observations:
        label = BC_CANONICAL_LABELS.get(normalize_label(observation.get("bc")), observation.get("bc"))
        if label:
            grouped.setdefault(normalize_label(label), {"label": label, "rows": []})["rows"].append(observation)
    historical_added = []
    for normalized, group in sorted(grouped.items()):
        if normalized in existing_labels:
            continue
        record = historical_host_record(group["label"], group["rows"])
        if record is None:
            continue
        layer.append(record)
        historical_added.append(record["canonical_project_id"])
        existing_labels.add(normalized)
        existing_labels.update(normalize_label(alias) for alias in record.get("aliases") or [])

    for record in layer:
        if record.get("entity_role") == "host_building" and record.get("canonical_name") in PREFERRED_BUILDING_IDS:
            record["canonical_building_id"] = PREFERRED_BUILDING_IDS[record["canonical_name"]]
        if str(record.get("canonical_project_id", "")).startswith("cwhost-hist-"):
            record["quarter_offer_refs"] = []
            record["quarter_offer_exists"] = False

    links, rejected = link_coworking_sites(layer, observations)
    linked = []
    for record in layer:
        if record.get("entity_role") != "coworking_site":
            continue
        link = links.get(record["canonical_project_id"])
        if link:
            record["canonical_building_id"] = link["canonical_building_id"]
            note = link_note(link)
            if note not in (record.get("qa_notes") or ""):
                record["qa_notes"] = ((record.get("qa_notes") or "").rstrip() + " " + note).strip()
            if "Building link blocked 2026-08-22" in (record.get("qa_notes") or ""):
                record["public_visibility"] = "public"
                record["verification_status"] = "accepted"
                record["qa_status"] = "duplicate_suspect" if record.get("duplicate_of") else "ok"
            linked.append(record["canonical_project_id"])
        else:
            record["canonical_building_id"] = None
            record["public_visibility"] = "internal_only"
            record["verification_status"] = "blocked"
            record["qa_status"] = "quarantine"
            reason = rejected.get(record["canonical_project_id"]) or rejected.get(normalize_label(record.get("flex_site_label"))) or "no safe host match"
            note = f"Building link blocked {COORDINATE_RECHECK_DATE}: {reason}; kept internal until two-source verification."
            if note not in (record.get("qa_notes") or ""):
                record["qa_notes"] = ((record.get("qa_notes") or "").rstrip() + " " + note).strip()

    channels_by_building = {}
    for record in layer:
        building_id = record.get("canonical_building_id")
        if building_id:
            channels_by_building.setdefault(building_id, set()).update(record.get("market_channel") or [])
    for record in layer:
        building_id = record.get("canonical_building_id")
        record["observed_market_channels"] = sorted(
            channels_by_building.get(building_id, set()) or set(record.get("market_channel") or [])
        )

    with open(LAYER_PATH, "w", encoding="utf-8") as f:
        json.dump(layer, f, ensure_ascii=False, indent=2)
    print(
        f"added confirmed {len(added)}: {added}; updated coordinates {len(updated)}: {updated}; "
        f"added historical {len(historical_added)}; linked sites {len(linked)}; unresolved {len(rejected)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
