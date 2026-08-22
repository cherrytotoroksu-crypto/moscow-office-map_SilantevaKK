"""Apply the first source-backed wave of codifier gap fixes.

The script is intentionally idempotent.  It updates only projects whose address
and identity were corroborated independently and records the replaced values in
the evidence file rather than adding non-schema fields to the public registry.
"""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LAYER_PATH = ROOT / "data" / "all_projects_layer.json"
EVIDENCE_PATH = ROOT / "data" / "qa" / "codifier_gap_wave_01_20260822.json"
CHECKED = "2026-08-22"


FIXES = {
    "proj-1": {
        "expected_name": "STONE Пресня",
        "values": {
            "gba": 16277,
            "gla": 13338,
        },
        "sources": [
            "https://ibcrealestate.ru/catalog/T96_13282/",
            "https://of.ru/bc/12524",
        ],
        "note": (
            "Wave 01 verified 2026-08-22 by exact address Ходынская ул., вл. 2, стр. 9. "
            "ibcrealestate.ru/catalog/T96_13282 reports GBA 16277 m2, GLA 13338 m2 "
            "and planned Q1 2027; of.ru/bc/12524 independently reports the same address, "
            "GBA 16277 m2 and year 2027. "
            "The completion date remains planned, not confirmed."
        ),
    },
    "proj-85": {
        "expected_name": "Plaza Technopark",
        "values": {
            "gba": 32138,
            "gla": 23358,
        },
        "sources": [
            "https://www.plazatechnopark.ru/",
            "https://morrowgroup.ru/biznescentr/plaza-technopark/",
        ],
        "note": (
            "Wave 01 verified 2026-08-22 by exact address Андропова проспект, 10. "
            "plazatechnopark.ru and morrowgroup.ru/biznescentr/plaza-technopark independently "
            "report GBA 32138 m2, rentable area/GLA 23358 m2 and completion in 2021; the existing Q4 value "
            "comes from the cited official commissioning permit in building_dates.json."
        ),
    },
}

ORIGINAL_VALUES = {
    "proj-1": {"gba": 15000, "gla": 15000},
    "proj-85": {"gba": 24700, "gla": None},
}


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def save(path: Path, value) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def append_note(record: dict, note: str) -> None:
    existing = str(record.get("qa_notes") or "").strip()
    if note not in existing:
        record["qa_notes"] = f"{existing} {note}".strip()


def main() -> None:
    layer = load(LAYER_PATH)
    by_id = {row.get("canonical_project_id"): row for row in layer}
    evidence = {"checked_at": CHECKED, "wave": 1, "applied": [], "deferred_conflicts": []}

    for project_id, fix in FIXES.items():
        record = by_id[project_id]
        if record.get("canonical_name") != fix["expected_name"]:
            raise ValueError(f"identity drift for {project_id}: {record.get('canonical_name')!r}")
        before = ORIGINAL_VALUES[project_id]
        record.update(fix["values"])
        record["last_verified_at"] = CHECKED
        record["source_count"] = max(len(fix["sources"]), int(record.get("source_count") or 0))
        append_note(record, fix["note"])
        evidence["applied"].append({
            "canonical_project_id": project_id,
            "canonical_name": record["canonical_name"],
            "address": record.get("address"),
            "before": before,
            "after": fix["values"],
            "sources": fix["sources"],
        })

    evidence["deferred_conflicts"] = [
        {
            "canonical_project_id": "proj-1/proj-85/proj-86",
            "canonical_name": "STONE Пресня / Plaza Technopark / Porta Forma lifecycle dates",
            "reason": "Verified date changes are prepared but data/building_dates.json requires separate explicit permission.",
        },
        {
            "canonical_project_id": "proj-13",
            "canonical_name": "Fly Tower",
            "reason": "Sources describe incompatible historical/current concepts and areas (30000, 52200, 74000 m2).",
        },
        {
            "canonical_project_id": "proj-87",
            "canonical_name": "Slava",
            "reason": "Sources mix residential phases, SLAVA 4 office cluster and a separate marketed office building.",
        },
        {
            "canonical_project_id": "proj-95",
            "canonical_name": "Алкон 3",
            "reason": "Exact-address sources conflict on GBA (24321, 35865 and existing 53104 m2).",
        },
    ]
    save(LAYER_PATH, layer)
    save(EVIDENCE_PATH, evidence)
    print(json.dumps({"updated": len(FIXES), "evidence": str(EVIDENCE_PATH)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
