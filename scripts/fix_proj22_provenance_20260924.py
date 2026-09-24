"""Remove foreign River Park provenance from proj-22 and record the real conflict."""

import json
from pathlib import Path

from validate_all_projects_layer import validate


ROOT = Path(__file__).resolve().parents[1]
LAYER_PATH = ROOT / "data" / "all_projects_layer.json"
TARGET_ID = "proj-22"
NOTE = (
    "entity_role=office_project assigned 2026-08-22; source: user decision to keep "
    "coworking_site and host_building as distinct public entities. Provenance corrected "
    "2026-09-24: the River Park commissioning note previously attached to this row belonged "
    "to proj-279 and was removed. The official Skolkovo directory identifies Большой бульвар, "
    "40 as БЦ «Амальтея» (https://sk.ru/transport/adresa-klyuchevyh-obektov/), while the "
    "classifier row represents an 8,500 m2 sale project with a different lifecycle. Developer, "
    "commissioning date and canonical-name changes remain unfilled until the building/offer "
    "grain is resolved; values for the full 78,000 m2 Amaltea complex must not be copied."
)


def main():
    rows = json.loads(LAYER_PATH.read_text(encoding="utf-8"))
    matches = [row for row in rows if row.get("canonical_project_id") == TARGET_ID]
    if len(matches) != 1:
        raise ValueError(f"Expected one {TARGET_ID} row, found {len(matches)}")
    row = matches[0]
    row["qa_notes"] = NOTE
    row["verification_status"] = "under_review"
    row["confidence"] = "low"
    row["qa_status"] = "conflict"
    row["last_verified_at"] = "2026-09-24"
    errors = validate(rows)
    if errors:
        raise ValueError("Layer validation failed:\n" + "\n".join(errors))
    LAYER_PATH.write_text(json.dumps(rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"updated": TARGET_ID, "qa_status": "conflict"}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
