"""Resolve the duplicate LUNAR Module B rows from official HUTTON evidence."""

import json
from pathlib import Path

from validate_all_projects_layer import validate


ROOT = Path(__file__).resolve().parents[1]
LAYER_PATH = ROOT / "data" / "all_projects_layer.json"
DATES_PATH = ROOT / "data" / "building_dates.json"
CLASSIFIER_PATH = ROOT / "data" / "unified_classifier_audited_2026-08-27.json"
QA_PATH = ROOT / "data" / "qa" / "lunar_duplicate_resolution_20260926.json"


def _assert_state(record, expected_before, expected_after, label):
    current = {key: record.get(key) for key in expected_before}
    before = {key: expected_before[key] for key in expected_before}
    after = {key: expected_after[key] for key in expected_before}
    if current not in (before, after):
        raise ValueError(f"Unexpected state for {label}: {current!r}")


def _append_note(record, note):
    notes = (record.get("qa_notes") or "").rstrip()
    if note not in notes:
        record["qa_notes"] = f"{notes} {note}".strip()


def main():
    rows = json.loads(LAYER_PATH.read_text(encoding="utf-8"))
    dates = json.loads(DATES_PATH.read_text(encoding="utf-8"))
    classifier = json.loads(CLASSIFIER_PATH.read_text(encoding="utf-8"))
    qa = json.loads(QA_PATH.read_text(encoding="utf-8"))
    decision = qa["decision"]
    by_id = {row["canonical_project_id"]: row for row in rows}
    canonical = by_id[decision["canonical_project_id"]]
    duplicate = by_id[decision["duplicate_project_id"]]

    if (canonical.get("project_no"), canonical.get("subid")) != ("594", "01"):
        raise ValueError("Unexpected LUNAR canonical identity")
    for field in ("project_no", "subid", "address", "latitude", "longitude"):
        if duplicate.get(field) != canonical.get(field):
            raise ValueError(f"LUNAR rows differ on identity field {field}")

    before = decision["before"]
    after = decision["after"]
    _assert_state(duplicate, before["proj-14"], after["proj-14"], "proj-14")
    _assert_state(canonical, before["proj-80"], after["proj-80"], "proj-80")
    duplicate.update(after["proj-14"])
    canonical.update(after["proj-80"])

    urls = [source["url"] for source in decision["sources"]]
    note = (
        "LUNAR duplicate resolved 2026-09-26 from official HUTTON evidence: "
        "Module B commissioned in September 2024; GBA 13,431 sqm; official "
        "floor schedule totals 9,941.78 sqm of offices. proj-14 is the same "
        "project_no=594/subid=01 entity as canonical proj-80. Sources: "
        + ", ".join(urls)
        + "."
    )
    for row in (duplicate, canonical):
        row["input_date_kind"] = "confirmed"
        row["project_status"] = "Введён"
        row["verification_status"] = "accepted"
        row["confidence"] = "high"
        row["last_verified_at"] = qa["checked_on"]
        row["source_count"] = max(int(row.get("source_count") or 0), len(urls))
        _append_note(row, note)

    for key in ("lunar", "lunar модуль в"):
        record = dates[key]
        record["canonical_project_id"] = "proj-80"
        record["canonical_building_id"] = None
        record["commission_year"] = 2024
        record["commission_q"] = "202409"
        record["source"] = "Official HUTTON evidence: " + ", ".join(urls)
        record["last_checked"] = qa["checked_on"]

    classifier_row = next(
        row for row in classifier["records"] if row.get("unified_id") == "UC-OBJ-0745"
    )
    expected_classifier = {
        "gba": 13431.0,
        "gla": 10194.0,
        "commission_year": None,
        "commission_quarter": None,
        "legacy_ids": ["proj-80"],
        "needs_review": True,
        "review_reason": "ambiguous layer match",
    }
    resolved_classifier = {
        "gba": 13431.0,
        "gla": 9941.78,
        "commission_year": 2024,
        "commission_quarter": 3,
        "legacy_ids": ["proj-14", "proj-80"],
        "needs_review": False,
        "review_reason": None,
    }
    _assert_state(
        classifier_row, expected_classifier, resolved_classifier, "UC-OBJ-0745"
    )
    classifier_row.update(resolved_classifier)
    classifier_row["source_links"] = urls
    classifier_row["verification_status"] = (
        "Verified from official HUTTON project page, brochure and commissioning news"
    )
    classifier_row["confidence"] = "Высокий"
    classifier_note = (
        "2026-09-26: exact layer duplicate proj-14 merged into proj-80; official "
        "HUTTON evidence confirms Q3 2024 commissioning, GBA 13,431 sqm and "
        "9,941.78 sqm office area."
    )
    if classifier_note not in classifier_row.get("classification_note", ""):
        classifier_row["classification_note"] = (
            classifier_row.get("classification_note", "").rstrip()
            + " "
            + classifier_note
        ).strip()

    errors = validate(rows)
    if errors:
        raise ValueError("Layer validation failed:\n" + "\n".join(errors))
    LAYER_PATH.write_text(
        json.dumps(rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    DATES_PATH.write_text(
        json.dumps(dates, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    CLASSIFIER_PATH.write_text(
        json.dumps(classifier, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps({"canonical": "proj-80", "duplicate": "proj-14"}, ensure_ascii=False))


if __name__ == "__main__":
    main()
