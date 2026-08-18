"""
Наполняет общий реестр (data/all_projects_layer.json) реальными данными из
classifier.html — шаг 1 рекомендованного порядка внедрения из
UNIFIED_DATA_ARCHITECTURE_2026-07-30.md.

ВАЖНО: это ЧТЕНИЕ classifier.html/data/buildings_*.json и запись НОВОГО
производного файла. classifier.html и квартальные файлы не меняются.

Что делается надёжно (прямое копирование уже проверенных полей):
  raw_name, canonical_name, developer, address, latitude, longitude, cls,
  gba, gla, zone, submarket, bizFormed, bizForming, market_channel,
  project_status (из status), input_year/input_quarter (из commission_q),
  quarter_offer_refs/quarter_offer_exists (вычислено сверкой со всеми
  data/buildings_*.json — не догадка, а проверка присутствия построчно).

Что ЯВЛЯЕТСЯ ЭВРИСТИКОЙ и помечается в qa_notes как «производное, требует
проверки» (не выдаётся за проверенный факт):
  offer_status (статус предложения) — правило по project_status +
  market_channel + quarter_offer_exists, см. функцию derive_offer_status();
  geometry_quality — по присутствию lat/lng в тире COLORMAP (green/yellow),
  иначе средний по умолчанию, а не факт отдельной перепроверки координаты;
  source/source_date — ссылка на classifier.html и дата запуска ЭТОГО
  скрипта, а не дата исходной проверки конкретного факта (та живёт в
  прозе NOTES и не извлекается автоматически).

Правила из задачи, реализованные явно:
  - Бадаевский — общий canonical_project_id='badaevsky', разные
    canonical_building_id для лент (не переиспользуется ни для чего другого).
  - out_of_scope (не Москва) — исключены из реестра совсем.
  - Дубли имён (12 известных коллизий) — НЕ объединяются; каждая строка
    RAW_DATA получает собственный canonical_project_id = f"proj-{old_id}".

⚠️ 2026-07-31: поля project_status/construction_status переименованы в
project_status (жизненный цикл)/offer_status (статус предложения) — эта
задача явно определила семантику наоборот тому, что было названо раньше.
Значение offer_status "Продажи завершены" переименовано в "Продано / снято".

⚠️ Известное ограничение: market_channel допускает 'serviced_office'
отдельно от 'coworking' (сервисный офис — Регус/WeWork/BusinessClub через
оператора, vs чистый коворкинг), но эта конвертация продолжает писать всё
как 'coworking' — в RAW_DATA/classifier.html нет структурного признака,
различающего их, а угадывать по названию оператора без доказательства
нельзя (см. правило "не исправляй данные без доказательства").
"""
import json
import os
import re
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_PATH = os.path.join(REPO_ROOT, "data", "all_projects_layer.json")
TODAY = "2026-07-31"

QUARTER_MONTH_TO_Q = {"03": 1, "06": 2, "09": 3, "12": 4}


def load_classifier():
    with open(os.path.join(REPO_ROOT, "classifier.html"), encoding="utf-8") as f:
        text = f.read()
    start = text.index("const RAW_DATA = [")
    open_idx = text.index("[", start)
    close_idx = text.rindex("]", open_idx, text.index("const COLORMAP = {"))
    raw_data = json.loads(text[open_idx:close_idx + 1])

    cm_start = text.index("const COLORMAP = {")
    cm_open = text.index("{", cm_start)
    depth = 0
    cm_close = None
    for i in range(cm_open, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                cm_close = i
                break
    colormap = json.loads(text[cm_open:cm_close + 1])
    return raw_data, colormap


def load_quarter_presence():
    """Для каждого имени здания — список кварталов (YYYYMM), где оно
    реально встречается в data/buildings_{quarter}.json ИЛИ
    data/coworking_{quarter}.json. Механическая сверка, не догадка.

    ⚠️ 2026-08-12: исправлен пропуск coworking-каналов — раньше сканировались
    только buildings_*.json, поэтому у ВСЕХ строк RAW_DATA с
    market_channel=coworking (напр. СODE Novo) quarter_offer_refs оставался
    пустым и quarter_offer_exists=false, даже если запись реально
    присутствует в coworking_{quarter}.json. Обнаружено при разборе
    подтверждённого пропуска Q2 2026 для СODE Novo (data/coworking_202606.json
    id=149)."""
    presence = {}
    data_dir = os.path.join(REPO_ROOT, "data")
    for fname in sorted(os.listdir(data_dir)):
        m = re.match(r"^buildings_(\d{6})\.json$", fname)
        if m:
            quarter = m.group(1)
            with open(os.path.join(data_dir, fname), encoding="utf-8-sig") as f:
                rows = json.load(f)
            for row in rows:
                for key in (row.get("name"), row.get("name_orig")):
                    if key:
                        presence.setdefault(key, set()).add(quarter)
            continue
        m = re.match(r"^coworking_(\d{6})\.json$", fname)
        if m:
            quarter = m.group(1)
            with open(os.path.join(data_dir, fname), encoding="utf-8-sig") as f:
                rows = json.load(f)
            for row in rows:
                key = row.get("name")
                if key:
                    presence.setdefault(key, set()).add(quarter)
    return presence


def commission_to_input(commission_q):
    if not commission_q or not re.match(r"^\d{6}$", str(commission_q)):
        return None, None
    year = int(str(commission_q)[:4])
    month = str(commission_q)[4:6]
    quarter = QUARTER_MONTH_TO_Q.get(month)
    return year, quarter


def derive_project_status(status):
    """Жизненный цикл (Проектируется/Строится/Введён/...) — из поля status."""
    if status == "Строится":
        return "Строится"
    if status == "Построен":
        return "Введён"
    return "Не установлен"  # коворкинг-операторы без собственного статуса стройки


def derive_market_channel(row):
    channels = []
    if row.get("sale"):
        channels.append("sale")
    if row.get("rent"):
        channels.append("rent")
    if row.get("coworking"):
        channels.append("coworking")
    return channels


def derive_offer_status(project_status, channels, quarter_offer_exists):
    """Статус предложения — ЭВРИСТИКА, см. docstring модуля. Не факт, а
    вычисленное приближение по project_status (жизненный цикл) +
    market_channel + quarter_offer_exists."""
    if not channels or channels == ["coworking"]:
        return "Не применяется", None
    if quarter_offer_exists:
        return "В продаже", None
    if project_status == "Введён":
        return "Продано / снято", None
    if project_status in ("Строится", "Проектируется"):
        return "Ещё не вышел в продажу", "Нет подтверждённых лотов"
    return "Не применяется", None


def derive_geometry_quality(name, colormap):
    green = colormap.get("green", {})
    yellow = colormap.get("yellow", {})
    if name in green and any(f in green[name] for f in ("lat", "lng")):
        return "house_exact"
    if name in yellow and any(f in yellow[name] for f in ("lat", "lng")):
        return "geocoded_approx"
    return "geocoded_approx"  # базовый уровень для давно существующих непровеченных заново записей


def derive_confidence_and_status(name, colormap):
    green = colormap.get("green", {})
    yellow = colormap.get("yellow", {})
    red = colormap.get("red", {})
    if name in red:
        return "low", "under_review"
    if name in green:
        return "high", "accepted"
    if name in yellow:
        return "medium", "accepted"
    return "medium", "accepted"  # давно существующая, не флагованная запись — не 'unverified' (это не новый внешний кандидат)


def derive_flex_site_label(name, name_orig):
    """Для гибких офисов имя строится как "<бренд/название площадки> (<site>)"
    — извлекаем именно <site> механически (по префиксу name_orig), а не
    регэкспом от конца строки. Регэксп на конце строки ломается, когда сам
    <site> тоже содержит скобки (напр. name_orig="SOK", name="SOK (SOK Сити
    (3 и 4 этаж))" — site="SOK Сити (3 и 4 этаж)"), поэтому раньше это поле
    не считалось вовсе. См. scripts/_tmp_join_key_audit_2026-08-12 (был найден
    как причина, почему codifier.html не сопоставлял ~58% coworking-строк с
    реестром — ключ строился как f"{network} ({bc})", а не по site-label)."""
    if not name or not name_orig:
        return None
    prefix = name_orig + " ("
    if name.startswith(prefix) and name.endswith(")"):
        return name[len(prefix):-1]
    return None


BADAEVSKY_IDS = {
    "Бадаевский Западная лента": ("badaevsky", "badaevsky-west", "building"),
    "Бадаевский Восточная лента": ("badaevsky", "badaevsky-east", "building"),
}

# Ручные уточнения по конкретному canonical_project_id (proj-{old_id}),
# переживающие regenerate — раньше applied как разовый патч JSON и
# терялись при каждом build_all_projects_layer.py (найдено в аудите
# 2026-08-14). canonical_project_id стабилен (= proj-{old_id}), поэтому
# ключ здесь — именно он, не raw_name (несколько строк могут делить имя).
EXTRA_BUILDING_ID = {
    "proj-149": "code-novo-dolgorukovskaya-21",  # СODE Novo, Долгоруковская 21
}
EXTRA_ALIASES = {
    "proj-149": ["CODE Novo", "Долгоруковская 21"],
}

# Технические дубли (аудит outputs/unified_codifier_review_decisions_2026-08-18.md,
# раздел "Уверенные технические дубли"): совпадают канал, девелопер и
# координата внутри группы — расхождения только в пунктуации/пробелах/
# пустом адресе или в диапазоне кварталов одного и того же места. Канонический
# ID в каждой группе — с наиболее полным адресом, при равенстве наименьший
# old_id. Легаси-строки НЕ удаляются: остаются в реестре с duplicate_of,
# их raw_name уходит в aliases канонической записи.
DUPLICATE_GROUPS = {
    "proj-9": ["proj-186", "proj-60", "proj-70"],
    "proj-17": ["proj-242", "proj-45"],
    "proj-28": ["proj-65"],
    "proj-29": ["proj-131"],
    "proj-30": ["proj-133"],
    "proj-31": ["proj-41"],
    "proj-47": ["proj-34"],
    "proj-46": ["proj-219"],
    "proj-50": ["proj-110"],
    "proj-63": ["proj-162"],
    "proj-64": ["proj-66"],
    "proj-68": ["proj-198"],
    "proj-75": ["proj-137"],
    "proj-78": ["proj-151"],
}


def convert_row(row, colormap, quarter_presence, warnings):
    name = row.get("name")
    name_orig = row.get("name_orig") or name
    old_id = row.get("old_id")

    if name_orig in BADAEVSKY_IDS:
        canonical_project_id, canonical_building_id, entity_grain = BADAEVSKY_IDS[name_orig]
        area_scope = "building"
    else:
        canonical_project_id = f"proj-{old_id}"
        canonical_building_id = EXTRA_BUILDING_ID.get(canonical_project_id)
        entity_grain = "project"
        area_scope = "project"

    project_status = derive_project_status(row.get("status"))
    channels = derive_market_channel(row)
    input_year, input_quarter = commission_to_input(row.get("commission_q"))

    refs = sorted(quarter_presence.get(name, set()) | quarter_presence.get(name_orig, set()))
    quarter_offer_exists = "202606" in refs

    offer_status, offer_reason = derive_offer_status(project_status, channels, quarter_offer_exists)
    geometry_quality = derive_geometry_quality(name, colormap)
    confidence, verification_status = derive_confidence_and_status(name, colormap)

    qa_notes = []
    if project_status == "Не установлен":
        qa_notes.append("Коворкинг-оператор без собственного статуса стройки — project_status/offer_status не применимы буквально.")
    qa_notes.append("offer_status и geometry_quality — производные значения (эвристика конвертации), не подтверждены отдельно; см. scripts/build_all_projects_layer.py.")

    has_area = any(row.get(k) is not None for k in ("gba", "gla"))
    qa_status = "ok"
    if has_area and area_scope == "unknown":
        qa_status = "conflict"

    return {
        "canonical_project_id": canonical_project_id,
        "canonical_building_id": canonical_building_id,
        "entity_grain": entity_grain,
        "raw_name": name_orig,
        "canonical_name": name,
        "flex_site_label": derive_flex_site_label(name, name_orig),
        "aliases": sorted(set(
            ([] if name == name_orig else [name_orig])
            + EXTRA_ALIASES.get(canonical_project_id, [])
        )),
        "developer": row.get("developer"),
        "address": row.get("address"),
        "latitude": row.get("lat"),
        "longitude": row.get("lng"),
        "geometry_quality": geometry_quality,
        "project_status": project_status,
        "offer_status": offer_status,
        "offer_not_started_reason": offer_reason,
        "input_year": input_year,
        "input_quarter": input_quarter,
        "input_date_kind": "confirmed" if project_status == "Введён" else ("planned" if input_year else "unknown"),
        "cls": row.get("cls"),
        "gba": row.get("gba"),
        "gla": row.get("gla"),
        "office_area": None,
        "area_scope": area_scope,
        "zone": row.get("zone") or None,
        "submarket": row.get("submarket") or None,
        "bizFormed": row.get("bizFormed") or None,
        "bizForming": row.get("bizForming") or None,
        "market_channel": channels,
        "source": "classifier.html",
        "source_date": TODAY,
        "verification_status": verification_status,
        "confidence": confidence,
        "external_only": False,
        "quarter_offer_refs": refs,
        "quarter_offer_exists": quarter_offer_exists,
        "qa_status": qa_status,
        "qa_notes": " ".join(qa_notes),
        "public_visibility": "public",
        "first_seen_at": min(refs) if refs else None,
        "last_verified_at": TODAY,
        "source_count": 1,
        "duplicate_of": None,
        "legacy_ids": [],
    }


def apply_duplicate_groups(records):
    """Проставляет duplicate_of/legacy_ids по DUPLICATE_GROUPS. Легаси-строки
    НЕ удаляются из records — остаются с duplicate_of, указывающим на
    каноническую запись; их raw_name уходит в aliases канонической записи."""
    by_id = {r["canonical_project_id"]: r for r in records}
    legacy_to_canonical = {
        legacy_id: canonical_id
        for canonical_id, legacy_ids in DUPLICATE_GROUPS.items()
        for legacy_id in legacy_ids
    }

    for canonical_id, legacy_ids in DUPLICATE_GROUPS.items():
        canonical = by_id[canonical_id]
        canonical["legacy_ids"] = sorted(legacy_ids, key=lambda x: int(x.split("-")[1]))
        extra_aliases = []
        for legacy_id in legacy_ids:
            legacy = by_id[legacy_id]
            for name in (legacy["raw_name"], legacy["canonical_name"]):
                if name and name != canonical["raw_name"] and name != canonical["canonical_name"]:
                    extra_aliases.append(name)
        if extra_aliases:
            canonical["aliases"] = sorted(set((canonical.get("aliases") or []) + extra_aliases))
        canonical["qa_notes"] = (
            canonical["qa_notes"]
            + f" Технический дубль объединён 2026-08-18 (unified_codifier_review_decisions): "
            f"{', '.join(legacy_ids)} — тот же канал/девелопер/координата, "
            f"расхождение только в адресе/пунктуации/диапазоне кварталов."
        ).strip()

    for legacy_id, canonical_id in legacy_to_canonical.items():
        legacy = by_id[legacy_id]
        legacy["duplicate_of"] = canonical_id
        legacy["qa_notes"] = (
            legacy["qa_notes"]
            + f" ОБЪЕДИНЕНО 2026-08-18: технический дубль {canonical_id}, "
            f"см. unified_codifier_review_decisions_2026-08-18.md — запись сохранена, "
            f"не удалена."
        ).strip()

    return records


def main():
    raw_data, colormap = load_classifier()
    quarter_presence = load_quarter_presence()

    excluded_out_of_scope = 0
    records = []
    warnings = []
    for row in raw_data:
        if row.get("out_of_scope"):
            excluded_out_of_scope += 1
            continue
        records.append(convert_row(row, colormap, quarter_presence, warnings))

    apply_duplicate_groups(records)

    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=2)

    project_counts = {}
    offer_counts = {}
    for r in records:
        project_counts[r["project_status"]] = project_counts.get(r["project_status"], 0) + 1
        offer_counts[r["offer_status"]] = offer_counts.get(r["offer_status"], 0) + 1
    conf_counts = {}
    for r in records:
        conf_counts[r["confidence"]] = conf_counts.get(r["confidence"], 0) + 1

    print(f"RAW_DATA rows: {len(raw_data)}")
    print(f"Excluded (out_of_scope, not Moscow): {excluded_out_of_scope}")
    print(f"Written records: {len(records)} -> {OUT_PATH}")
    print(f"project_status (жизненный цикл) breakdown: {project_counts}")
    print(f"offer_status (статус предложения) breakdown: {offer_counts}")
    print(f"confidence breakdown: {conf_counts}")
    print(f"Бадаевский: {sum(1 for r in records if r['canonical_project_id']=='badaevsky')} записи под общим canonical_project_id")
    print(f"Технические дубли: {len(DUPLICATE_GROUPS)} канонических записей, {sum(1 for r in records if r['duplicate_of'])} legacy-строк с duplicate_of")


if __name__ == "__main__":
    sys.exit(main())
