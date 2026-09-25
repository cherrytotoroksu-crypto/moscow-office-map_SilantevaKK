"""Apply the fourth reviewed wave of office-project dates and areas."""

import json
from pathlib import Path

from validate_all_projects_layer import validate


ROOT = Path(__file__).resolve().parents[1]
LAYER_PATH = ROOT / "data" / "all_projects_layer.json"
DATES_PATH = ROOT / "data" / "building_dates.json"
QA_PATH = ROOT / "data" / "qa" / "gap_fill_official_projects_20260925_wave4.json"


def main():
    rows = json.loads(LAYER_PATH.read_text(encoding="utf-8"))
    dates = json.loads(DATES_PATH.read_text(encoding="utf-8"))
    qa = json.loads(QA_PATH.read_text(encoding="utf-8"))
    accepted = {item["canonical_project_id"]: item for item in qa["accepted"]}
    updated = []

    for row in rows:
        item = accepted.get(row.get("canonical_project_id"))
        if not item:
            continue
        if row.get("canonical_name") != item["canonical_name"]:
            raise ValueError(
                f"Unexpected canonical_name for {item['canonical_project_id']}: "
                f"{row.get('canonical_name')!r}"
            )
        before = item["before"]
        after = item["after"]
        current = {key: row.get(key) for key in before}
        if current not in (before, after):
            raise ValueError(
                f"Unexpected state for {item['canonical_project_id']}: {current!r}"
            )
        row.update(after)
        row["last_verified_at"] = qa["checked_on"]
        note = (
            f" Gap fill verified {qa['checked_on']}: {item['decision']} "
            f"Sources: {', '.join(item['sources'])}."
        )
        if note.strip() not in (row.get("qa_notes") or ""):
            row["qa_notes"] = (row.get("qa_notes") or "").rstrip() + note
        updated.append(item["canonical_project_id"])

        date_key = item.get("building_date_key")
        if date_key:
            record = dates.setdefault(date_key, {})
            existing_project_id = record.get("canonical_project_id")
            if existing_project_id not in (None, item["canonical_project_id"]):
                raise ValueError(f"Unexpected canonical_project_id for {date_key!r}")
            record["canonical_project_id"] = item["canonical_project_id"]
            record.setdefault("canonical_building_id", None)
            record.setdefault("construction_start_q", None)
            record.setdefault("start_q", None)
            record["commission_q"] = None
            record["commission_year"] = after["input_year"]
            verification = "Verified sources: " + ", ".join(item["sources"])
            previous_source = item.get("building_date_source_before")
            target_source = (
                previous_source + " | RECHECKED 2026-09-25: " + verification
                if previous_source
                else verification
            )
            if record.get("source") not in (previous_source, target_source, verification):
                raise ValueError(f"Unexpected source history for {date_key!r}")
            record["source"] = target_source
            record["last_checked"] = qa["checked_on"]

    missing = sorted(set(accepted) - set(updated))
    if missing:
        raise ValueError(f"Fourth-wave targets not found: {missing}")

    errors = validate(rows)
    if errors:
        raise ValueError("Layer validation failed:\n" + "\n".join(errors))
    LAYER_PATH.write_text(
        json.dumps(rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    DATES_PATH.write_text(
        json.dumps(dates, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps({"updated": len(updated), "targets": updated}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
