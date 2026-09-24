"""Apply the source-reviewed host-building area and year wave."""

import json
from pathlib import Path

from validate_all_projects_layer import validate


ROOT = Path(__file__).resolve().parents[1]
LAYER_PATH = ROOT / "data" / "all_projects_layer.json"
QA_PATH = ROOT / "data" / "qa" / "host_building_gap_fill_20260924.json"


def main():
    rows = json.loads(LAYER_PATH.read_text(encoding="utf-8"))
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
        if row.get("entity_role") != "host_building":
            raise ValueError(f"Gap-fill target is not a host building: {key}")
        for field, value in item["fields"].items():
            current = row.get(field)
            if current not in (None, value):
                raise ValueError(f"Unexpected {field} for {key}: {current!r}")
            row[field] = value
        row["input_date_kind"] = "confirmed"
        row["last_verified_at"] = qa["checked_on"]
        row["source_count"] = max(int(row.get("source_count") or 0), len(item["sources"]))
        note = (
            f" Host-building gaps verified {qa['checked_on']}: "
            f"{'; '.join(item['sources'])}. {item['note']}."
        )
        if note.strip() not in (row.get("qa_notes") or ""):
            row["qa_notes"] = (row.get("qa_notes") or "").rstrip() + note
        updated.append(key)

    missing = sorted(set(accepted) - set(updated))
    if missing:
        raise ValueError(f"Host-building targets not found: {missing}")
    errors = validate(rows)
    if errors:
        raise ValueError("Layer validation failed:\n" + "\n".join(errors))
    LAYER_PATH.write_text(json.dumps(rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"updated": len(updated), "targets": updated}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
