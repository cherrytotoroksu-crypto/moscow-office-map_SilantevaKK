"""Replace obsolete ALCON III concept areas with the current official project scope."""

import json
from pathlib import Path

from validate_all_projects_layer import validate


ROOT = Path(__file__).resolve().parents[1]
LAYER = ROOT / "data" / "all_projects_layer.json"
CLASSIFIER = ROOT / "data" / "unified_classifier_audited_2026-08-27.json"
DATES = ROOT / "data" / "building_dates.json"
QA = ROOT / "data" / "qa" / "alcon3_current_project_recheck_20260926.json"


def main():
    rows = json.loads(LAYER.read_text(encoding="utf-8"))
    classifier = json.loads(CLASSIFIER.read_text(encoding="utf-8"))
    dates = json.loads(DATES.read_text(encoding="utf-8"))
    qa = json.loads(QA.read_text(encoding="utf-8"))
    row = next(r for r in rows if r.get("canonical_project_id") == "proj-95")
    keys = qa["before"].keys()
    current = {key: row.get(key) for key in keys}
    if current not in (qa["before"], qa["after"]):
        raise ValueError(f"Unexpected proj-95 state: {current!r}")
    row.update(qa["after"])
    row.update({"confidence": "high", "last_verified_at": qa["checked_on"]})
    row["source_count"] = max(int(row.get("source_count") or 0), 2)
    urls = [source["url"] for source in qa["sources"]]
    note = (
        " ALCON III scope rechecked 2026-09-26: current official developer page "
        "identifies one eight-storey office building with GBA 35,865 sqm. The "
        "old 53,104 sqm mixed-use concept area is superseded. GLA stays null: "
        "legacy 10,500 and earlier-phase 10,155 sqm values are not confirmed by "
        "the current page. Q2 developer handover conflicts with the retained "
        "2023-07-14 permit evidence, so input_quarter stays null. Sources: "
        + ", ".join(urls) + "."
    )
    if note.strip() not in row.get("qa_notes", ""):
        row["qa_notes"] = row.get("qa_notes", "").rstrip() + note

    unified = next(r for r in classifier["records"] if r.get("unified_id") == "UC-OBJ-0012")
    expected = {"gba": 52624.0, "gla": 10500.0, "commission_quarter": 3}
    resolved = {"gba": 35865.0, "gla": None, "commission_quarter": None}
    current_unified = {key: unified.get(key) for key in expected}
    if current_unified not in (expected, resolved):
        raise ValueError(f"Unexpected UC-OBJ-0012 state: {current_unified!r}")
    unified.update(resolved)
    unified.update({
        "commission_year": 2023,
        "source_links": urls,
        "verification_status": "Current official ALCON III project scope verified",
        "confidence": "Высокий",
        "needs_review": True,
        "review_reason": "commission_quarter_q2_vs_q3",
    })
    addition = (
        "2026-09-26: current official project page confirms GBA 35,865 sqm; "
        "legacy GLA values cleared; Q2/Q3 commissioning conflict retained."
    )
    if addition not in (unified.get("classification_note") or ""):
        unified["classification_note"] = ((unified.get("classification_note") or "").rstrip() + " " + addition).strip()

    date_record = dates["алкон 3"]
    date_record["commission_year"] = 2023
    date_record["last_checked"] = qa["checked_on"]
    date_record["source"] = (
        date_record.get("source", "")
        + "; current official project page states Q2 2023: https://alcongroup.ru/projects/alcon-3; quarter conflict intentionally retained"
    ) if "alcongroup.ru/projects/alcon-3" not in date_record.get("source", "") else date_record["source"]

    errors = validate(rows)
    if errors:
        raise ValueError("Layer validation failed:\n" + "\n".join(errors))
    for path, payload in ((LAYER, rows), (CLASSIFIER, classifier), (DATES, dates)):
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"updated": "proj-95", "gba": 35865.0, "gla": None}, ensure_ascii=False))


if __name__ == "__main__":
    main()
