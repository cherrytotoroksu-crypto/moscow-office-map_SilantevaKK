"""Find safe gap-fill candidates in the local MosPrime snapshot.

This audit is deliberately read-only. A card must match a public office
project or host building by normalized name, normalized address and a point
within 150 metres. The reciprocal-use guard prevents one source building from
being copied into multiple target grains.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path

from all_projects_entity_roles import ROLE_REQUIRED_FIELDS
from audit_gap_fill_from_bc_base import distance_m, record_names
from unified_building_identity import normalize_address, normalize_label


ROOT = Path(__file__).resolve().parents[1]
LAYER_PATH = ROOT / "data" / "all_projects_layer.json"
SOURCE_PATH = ROOT / "data" / "mosprimeoffice_bc_2026-09-23.json"
REVIEW_PATH = ROOT / "data" / "qa" / "host_building_gap_fill_20260924.json"
MAX_DISTANCE_M = 150


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def source_names(record):
    return {normalize_label(record.get("name"))} - {""}


def candidate_fields(target, source):
    required = set(ROLE_REQUIRED_FIELDS.get(target.get("entity_role"), ()))
    proposed = {}
    if "gba" in required and target.get("gba") is None and source.get("total_area") is not None:
        proposed["gba"] = source["total_area"]
    if "input_year" in required and target.get("input_year") is None and source.get("year") is not None:
        proposed["input_year"] = source["year"]
    if target.get("cls") in (None, "") and source.get("mrf_class"):
        proposed["cls"] = source["mrf_class"]
    return proposed


def audit(layer, source_items, reviewed_rejections=None):
    reviewed_rejections = set(reviewed_rejections or ())
    by_address = defaultdict(list)
    by_name = defaultdict(list)
    for source in source_items:
        address = normalize_address(source.get("address"))
        if address:
            by_address[address].append(source)
        for name in source_names(source):
            by_name[name].append(source)

    candidates = []
    rejected = Counter()
    for target in layer:
        if target.get("public_visibility") != "public" or target.get("duplicate_of"):
            continue
        if target.get("entity_role") not in {"office_project", "host_building"}:
            continue
        if target.get("canonical_project_id") in reviewed_rejections:
            rejected["reviewed_source_conflict"] += 1
            continue
        target_address = normalize_address(target.get("address"))
        target_names = record_names(target)
        pool = []
        if target_address:
            pool.extend(by_address.get(target_address, []))
        for name in target_names:
            pool.extend(by_name.get(name, []))
        unique_pool = {item.get("id"): item for item in pool}.values()

        accepted = []
        for source in unique_pool:
            address_match = bool(target_address) and target_address == normalize_address(source.get("address"))
            name_match = bool(target_names & source_names(source))
            if not (address_match and name_match):
                continue
            distance = distance_m(target, source)
            if distance is None or distance > MAX_DISTANCE_M:
                continue
            fields = candidate_fields(target, source)
            if fields:
                accepted.append((source, fields, round(distance, 1)))

        if len(accepted) != 1:
            rejected["no_safe_match" if not accepted else "ambiguous_safe_matches"] += 1
            continue
        source, fields, distance = accepted[0]
        candidates.append({
            "canonical_project_id": target.get("canonical_project_id"),
            "canonical_building_id": target.get("canonical_building_id"),
            "canonical_name": target.get("canonical_name"),
            "entity_role": target.get("entity_role"),
            "source_id": source.get("id"),
            "source_name": source.get("name"),
            "source_address": source.get("address"),
            "identity": {"address_match": True, "name_match": True, "distance_m": distance},
            "proposed_fields": fields,
            "sources": [source.get("source_url")],
        })

    source_usage = Counter(candidate["source_id"] for candidate in candidates)
    reciprocal = [candidate for candidate in candidates if source_usage[candidate["source_id"]] == 1]
    rejected["source_matches_multiple_targets"] += len(candidates) - len(reciprocal)
    return {
        "read_only": True,
        "source": str(SOURCE_PATH.relative_to(ROOT)),
        "max_distance_m": MAX_DISTANCE_M,
        "candidate_count": len(reciprocal),
        "proposed_field_counts": dict(sorted(Counter(
            field for candidate in reciprocal for field in candidate["proposed_fields"]
        ).items())),
        "rejected": dict(sorted(rejected.items())),
        "candidates": reciprocal,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    review = load(REVIEW_PATH) if REVIEW_PATH.exists() else {"rejected": []}
    reviewed_rejections = {
        item["canonical_project_id"] for item in review.get("rejected", [])
    }
    report = audit(load(LAYER_PATH), load(SOURCE_PATH)["items"], reviewed_rejections)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
