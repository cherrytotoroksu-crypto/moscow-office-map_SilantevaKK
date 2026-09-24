"""Apply official STONE planned commissioning years without inventing quarters."""

import json
from pathlib import Path

from validate_all_projects_layer import validate


ROOT = Path(__file__).resolve().parents[1]
LAYER_PATH = ROOT / "data" / "all_projects_layer.json"
DATES_PATH = ROOT / "data" / "building_dates.json"
QA_PATH = ROOT / "data" / "qa" / "gap_fill_stone_20260924.json"


def main():
    rows = json.loads(LAYER_PATH.read_text(encoding="utf-8"))
    dates = json.loads(DATES_PATH.read_text(encoding="utf-8"))
    qa = json.loads(QA_PATH.read_text(encoding="utf-8"))
    accepted = {
        (item["canonical_project_id"], item["canonical_name"]): item
        for item in qa["accepted"]
    }
    updated = []
    for row in rows:
        key = (row.get("canonical_project_id"), row.get("canonical_name"))
        item = accepted.get(key)
        if not item:
            continue
        if row.get("input_year") not in (None, item["input_year"]):
            raise ValueError(f"Unexpected input_year for {key}: {row.get('input_year')!r}")
        row["input_year"] = item["input_year"]
        row["input_quarter"] = None
        row["input_date_kind"] = "planned"
        row["last_verified_at"] = qa["checked_on"]
        row["source_count"] = max(int(row.get("source_count") or 0), 1)
        note = (
            f" Planned readiness year verified {qa['checked_on']} on the official "
            f"developer page: {item['source']}; quarter is not published and remains null."
        )
        if note.strip() not in (row.get("qa_notes") or ""):
            row["qa_notes"] = (row.get("qa_notes") or "").rstrip() + note
        updated.append(key)
    missing = sorted(set(accepted) - set(updated))
    if missing:
        raise ValueError(f"STONE targets not found: {missing}")

    date_updates = {
        "stone мневники i": ("proj-185", 2028, "https://stone.ru/commercial/mnevniki"),
        "stone мневники ii": ("proj-188", 2029, "https://stone.ru/commercial/mnevniki"),
        "stone мневники iii": ("proj-189", 2030, "https://stone.ru/commercial/mnevniki3"),
        "stone римская": ("proj-192", 2028, "https://stone.ru/commercial/rimskaya"),
    }
    for key, (project_id, year, source) in date_updates.items():
        record = dates.setdefault(key, {})
        record["canonical_project_id"] = project_id
        record.setdefault("canonical_building_id", None)
        record.setdefault("construction_start_q", None)
        record.setdefault("start_q", None)
        record["commission_q"] = None
        record["commission_year"] = year
        record["source"] = f"Official STONE project page: {source}"
        record["last_checked"] = qa["checked_on"]

    errors = validate(rows)
    if errors:
        raise ValueError("Layer validation failed:\n" + "\n".join(errors))
    LAYER_PATH.write_text(json.dumps(rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    DATES_PATH.write_text(json.dumps(dates, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"updated": len(updated), "targets": updated}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
