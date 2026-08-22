"""Inventory and candidate matching for the unified project codifier.

Read-only: never rewrites source data. Produces a review queue, not IDs.
"""
from __future__ import annotations

import json
import re
import unicodedata
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
OUT = Path(__import__("os").environ.get("AUDIT_OUT", str(ROOT / "outputs")))


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def norm(value) -> str:
    s = unicodedata.normalize("NFKC", str(value or "")).lower().replace("ё", "е")
    s = re.sub(r"[«»\"'`“”„]", "", s)
    s = re.sub(r"[^0-9a-zа-я]+", " ", s, flags=re.I)
    return re.sub(r"\s+", " ", s).strip()


def names_from(path: Path):
    d = load(path)
    if isinstance(d, dict) and "projects" in d:
        d = d["projects"]
    if isinstance(d, dict):
        return list(d.keys())
    if isinstance(d, list):
        return [x.get("name") or x.get("canonical_name") or x.get("raw_name") for x in d]
    return []


def main():
    sources = {}
    for path in sorted(DATA.glob("*_20*.json")):
        if path.name == "building_dates.json":
            continue
        sources[path.name] = [x for x in names_from(path) if x]

    by_norm = defaultdict(list)
    for source, names in sources.items():
        for name in names:
            by_norm[norm(name)].append({"source": source, "name": name})

    exact_cross_source = []
    for key, rows in sorted(by_norm.items()):
        source_set = {r["source"] for r in rows}
        name_set = {r["name"] for r in rows}
        if key and len(source_set) > 1:
            exact_cross_source.append({"normalized": key, "names": sorted(name_set), "sources": sorted(source_set)})

    collisions = []
    for key, rows in sorted(by_norm.items()):
        names = sorted({r["name"] for r in rows})
        if key and len(names) > 1:
            collisions.append({"normalized": key, "names": names, "rows": rows})

    layer = load(DATA / "all_projects_layer.json")
    layer_by_name = defaultdict(list)
    for row in layer:
        key = norm(row.get("canonical_name") or row.get("raw_name"))
        if key:
            layer_by_name[key].append(row)
    layer_dupes = []
    for key, rows in layer_by_name.items():
        ids = {r.get("canonical_project_id") for r in rows}
        if len(ids) > 1:
            layer_dupes.append({"normalized": key, "ids": sorted(ids), "names": sorted({r.get("canonical_name") for r in rows})})

    layer_duplicate_details = []
    for item in layer_dupes:
        rows = [r for r in layer if r.get("canonical_project_id") in item["ids"] and norm(r.get("canonical_name") or r.get("raw_name")) == item["normalized"]]
        layer_duplicate_details.append({
            **item,
            "records": [{k: r.get(k) for k in ("canonical_project_id", "canonical_building_id", "entity_grain", "canonical_name", "raw_name", "developer", "address", "latitude", "longitude", "gla", "gba", "market_channel", "project_status", "offer_status", "source", "verification_status", "confidence", "duplicate_of", "aliases")} for r in rows],
        })

    report = {
        "generated_at": "2026-08-18",
        "read_only": True,
        "source_file_count": len(sources),
        "source_name_counts": {k: len(v) for k, v in sources.items()},
        "exact_cross_source_matches": exact_cross_source,
        "name_collisions": collisions,
        "all_projects_layer_duplicate_names": layer_dupes,
        "all_projects_layer_duplicate_details": layer_duplicate_details,
        "next_review": [
            "validate candidate merges with address/developer/GLA or GBA, never name alone",
            "separate project, building/corpus/tower and lot before assigning PRJ IDs",
            "review empty/missing historical channel files explicitly",
        ],
    }
    OUT.mkdir(exist_ok=True)
    (OUT / "unified_codifier_candidates_2026-08-18.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({k: (len(v) if isinstance(v, list) else v) for k, v in report.items() if k in {"source_file_count", "exact_cross_source_matches", "name_collisions", "all_projects_layer_duplicate_names"}}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
