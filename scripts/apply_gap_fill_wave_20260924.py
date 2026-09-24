"""Apply the source-reviewed 2026-09-24 host-building year fill."""
from __future__ import annotations

import json
from pathlib import Path

from validate_all_projects_layer import validate


ROOT = Path(__file__).resolve().parents[1]
LAYER_PATH = ROOT / "data" / "all_projects_layer.json"
DECISIONS_PATH = ROOT / "data" / "qa" / "gap_fill_wave_20260924.json"
CHECKED_AT = "2026-09-24"


def append_note(record, note):
    if note not in (record.get("qa_notes") or ""):
        record["qa_notes"] = ((record.get("qa_notes") or "").rstrip() + " " + note).strip()


def apply(layer, decisions):
    by_identity = {
        (row.get("canonical_project_id"), row.get("canonical_building_id")): row
        for row in layer
    }
    changed = []
    for decision in decisions["accepted"]:
        key = (decision["canonical_project_id"], decision["canonical_building_id"])
        record = by_identity.get(key)
        if record is None:
            raise KeyError(f"missing target {key}")
        expected_year = decision["input_year"]
        current_year = record.get("input_year")
        if current_year not in (None, expected_year):
            raise ValueError(f"refusing to overwrite {key}: input_year={current_year}")
        if current_year is None:
            record["input_year"] = expected_year
            record["input_quarter"] = None
            record["input_date_kind"] = "confirmed"
            record["last_verified_at"] = CHECKED_AT
            record["source_count"] = max(2, record.get("source_count") or 0)
            append_note(
                record,
                f"Input year {expected_year} verified {CHECKED_AT} for this exact building/address; "
                f"sources: {'; '.join(decision['sources'])}. Exact quarter was not published and remains null.",
            )
            changed.append({"canonical_project_id": key[0], "canonical_building_id": key[1], "input_year": expected_year})
    return changed


def main():
    layer = json.loads(LAYER_PATH.read_text(encoding="utf-8-sig"))
    decisions = json.loads(DECISIONS_PATH.read_text(encoding="utf-8-sig"))
    changed = apply(layer, decisions)
    errors = validate(layer)
    if errors:
        raise ValueError("gap fill produced invalid layer:\n" + "\n".join(errors))
    LAYER_PATH.write_text(json.dumps(layer, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"changed": changed, "count": len(changed)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
