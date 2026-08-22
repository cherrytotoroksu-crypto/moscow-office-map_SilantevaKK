"""Apply cited address/scope fixes found during the unified-codifier audit."""
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
CHECKED = "2026-08-22"
PORTA_FILES = ("coworking_202509.json", "coworking_202512.json", "coworking_202603.json")
PORTA_ADDRESS = "Москва, Заречная улица, 2/1"
PORTA_POINT = (55.75048, 37.53953)
PORTA_NOTE = (
    "Исправлено 2026-08-22 по точному зданию, не по ближайшей точке: "
    "porta.moscow (официальный сайт БЦ, Заречная ул., вл. 2/1), "
    "arendator.ru/news/188612 (Multispace именно в БЦ Porta); координаты уже "
    "подтверждены независимой записью BusinessClub PORTA по тому же адресу."
)
ONEGIN_ADDRESS = "Москва, улица Малая Полянка, 2"
ONEGIN_NOTE = (
    "Адрес подтверждён 2026-08-22: pmg-office.ru (официальный сайт оператора) "
    "и cian.ru/coworking-servisnyj-ofis-pmg-onegin-71739."
)
CHELYABINSK_NOTE = (
    "Исключено из московского слоя 2026-08-22: официальный praktik.work/chelyabinsk "
    "и cian.ru/coworking-praktik-chelyabinsk-70101 подтверждают адрес Челябинск, "
    "ул. Коммуны, 87; московские координаты были ошибочными."
)


def load(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def append_note(row, note):
    if note not in (row.get("qa_notes") or ""):
        row["qa_notes"] = ((row.get("qa_notes") or "").rstrip() + " " + note).strip()


def fix_porta():
    changed = 0
    for filename in PORTA_FILES:
        path = DATA / filename
        rows = load(path)
        for row in rows:
            if row.get("name") != "Multispace Porta":
                continue
            row.setdefault("prev_address", row.get("address"))
            row.setdefault("prev_lat", row.get("lat"))
            row.setdefault("prev_lng", row.get("lng"))
            row["address"] = PORTA_ADDRESS
            row["lat"], row["lng"] = PORTA_POINT
            append_note(row, PORTA_NOTE)
            changed += 1
        save(path, rows)
    return changed


def fix_onegin():
    path = DATA / "coworking_202603.json"
    rows = load(path)
    changed = 0
    kept = []
    for row in rows:
        if row.get("name") == "Онегин PMG":
            row.setdefault("prev_address", row.get("address"))
            row["address"] = ONEGIN_ADDRESS
            append_note(row, ONEGIN_NOTE)
            changed += 1
    save(path, rows)
    return changed


def quarantine_chelyabinsk():
    source = DATA / "coworking_202503.json"
    rows = load(source)
    kept, removed = [], []
    for row in rows:
        if row.get("name") == "Челябинск" and row.get("bc") == "Коммуны, 87":
            item = dict(row)
            item["source_file"] = source.name
            item["out_of_scope"] = True
            item["city"] = "Челябинск"
            item["verified_address"] = "Челябинск, улица Коммуны, 87"
            item["qa_notes"] = CHELYABINSK_NOTE
            removed.append(item)
        else:
            kept.append(row)
    save(source, kept)
    quarantine_path = DATA / "coworking_out_of_scope.json"
    existing = load(quarantine_path) if quarantine_path.exists() else []
    by_key = {(row.get("source_file"), row.get("id")): row for row in existing}
    for row in removed:
        by_key[(row.get("source_file"), row.get("id"))] = row
    save(quarantine_path, list(by_key.values()))
    return len(removed)


def fix_registry_rows():
    path = DATA / "all_projects_layer.json"
    rows = load(path)
    changed = 0
    kept = []
    for row in rows:
        project_id = row.get("canonical_project_id")
        if project_id == "proj-79":
            row["address"] = PORTA_ADDRESS
            row["latitude"], row["longitude"] = PORTA_POINT
            append_note(row, PORTA_NOTE)
            changed += 1
        elif project_id == "proj-92":
            row["address"] = ONEGIN_ADDRESS
            append_note(row, ONEGIN_NOTE)
            changed += 1
        elif project_id == "proj-36":
            changed += 1
            continue
        kept.append(row)
    save(path, kept)
    return changed


def main():
    result = {
        "porta_rows": fix_porta(),
        "onegin_rows": fix_onegin(),
        "chelyabinsk_rows_quarantined": quarantine_chelyabinsk(),
        "registry_rows": fix_registry_rows(),
    }
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
