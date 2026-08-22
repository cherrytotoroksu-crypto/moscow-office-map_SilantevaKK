"""Idempotently assign explicit entity roles to the current registry."""
import json
from pathlib import Path

from all_projects_entity_roles import derive_entity_role, role_assignment_note
from validate_all_projects_layer import validate


ROOT = Path(__file__).resolve().parents[1]
LAYER_PATH = ROOT / "data" / "all_projects_layer.json"


def main():
    records = json.loads(LAYER_PATH.read_text(encoding="utf-8-sig"))
    counts = {}
    for record in records:
        role = derive_entity_role(record.get("source"), record.get("market_channel"))
        record["entity_role"] = role
        note = role_assignment_note(role)
        if note not in (record.get("qa_notes") or ""):
            record["qa_notes"] = ((record.get("qa_notes") or "").rstrip() + " " + note).strip()
        counts[role] = counts.get(role, 0) + 1
    errors = validate(records)
    if errors:
        raise ValueError("entity-role migration produced invalid data:\n" + "\n".join(errors))
    LAYER_PATH.write_text(json.dumps(records, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"records": len(records), "roles": counts}, ensure_ascii=False))


if __name__ == "__main__":
    main()
