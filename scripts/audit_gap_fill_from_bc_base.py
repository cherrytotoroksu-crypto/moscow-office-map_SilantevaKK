"""Find safe gap-fill candidates in the consolidated business-centre base.

Read-only by design.  A source row is accepted only when identity is
corroborated by an exact normalized address or label and coordinates are no
more than 150 metres apart.  Coordinates never select the nearest object.
Project and building identifiers are kept together so multi-building projects
cannot collapse to one arbitrary row.
"""
from __future__ import annotations

import argparse
import json
import math
from collections import Counter, defaultdict
from pathlib import Path

from all_projects_entity_roles import ROLE_REQUIRED_FIELDS
from unified_building_identity import normalize_address, normalize_label


ROOT = Path(__file__).resolve().parents[1]
LAYER_PATH = ROOT / "data" / "all_projects_layer.json"
SOURCE_PATH = ROOT / "data" / "bc_base_classes_2026-09-24.json"
MAX_DISTANCE_M = 150

FIELD_MAP = {
    "cls": "class",
    "input_year": "year",
    "input_quarter": "quarter",
}


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def distance_m(left, right):
    values = (
        left.get("latitude"), left.get("longitude"),
        right.get("lat"), right.get("lng"),
    )
    if None in values:
        return None
    lat1, lon1, lat2, lon2 = map(float, values)
    radius = 6_371_000
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    value = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * radius * math.asin(math.sqrt(value))


def record_names(record):
    return {
        normalize_label(value)
        for value in [
            record.get("canonical_name"), record.get("raw_name"),
            record.get("flex_site_label"), *(record.get("aliases") or []),
        ]
        if normalize_label(value)
    }


def source_names(record):
    return {
        normalize_label(record.get(key))
        for key in ("name", "name_src", "name_2gis")
        if normalize_label(record.get(key))
    }


def identity_key(record):
    return (
        record.get("canonical_project_id"),
        record.get("canonical_building_id"),
    )


def candidate_fields(target, source):
    required = set(ROLE_REQUIRED_FIELDS.get(target.get("entity_role"), ()))
    proposed = {}
    for target_field, source_field in FIELD_MAP.items():
        if target_field not in required and target_field != "cls":
            continue
        if target.get(target_field) not in (None, ""):
            continue
        value = source.get(source_field)
        if value in (None, ""):
            continue
        if target_field == "cls" and source.get("class_source") == "подтверждённый источник не найден":
            continue
        proposed[target_field] = value
    if "input_year" not in proposed:
        proposed.pop("input_quarter", None)
    return proposed


def audit(layer, source_items):
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
        # candidate_fields cannot discover missing targets without a source;
        # this cheap pre-check keeps fully populated rows out of matching.
        relevant = set(ROLE_REQUIRED_FIELDS[target["entity_role"]]) | {"cls"}
        if not any(target.get(field) in (None, "") for field in relevant):
            continue

        target_address = normalize_address(target.get("address"))
        target_names = record_names(target)
        pool = []
        if target_address:
            pool.extend(by_address.get(target_address, []))
        for name in target_names:
            pool.extend(by_name.get(name, []))
        unique_pool = {item.get("no"): item for item in pool}.values()

        accepted = []
        for source in unique_pool:
            address_match = bool(target_address) and target_address == normalize_address(source.get("address"))
            name_match = bool(target_names & source_names(source))
            # Neither address nor coordinates are a sufficient identity key in
            # dense office clusters.  The consolidated source can contain a
            # generic card for another building at the same street address, so
            # require a corroborating normalized name as well.
            if not (address_match and name_match):
                continue
            distance = distance_m(target, source)
            if distance is None or distance > MAX_DISTANCE_M:
                continue
            fields = candidate_fields(target, source)
            if fields:
                accepted.append((source, fields, address_match, name_match, round(distance, 1)))

        if len(accepted) != 1:
            rejected["no_safe_match" if not accepted else "ambiguous_safe_matches"] += 1
            continue
        source, fields, address_match, name_match, distance = accepted[0]
        candidates.append({
            "canonical_project_id": target.get("canonical_project_id"),
            "canonical_building_id": target.get("canonical_building_id"),
            "canonical_name": target.get("canonical_name"),
            "entity_role": target.get("entity_role"),
            "source_no": source.get("no"),
            "source_name": source.get("name"),
            "source_name_src": source.get("name_src"),
            "source_address": source.get("address"),
            "identity": {
                "address_match": address_match,
                "name_match": name_match,
                "distance_m": distance,
            },
            "proposed_fields": fields,
            "sources": [value for value in (source.get("url_mosprime"), source.get("url_2gis")) if value],
        })

    # One source building must not enrich two target buildings.  This catches
    # duplicate host rows and project/building grain collisions.
    source_usage = Counter(candidate["source_no"] for candidate in candidates)
    reciprocal = [candidate for candidate in candidates if source_usage[candidate["source_no"]] == 1]
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
    layer = load(LAYER_PATH)
    source = load(SOURCE_PATH)
    report = audit(layer, source["items"])
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
