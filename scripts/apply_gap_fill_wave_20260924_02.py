"""Apply the second source-backed commissioning-year gap-fill wave."""
from __future__ import annotations

import json
from pathlib import Path

from validate_all_projects_layer import validate


ROOT = Path(__file__).resolve().parents[1]
LAYER_PATH = ROOT / "data" / "all_projects_layer.json"
DATES_PATH = ROOT / "data" / "building_dates.json"
QA_PATH = ROOT / "data" / "qa" / "gap_fill_wave_20260924_02.json"
CHECKED = "2026-09-24"


def load(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def append_note(row, note):
    if note not in (row.get("qa_notes") or ""):
        row["qa_notes"] = ((row.get("qa_notes") or "").rstrip() + " " + note).strip()


def apply():
    layer = load(LAYER_PATH)
    dates = load(DATES_PATH)
    qa = load(QA_PATH)
    by_id = {row.get("canonical_project_id"): row for row in layer}

    for decision in qa["accepted"]:
        row = by_id[decision["canonical_project_id"]]
        row["input_year"] = decision["input_year"]
        row["input_quarter"] = decision["input_quarter"]
        row["input_date_kind"] = "confirmed"
        row["last_verified_at"] = CHECKED
        row["source_count"] = max(2, row.get("source_count") or 0)
        append_note(
            row,
            f"Commissioning verified {CHECKED}: " + "; ".join(decision["sources"]) +
            (f". {decision['note']}" if decision.get("note") else "."),
        )

    dates["lunar"].update({
        "commission_q": None,
        "commission_year": 2023,
        "last_checked": CHECKED,
        "source": "lunar-center.ru reports the Lunar office building commissioned in 2023; MosPrimeOffice corroborates identity/address.",
    })
    dates["lakes"].update({
        "commission_q": "202603",
        "commission_year": 2026,
        "last_checked": CHECKED,
        "source": "Official FORMA Workplace news dated 2026-01-23 confirms the operating permit; current project page gives Q1 2026.",
    })

    errors = validate(layer)
    if errors:
        raise ValueError("second gap-fill wave produced invalid layer:\n" + "\n".join(errors))
    save(LAYER_PATH, layer)
    save(DATES_PATH, dates)
    return {"updated": len(qa["accepted"]), "ids": [item["canonical_project_id"] for item in qa["accepted"]]}


def main():
    print(json.dumps(apply(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
