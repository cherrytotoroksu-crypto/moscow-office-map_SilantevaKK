"""Fill Silver Fountain office GLA from the current asset-manager disclosure."""

import json
from pathlib import Path

from validate_all_projects_layer import validate


ROOT = Path(__file__).resolve().parents[1]
LAYER = ROOT / "data" / "all_projects_layer.json"
CLASSIFIER = ROOT / "data" / "unified_classifier_audited_2026-08-27.json"
QA = ROOT / "data" / "qa" / "silver_fountain_gla_fill_20260926.json"


def main():
    rows = json.loads(LAYER.read_text(encoding="utf-8"))
    classifier = json.loads(CLASSIFIER.read_text(encoding="utf-8"))
    qa = json.loads(QA.read_text(encoding="utf-8"))
    row = next(r for r in rows if r.get("canonical_project_id") == "proj-20")
    current = {"gla": row.get("gla")}
    if current not in (qa["before"], qa["after"]):
        raise ValueError(f"Unexpected proj-20 state: {current!r}")
    row.update(qa["after"])
    row.update({"confidence": "high", "last_verified_at": qa["checked_on"]})
    row["source_count"] = max(int(row.get("source_count") or 0), 2)
    urls = [source["url"] for source in qa["sources"]]
    note = (
        " Silver Fountain GLA verified 2026-09-26: current asset-manager page "
        "states 18,717 sqm rentable office area as of 2026-04-30. The stale "
        "classifier value 13,804 sqm is superseded. Precise registry GBA 21,403 "
        "sqm is retained instead of the developer's rounded 21,700 sqm; корпус "
        "1 / корпус 5 address conflict remains unresolved. Sources: "
        + ", ".join(urls) + "."
    )
    if note.strip() not in row.get("qa_notes", ""):
        row["qa_notes"] = row.get("qa_notes", "").rstrip() + note

    unified = next(r for r in classifier["records"] if r.get("unified_id") == "UC-OBJ-0058")
    if unified.get("gla") not in (13804.0, 18717.0):
        raise ValueError(f"Unexpected UC-OBJ-0058 GLA: {unified.get('gla')!r}")
    unified.update({
        "gla": 18717.0,
        "commission_year": 2025,
        "commission_quarter": None,
        "status": "Сданный",
        "layer_status": "Введён",
        "source_links": urls,
        "verification_status": "Current asset-manager disclosure verified",
        "confidence": "Высокий",
        "needs_review": True,
        "review_reason": "address_corpus_1_vs_5",
    })
    addition = (
        "2026-09-26: current asset manager reports 18,717 sqm rentable office "
        "area as of 2026-04-30; address corpus discrepancy remains under review."
    )
    if addition not in (unified.get("classification_note") or ""):
        unified["classification_note"] = ((unified.get("classification_note") or "").rstrip() + " " + addition).strip()

    errors = validate(rows)
    if errors:
        raise ValueError("Layer validation failed:\n" + "\n".join(errors))
    LAYER.write_text(json.dumps(rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    CLASSIFIER.write_text(json.dumps(classifier, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"updated": "proj-20", "gla": 18717.0}, ensure_ascii=False))


if __name__ == "__main__":
    main()
