"""Controlled sync, step 8: after the mapping report is clean, propagate the
classifier's `unified_id` onto the quarterly buildings_*.json layer for
EXACT_MATCH pairs only (never probable_match/conflict/new_record, per the
sync request's rule 7).

Does not call scripts/build_all_projects_layer.py (that rebuilds the whole
registry from scratch and wipes manually-added overlays - out of scope
here). This only adds/updates one field, `unified_id`, per building row,
using the SAME normalized-name matching as
scripts/build_classifier_registry_mapping.py, so linkage stays consistent
with the report.

Run: python scripts/apply_unified_id_to_buildings_layer.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from unified_building_identity import normalize_label  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
MAPPING_REPORT = ROOT / "outputs" / "classifier_registry_mapping_2026-08-30.json"
REGISTRY_PATH = ROOT / "data" / "all_projects_layer.json"
BUILDINGS_GLOB = "buildings_*.json"


def main():
    report = json.loads(MAPPING_REPORT.read_text(encoding="utf-8"))
    registry = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    registry_by_id = {r["canonical_project_id"]: r for r in registry}

    # normalized registry-name -> classifier unified_id, exact_match only
    name_to_unified_id = {}
    exact = [e for e in report if e["status"] == "exact_match"]
    for e in exact:
        reg = registry_by_id.get(e["matched_project_id"])
        if reg is None:
            continue
        for name_field in ("canonical_name", "raw_name"):
            v = reg.get(name_field)
            if v:
                name_to_unified_id[normalize_label(v)] = e["unified_id"]
        for alias in (reg.get("aliases") or []):
            name_to_unified_id[normalize_label(alias)] = e["unified_id"]

    print(f"exact_match linkable names: {len(name_to_unified_id)} "
          f"(from {len(exact)} exact_match rows)")

    total_rows = 0
    total_linked = 0
    for path in sorted((ROOT / "data").glob(BUILDINGS_GLOB)):
        if "pre_sync" in path.name:
            continue
        rows = json.loads(path.read_text(encoding="utf-8"))
        linked_here = 0
        for row in rows:
            uid = (
                name_to_unified_id.get(normalize_label(row.get("name")))
                or name_to_unified_id.get(normalize_label(row.get("name_orig")))
            )
            row["unified_id"] = uid  # explicit null for non-exact_match rows
            if uid:
                linked_here += 1
        path.write_text(json.dumps(rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        total_rows += len(rows)
        total_linked += linked_here
        print(f"  {path.name}: {linked_here}/{len(rows)} rows linked")

    print(f"\ntotal: {total_linked}/{total_rows} building rows linked to a classifier unified_id")


if __name__ == "__main__":
    main()
