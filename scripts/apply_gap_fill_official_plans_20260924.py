"""Apply reviewed current commissioning plans for three office projects."""

import json
from pathlib import Path

from validate_all_projects_layer import validate


ROOT = Path(__file__).resolve().parents[1]
LAYER_PATH = ROOT / "data" / "all_projects_layer.json"
DATES_PATH = ROOT / "data" / "building_dates.json"
QA_PATH = ROOT / "data" / "qa" / "gap_fill_official_plans_20260924.json"


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
        row["input_quarter"] = item["input_quarter"]
        row["input_date_kind"] = "planned"
        row["last_verified_at"] = qa["checked_on"]
        note = (
            f" Current planned commissioning verified {qa['checked_on']}: {item['source']}."
        )
        if note.strip() not in (row.get("qa_notes") or ""):
            row["qa_notes"] = (row.get("qa_notes") or "").rstrip() + note
        updated.append(key)
    missing = sorted(set(accepted) - set(updated))
    if missing:
        raise ValueError(f"Official-plan targets not found: {missing}")

    k_city = next(row for row in rows if row.get("canonical_project_id") == "proj-136")
    k_city["input_year"] = None
    k_city["input_quarter"] = None
    k_city["input_date_kind"] = "unknown"
    k_city["last_verified_at"] = qa["checked_on"]
    k_city["qa_notes"] = (
        "entity_role=office_project assigned 2026-08-22; source: user decision to keep "
        "coworking_site and host_building as distinct public entities. Input date conflict "
        "rechecked 2026-09-24 and retained: current official project page gives Q2 2028 "
        "(https://kobzon.city/; earlier route https://kobzon.city/team), while RBC reports "
        "Q4 2028 (https://realty.rbc.ru/amp/news/68871e7b9a7947fdd81a8716). "
        "No value selected until the conflict is resolved."
    )

    date_keys = {"proj-164": "one tower", "proj-204": "top tower"}
    for item in qa["accepted"]:
        key = date_keys[item["canonical_project_id"]]
        record = dates.setdefault(key, {})
        record["canonical_project_id"] = item["canonical_project_id"]
        record.setdefault("canonical_building_id", None)
        record.setdefault("construction_start_q", None)
        record.setdefault("start_q", None)
        record["commission_q"] = (
            f"{item['input_year']}{item['input_quarter'] * 3:02d}"
            if item["input_quarter"] else None
        )
        record["commission_year"] = item["input_year"]
        record["source"] = f"Current project/developer source: {item['source']}"
        record["last_checked"] = qa["checked_on"]

    k_city_date = dates["k-city"]
    k_city_date["commission_q"] = None
    k_city_date.pop("commission_year", None)
    k_city_date["source"] = (
        "Unresolved commissioning conflict: official https://kobzon.city/ says Q2 2028; "
        "https://realty.rbc.ru/amp/news/68871e7b9a7947fdd81a8716 says Q4 2028."
    )
    k_city_date["last_checked"] = qa["checked_on"]

    errors = validate(rows)
    if errors:
        raise ValueError("Layer validation failed:\n" + "\n".join(errors))
    LAYER_PATH.write_text(json.dumps(rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    DATES_PATH.write_text(json.dumps(dates, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"updated": len(updated), "targets": updated}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
