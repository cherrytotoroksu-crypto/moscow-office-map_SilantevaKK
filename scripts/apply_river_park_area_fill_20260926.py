"""Apply official River Park building 12 areas without guessing its address."""

import json
from pathlib import Path

from validate_all_projects_layer import validate


ROOT = Path(__file__).resolve().parents[1]
LAYER = ROOT / "data" / "all_projects_layer.json"
BUILDINGS = ROOT / "data" / "buildings_202606.json"
CLASSIFIER = ROOT / "data" / "unified_classifier_audited_2026-08-27.json"
DATES = ROOT / "data" / "building_dates.json"
QA = ROOT / "data" / "qa" / "river_park_area_fill_20260926.json"


def checked_update(record, before, after, label):
    current = {key: record.get(key) for key in before}
    if current not in (before, after):
        raise ValueError(f"Unexpected state for {label}: {current!r}")
    record.update(after)


def main():
    rows = json.loads(LAYER.read_text(encoding="utf-8"))
    buildings = json.loads(BUILDINGS.read_text(encoding="utf-8"))
    classifier = json.loads(CLASSIFIER.read_text(encoding="utf-8"))
    dates = json.loads(DATES.read_text(encoding="utf-8"))
    qa = json.loads(QA.read_text(encoding="utf-8"))
    before, after = qa["before"], qa["after"]
    urls = [source["url"] for source in qa["sources"]]

    row = next(r for r in rows if r.get("canonical_project_id") == "proj-279")
    checked_update(row, before, after, "all_projects proj-279")
    row.update({"project_status": "Введён", "input_year": 2026,
                "input_quarter": 2, "input_date_kind": "confirmed",
                "confidence": "high", "last_verified_at": qa["checked_on"]})
    row["source_count"] = max(int(row.get("source_count") or 0), 2)
    note = (
        " River Park areas verified 2026-09-26 for office building 12: official "
        "commissioning permit 77-05-013108-2026 states GBA 10,800.0 sqm and "
        "office-block area 8,243.8 sqm. Registry address 3A conflicts with the "
        "commissioned address 2 and remains unchanged pending separate address "
        "reconciliation. Sources: " + ", ".join(urls) + "."
    )
    if note.strip() not in row.get("qa_notes", ""):
        row["qa_notes"] = row.get("qa_notes", "").rstrip() + note

    building = next(b for b in buildings if b.get("id") == 279)
    checked_update(building, before, after, "buildings_202606 id=279")
    building.update({"status": "Введён", "year": 2026})

    unified = next(r for r in classifier["records"] if r.get("unified_id") == "UC-OBJ-ADD-001")
    checked_update(unified, before, after, "classifier UC-OBJ-ADD-001")
    unified.update({
        "commission_year": 2026,
        "commission_quarter": 2,
        "status": "Сданный",
        "layer_status": "Введён",
        "source_links": urls,
        "verification_status": "Official building 12 commissioning permit verified",
        "confidence": "Высокий",
        "needs_review": True,
        "review_reason": "commissioned_address_conflict_3A_vs_2",
    })
    classification_note = (
        "2026-09-26: official permit confirms building 12 GBA 10,800.0 sqm and "
        "office-block area 8,243.8 sqm; address conflict remains under review."
    )
    if classification_note not in unified.get("classification_note", ""):
        unified["classification_note"] = (
            unified.get("classification_note", "").rstrip() + " " + classification_note
        ).strip()

    date_record = dates.setdefault("river park коломенское", {})
    date_record.update({
        "construction_start_q": date_record.get("construction_start_q"),
        "start_q": date_record.get("start_q"),
        "commission_q": "202604",
        "commission_year": 2026,
        "source": "Official sources: " + ", ".join(urls),
        "last_checked": qa["checked_on"],
        "canonical_project_id": "proj-279",
        "canonical_building_id": None,
    })

    errors = validate(rows)
    if errors:
        raise ValueError("Layer validation failed:\n" + "\n".join(errors))
    for path, payload in ((LAYER, rows), (BUILDINGS, buildings),
                          (CLASSIFIER, classifier), (DATES, dates)):
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"updated": "proj-279", **after}, ensure_ascii=False))


if __name__ == "__main__":
    main()
