"""Replace the White Square placeholder with a source-backed building point."""
import json
from pathlib import Path

from recompute_geo import compute_geo
from validate_all_projects_layer import validate


ROOT = Path(__file__).resolve().parents[1]
LAYER = ROOT / "data" / "all_projects_layer.json"
UNIFIED = ROOT / "data" / "unified_classifier_audited_2026-08-27.json"
PROJECT_ID = "cwhost-hist-5d45ac8941"
UNIFIED_ID = "UC-OBJ-ADD-328"
LAT = 55.7778039613667
LNG = 37.5866961479187
SOURCES = [
    "https://realty-guide.ru/offices/objects/2b78b525-795b-4f66-95c0-fc922719722a/",
    "https://yandex.com/maps/213/moscow/house/lesnaya_ulitsa_5/Z04Ycw9mQU0BQFtvfXt2dntrZw%3D%3D/",
]
NOTE = (
    " Placeholder coordinate replaced 2026-09-24 by the explicit GPS point published at "
    f"{SOURCES[0]}; {SOURCES[1]} independently corroborates the building point."
)


def apply():
    rows = json.loads(LAYER.read_text(encoding="utf-8"))
    row = next(row for row in rows if row.get("canonical_project_id") == PROJECT_ID)
    row.update({"latitude": LAT, "longitude": LNG, "geometry_quality": "house_exact", "confidence": "high"})
    computed = compute_geo(LAT, LNG)
    for field in ("zone", "submarket", "bizFormed", "bizForming"):
        row[field] = computed[field] or None
    notes = row.get("qa_notes") or ""
    notes = notes.replace(
        " Known placeholder coordinate 55.755819/37.617644 retained pending source-backed correction; derived geography deliberately left blank.",
        "",
    )
    if NOTE.strip() not in notes:
        notes = notes.rstrip() + NOTE
    row["qa_notes"] = notes
    errors = validate(rows)
    if errors:
        raise ValueError("layer validation failed:\n" + "\n".join(errors))
    LAYER.write_text(json.dumps(rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    payload = json.loads(UNIFIED.read_text(encoding="utf-8"))
    target = next(row for row in payload["records"] if row.get("unified_id") == UNIFIED_ID)
    target.update({"latitude": LAT, "longitude": LNG, "coordinates_status": "verified", "confidence": "high"})
    for field in ("ao", "raion", "zone", "submarket", "bizFormed", "bizForming"):
        target[f"geo_{field}"] = computed[field] or None
    target["source_links"] = list(dict.fromkeys((target.get("source_links") or []) + SOURCES))
    UNIFIED.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    apply()
