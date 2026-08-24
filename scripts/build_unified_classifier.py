"""Build the complete historical classifier from the 705-project registry.

The merge is deliberately conservative: existing layer rows are linked only by
normalized name or exact normalized address. Ambiguous/weak matches are kept in
needs_review instead of silently merging buildings and projects.
"""
from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data" / "future_projects.json"
LAYER = ROOT / "data" / "all_projects_layer.json"
OUTPUT = ROOT / "data" / "unified_classifier.json"


def norm(value: object) -> str:
    text = unicodedata.normalize("NFKC", str(value or "")).lower().replace("ё", "е")
    return re.sub(r"[^a-zа-я0-9]+", "", text)


def address_key(value: object) -> str:
    return norm(value).replace("москва", "")


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def main() -> None:
    source = load(SOURCE)
    # The exporter keeps the 25 coordinate-less records in a separate array;
    # the unified classifier must include them too.
    projects = list(source["projects"])
    known_ids = {p.get("id") for p in projects}
    projects.extend(p for p in source.get("no_coords", []) if p.get("id") not in known_ids)
    layer = load(LAYER)
    by_name: dict[str, list[dict]] = {}
    by_address: dict[str, list[dict]] = {}
    for row in layer:
        by_name.setdefault(norm(row.get("canonical_name") or row.get("raw_name")), []).append(row)
        key = address_key(row.get("address"))
        if key:
            by_address.setdefault(key, []).append(row)

    records = []
    classification_overrides = {
        "OBJ-0014": {
            "entity_type": "residential_complex_with_commercial_infrastructure",
            "classification_note": "Official Capital Group page describes Capital Towers as three residential skyscrapers; do not count as standalone office project without separate office-building evidence.",
        }
    }
    for project in projects:
        name_matches = by_name.get(norm(project.get("name")), [])
        addr_matches = by_address.get(address_key(project.get("address")), [])
        # The same row may arrive through both indexes, but two building rows
        # sharing one canonical_project_id must remain distinct/ambiguous.
        candidates = {id(r): r for r in name_matches + addr_matches}
        exact = list(candidates.values())
        match = exact[0] if len(exact) == 1 else None
        needs_review = len(exact) > 1 or not match
        override = classification_overrides.get(project.get("id"), {})
        records.append({
            # Source IDs are registry-stable; positional IDs would drift when a
            # row is inserted or the source export order changes.
            "unified_id": f"UC-{project.get('id')}",
            "source_id": project.get("id"),
            "name": project.get("name"),
            "address": project.get("address"),
            "developer": project.get("developer"),
            "gba": project.get("gba"),
            "gla": project.get("gla"),
            "cls": project.get("cls"),
            "commission_year": project.get("commission_year"),
            "commission_quarter": project.get("commission_quarter"),
            "status": project.get("status"),
            "latitude": project.get("lat"),
            "longitude": project.get("lng"),
            "coordinates_status": project.get("geometry_quality") or ("missing" if project.get("lat") is None else "unverified"),
            "legacy_ids": [match["canonical_project_id"]] if match else [],
            "quarter_offer_refs": (match or {}).get("quarter_offer_refs", []),
            "market_channel": (match or {}).get("market_channel", []),
            "layer_status": (match or {}).get("project_status"),
            "layer_offer_status": (match or {}).get("offer_status"),
            "layer_source": (match or {}).get("source"),
            "layer_source_date": (match or {}).get("source_date"),
            "layer_qa_notes": (match or {}).get("qa_notes"),
            "source_links": project.get("sources") or [],
            "verification_status": project.get("verification_status"),
            "confidence": project.get("confidence"),
            "entity_type": override.get("entity_type", "office_project_candidate"),
            "classification_note": override.get("classification_note"),
            "needs_review": needs_review or bool(override),
            "review_reason": "ambiguous layer match" if len(exact) > 1 else ("manual classification review" if override else ("no conservative layer match" if not match else None)),
        })

    output = {
        "schema_version": 1,
        "generated_by": "scripts/build_unified_classifier.py",
        "source_total": source.get("total"),
        "with_coordinates": source.get("with_coords"),
        "without_coordinates": source.get("without_coords"),
        "records": records,
    }
    OUTPUT.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {len(records)} records to {OUTPUT}")
    print(f"Needs review: {sum(r['needs_review'] for r in records)}")


if __name__ == "__main__":
    main()
