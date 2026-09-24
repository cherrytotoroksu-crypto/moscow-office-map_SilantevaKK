"""Remove the one unified-classifier geography value that fails recomputation."""
import json
from pathlib import Path

from recompute_geo import compute_geo


ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / "data" / "unified_classifier_audited_2026-08-27.json"
TARGETS = {"UC-OBJ-0028", "UC-OBJ-ADD-354"}


def apply():
    payload = json.loads(PATH.read_text(encoding="utf-8"))
    rows = [row for row in payload["records"] if row.get("unified_id") in TARGETS]
    if {row.get("unified_id") for row in rows} != TARGETS:
        raise ValueError("expected unified classifier rows were not found")
    for row in rows:
        computed = compute_geo(row["latitude"], row["longitude"])
        row["geo_submarket"] = computed["submarket"] or None
    PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    apply()
