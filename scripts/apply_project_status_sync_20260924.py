"""Synchronize stale lifecycle statuses with confirmed commissioning evidence."""

import json
from pathlib import Path

from validate_all_projects_layer import validate


ROOT = Path(__file__).resolve().parents[1]
LAYER_PATH = ROOT / "data" / "all_projects_layer.json"
QA_PATH = ROOT / "data" / "qa" / "project_status_sync_20260924.json"


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
        if row.get("entity_role") != "office_project":
            raise ValueError(f"Status sync target is not an office project: {key}")
        if row.get("input_date_kind") != "confirmed" or not row.get("input_year"):
            raise ValueError(f"Status sync target lacks confirmed commissioning: {key}")
        if row.get("project_status") not in {item["from"], item["to"]}:
            raise ValueError(f"Unexpected status for {key}: {row.get('project_status')!r}")

        row["project_status"] = item["to"]
        note = (
            f" Lifecycle status synchronized {qa['checked_on']} with confirmed "
            f"commissioning evidence: {item['source']}."
        )
        if note.strip() not in (row.get("qa_notes") or ""):
            row["qa_notes"] = (row.get("qa_notes") or "").rstrip() + note
        updated.append(key)

    missing = sorted(set(accepted) - set(updated))
    if missing:
        raise ValueError(f"Status sync targets not found: {missing}")

    errors = validate(rows)
    if errors:
        raise ValueError("Layer validation failed:\n" + "\n".join(errors))
    LAYER_PATH.write_text(json.dumps(rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"updated": len(updated), "targets": updated}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
