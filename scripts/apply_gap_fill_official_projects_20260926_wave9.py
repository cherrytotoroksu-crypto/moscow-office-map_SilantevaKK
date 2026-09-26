"""Apply the ninth reviewed wave of office-project lifecycle dates."""

import json
from pathlib import Path

from validate_all_projects_layer import validate


ROOT = Path(__file__).resolve().parents[1]
LAYER_PATH = ROOT / "data" / "all_projects_layer.json"
DATES_PATH = ROOT / "data" / "building_dates.json"
CLASSIFIER_PATH = ROOT / "data" / "unified_classifier_audited_2026-08-27.json"
QA_PATH = ROOT / "data" / "qa" / "gap_fill_official_projects_20260926_wave9.json"


def apply_expected(record, before, after, label):
    current = {key: record.get(key) for key in before}
    if current not in (before, after):
        raise ValueError(f"Unexpected state for {label}: {current!r}")
    record.update(after)


def main():
    rows = json.loads(LAYER_PATH.read_text(encoding="utf-8"))
    dates = json.loads(DATES_PATH.read_text(encoding="utf-8"))
    classifier = json.loads(CLASSIFIER_PATH.read_text(encoding="utf-8"))
    qa = json.loads(QA_PATH.read_text(encoding="utf-8"))
    accepted = {item["canonical_project_id"]: item for item in qa["accepted"]}
    classifier_by_id = {
        row.get("unified_id"): row for row in classifier.get("records", [])
    }
    updated = []

    for row in rows:
        item = accepted.get(row.get("canonical_project_id"))
        if not item:
            continue
        apply_expected(row, item["before"], item["after"], item["canonical_project_id"])
        row["last_verified_at"] = qa["checked_on"]
        row["verification_status"] = "accepted"
        row["confidence"] = item["confidence"]
        row["source_count"] = len(item["sources"])
        note = (
            f" Gap fill verified {qa['checked_on']}: {item['decision']} "
            f"Sources: {', '.join(item['sources'])}."
        )
        if note.strip() not in (row.get("qa_notes") or ""):
            row["qa_notes"] = (row.get("qa_notes") or "").rstrip() + note
        updated.append(item["canonical_project_id"])

        date_key = item["building_date_key"]
        date_record = dates.setdefault(date_key, {})
        existing_project_id = date_record.get("canonical_project_id")
        if existing_project_id not in (None, item["canonical_project_id"]):
            raise ValueError(f"Unexpected canonical_project_id for {date_key!r}")
        date_record.setdefault("construction_start_q", None)
        date_record.setdefault("start_q", None)
        date_record["commission_q"] = item["commission_q"]
        date_record["commission_year"] = item["after"]["input_year"]
        date_record["source"] = "Verified sources: " + ", ".join(item["sources"])
        date_record["last_checked"] = qa["checked_on"]
        date_record["canonical_project_id"] = item["canonical_project_id"]
        date_record.setdefault("canonical_building_id", None)

        classifier_row = classifier_by_id.get(item["classifier_unified_id"])
        if classifier_row is None:
            raise ValueError(f"Classifier target not found: {item['classifier_unified_id']}")
        apply_expected(
            classifier_row,
            item["classifier_before"],
            item["classifier_after"],
            item["classifier_unified_id"],
        )
        classifier_row["source_links"] = item["sources"]
        classifier_row["verification_status"] = item["classifier_verification_status"]
        classifier_row["confidence"] = (
            "Высокий" if item["confidence"] == "high" else "Средний"
        )
        classifier_row["classification_note"] = item["classifier_classification_note"]
        classifier_row["layer_qa_notes"] = item["decision"]
        classifier_row["needs_review"] = item["classifier_needs_review"]
        classifier_row["review_reason"] = item["classifier_review_reason"]

    missing = sorted(set(accepted) - set(updated))
    if missing:
        raise ValueError(f"Ninth-wave targets not found: {missing}")

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
    print(json.dumps({"updated": len(updated), "targets": updated}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
