"""Apply commissioning plans verified on current project pages."""

import json
from pathlib import Path

from validate_all_projects_layer import validate


ROOT = Path(__file__).resolve().parents[1]
LAYER_PATH = ROOT / "data" / "all_projects_layer.json"
DATES_PATH = ROOT / "data" / "building_dates.json"
QA_PATH = ROOT / "data" / "qa" / "gap_fill_official_projects_20260925.json"


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
                f"Unexpected date state for {item['canonical_project_id']}: {current!r}"
            )
        row.update(after)
        row["last_verified_at"] = qa["checked_on"]
        row["source_count"] = max(
            int(row.get("source_count") or 0),
            1 if item["reliability"] == "high" else 2,
        )
        source_list = ", ".join(item["sources"])
        note = (
            f" Commissioning plan verified {qa['checked_on']}: {item['decision']} "
            f"Sources: {source_list}."
        )
        if note.strip() not in (row.get("qa_notes") or ""):
            row["qa_notes"] = (row.get("qa_notes") or "").rstrip() + note
        updated.append(item["canonical_project_id"])

    missing = sorted(set(accepted) - set(updated))
    if missing:
        raise ValueError(f"Official-project targets not found: {missing}")

    date_keys = {
        "proj-147": "light city",
        "proj-267": "level нижегородская",
        "proj-273": "плэйн (бывший — workplace авиационная)",
    }
    for project_id, key in date_keys.items():
        item = accepted[project_id]
        after = item["after"]
        record = dates.setdefault(key, {})
        existing_project_id = record.get("canonical_project_id")
        if existing_project_id not in (None, project_id):
            raise ValueError(f"Unexpected canonical_project_id for date key {key!r}")
        record["canonical_project_id"] = project_id
        record.setdefault("canonical_building_id", None)
        record.setdefault("construction_start_q", None)
        record.setdefault("start_q", None)
        record["commission_q"] = (
            f"{after['input_year']}{after['input_quarter'] * 3:02d}"
            if after["input_quarter"]
            else None
        )
        record["commission_year"] = after["input_year"]
        record["source"] = "Verified sources: " + ", ".join(item["sources"])
        record["last_checked"] = qa["checked_on"]

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
