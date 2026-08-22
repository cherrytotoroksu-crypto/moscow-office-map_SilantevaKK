"""AUDIT-011 wave 02 (dates): STONE Пресня, PORTA — apply commission_q with
sources from data/qa/codifier_gap_wave_02_dates_20260822.json. Plaza
Technopark already correct (no-op, logged for traceability only).

Idempotent: re-running does not duplicate history, only updates if the
target value differs from what's already stored.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATES_PATH = ROOT / "data" / "building_dates.json"
EVIDENCE_PATH = ROOT / "data" / "qa" / "codifier_gap_wave_02_dates_20260822.json"
TODAY = "2026-08-22"


def main() -> int:
    dates = json.loads(DATES_PATH.read_text(encoding="utf-8-sig"))
    evidence = json.loads(EVIDENCE_PATH.read_text(encoding="utf-8"))

    applied = []
    for entry in evidence["entries"]:
        name = entry["name"]
        field = entry["field"]
        new_value = entry["new_value"]
        row = dates.setdefault(name, {
            "construction_start_q": None,
            "start_q": None,
            "commission_q": None,
            "source": None,
            "last_checked": None,
            "canonical_project_id": entry["canonical_project_id"],
            "canonical_building_id": None,
        })
        if row.get(field) == new_value and row.get("last_checked") == TODAY:
            continue  # already applied, idempotent no-op

        source_text = "; ".join(entry["sources"])
        if entry.get("conflict"):
            source_text += f" | КОНФЛИКТ: {entry['conflict_note']}"

        prev = row.get(field)
        row[field] = new_value
        row["source"] = source_text
        row["last_checked"] = TODAY
        row["canonical_project_id"] = entry["canonical_project_id"]
        if prev is not None and prev != new_value:
            row["prev_" + field] = prev
        applied.append(name)

    DATES_PATH.write_text(json.dumps(dates, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"applied/refreshed: {applied}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
