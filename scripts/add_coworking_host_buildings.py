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
