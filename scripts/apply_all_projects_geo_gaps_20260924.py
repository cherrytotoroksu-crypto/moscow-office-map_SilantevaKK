"""Fill missing derived geography in the all-projects registry.

Only empty fields are populated. Existing curated values are never replaced.
The computation uses the same point-in-polygon layers and labels as the site.
"""

import json
from collections import Counter
from pathlib import Path

from recompute_geo import compute_geo
from validate_all_projects_layer import validate


ROOT = Path(__file__).resolve().parents[1]
LAYER_PATH = ROOT / "data" / "all_projects_layer.json"
QA_PATH = ROOT / "data" / "qa" / "all_projects_geo_fill_20260924.json"
FIELDS = ("zone", "submarket", "bizFormed", "bizForming")
KNOWN_PLACEHOLDER_COORDS = {(55.755819, 37.617644)}


def fill_geo_gaps(rows):
    field_counts = Counter()
    row_count = 0
    for row in rows:
        lat, lng = row.get("latitude"), row.get("longitude")
        if lat is None or lng is None:
            continue
        if (lat, lng) in KNOWN_PLACEHOLDER_COORDS:
            continue
        computed = compute_geo(lat, lng)
        changed = []
        for field in FIELDS:
            if row.get(field) in (None, "") and computed.get(field):
                row[field] = computed[field]
                field_counts[field] += 1
                changed.append(field)
        if changed:
            row_count += 1
            note = (
                " Geography gaps recomputed 2026-09-24 by point-in-polygon "
                f"from project GeoJSON layers: {', '.join(changed)}."
            )
            if note.strip() not in (row.get("qa_notes") or ""):
                row["qa_notes"] = (row.get("qa_notes") or "").rstrip() + note
    return {"rows_updated": row_count, "field_counts": dict(sorted(field_counts.items()))}


def main():
    rows = json.loads(LAYER_PATH.read_text(encoding="utf-8"))
    summary = fill_geo_gaps(rows)
    errors = validate(rows)
    if errors:
        raise ValueError("Layer validation failed:\n" + "\n".join(errors))
    LAYER_PATH.write_text(json.dumps(rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    report = {
        "checked_on": "2026-09-24",
        "method": "scripts/recompute_geo.py point-in-polygon; fill empty fields only",
        **summary,
    }
    QA_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
