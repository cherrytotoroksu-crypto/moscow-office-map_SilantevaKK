"""Reproducible completeness and geography audit for the all-projects map.

Read-only.  The script compares the canonical registry with every historical
sale, rent, building and coworking snapshot.  It deliberately uses only
identity-safe matches (normalized name/alias or exact normalized address).
Coordinates are profiled as evidence but never used as a nearest-point match.
It never merges entities and never edits source data.
"""
from __future__ import annotations

import argparse
import json
import math
import re
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

from all_projects_entity_roles import ROLE_REQUIRED_FIELDS, role_completeness_issues


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
MOSCOW_CENTER = (55.755819, 37.617644)
COORD_TOLERANCE_M = 150
REGION_BOUNDS = (55.1, 56.1, 36.7, 38.3)
NON_PROJECT_KEYS = {"a", "a+", "b", "b+", "а", "а+", "в", "в+", "общий итог"}


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def norm(value) -> str:
    text = unicodedata.normalize("NFKC", str(value or "")).lower().replace("ё", "е")
    text = re.sub(r"[«»\"'`“”„]", "", text)
    text = re.sub(r"[^0-9a-zа-я]+", " ", text, flags=re.I)
    return re.sub(r"\s+", " ", text).strip()


def haversine_km(lat1, lon1, lat2, lon2):
    if None in (lat1, lon1, lat2, lon2):
        return None
    radius = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    value = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * radius * math.asin(math.sqrt(value))


def build_indexes(layer):
    names, addresses = defaultdict(list), defaultdict(list)
    for row in layer:
        for value in [row.get("raw_name"), row.get("canonical_name"), *(row.get("aliases") or [])]:
            if norm(value):
                names[norm(value)].append(row)
        if norm(row.get("address")):
            addresses[norm(row["address"])].append(row)
    return names, addresses


def unique_rows(rows):
    return list({(r.get("canonical_project_id"), r.get("canonical_building_id")): r for r in rows}.values())


def match_row(channel, source_row, names, addresses):
    matches = []
    # A coworking observation is the operator site, not its host building.
    # Matching `bc` here would falsely treat two related entities as duplicates.
    for key in (source_row.get("name"), source_row.get("name_orig")):
        matches.extend(names.get(norm(key), []))
    for key in (source_row.get("address"),):
        matches.extend(addresses.get(norm(key), []))
    # Coordinates are intentionally not an identity key.  They are valid
    # corroboration after a name/address match, never a nearest-point repair.
    return unique_rows(matches)


def source_observations():
    for path in sorted(DATA.glob("buildings_20*.json")):
        for row in load(path):
            yield "building", path.name, row
    for prefix, channel in (("lots", "sale"), ("rent_lots", "rent")):
        for path in sorted(DATA.glob(f"{prefix}_20*.json")):
            for name in load(path):
                if norm(name) not in NON_PROJECT_KEYS:
                    yield channel, path.name, {"name": name}
    for path in sorted(DATA.glob("coworking_20*.json")):
        for row in load(path):
            yield "coworking", path.name, row


def audit():
    layer = load(DATA / "all_projects_layer.json")
    names, addresses = build_indexes(layer)
    public = [r for r in layer if r.get("public_visibility") == "public"]
    canonical_public = [r for r in public if not r.get("duplicate_of")]

    unmatched, ambiguous = [], []
    observed = Counter()
    unique_source_names = defaultdict(set)
    for channel, filename, row in source_observations():
        observed[channel] += 1
        unique_source_names[channel].add(norm(row.get("name") or row.get("bc")))
        matches = match_row(channel, row, names, addresses)
        evidence = {
            "channel": channel,
            "source": filename,
            "name": row.get("name"),
            "bc": row.get("bc"),
            "address": row.get("address"),
            "lat": row.get("lat"),
            "lng": row.get("lng"),
        }
        if not matches:
            unmatched.append(evidence)
        elif len(matches) > 1:
            evidence["matched_ids"] = sorted({r["canonical_project_id"] for r in matches})
            ambiguous.append(evidence)

    missing_coordinates = [
        {k: r.get(k) for k in ("canonical_project_id", "canonical_name", "address", "source", "market_channel")}
        for r in canonical_public if r.get("latitude") is None or r.get("longitude") is None
    ]
    geography_outliers = []
    min_lat, max_lat, min_lon, max_lon = REGION_BOUNDS
    for row in canonical_public:
        lat, lon = row.get("latitude"), row.get("longitude")
        if lat is None or lon is None:
            continue
        distance = haversine_km(*MOSCOW_CENTER, lat, lon)
        outside = not (min_lat <= lat <= max_lat and min_lon <= lon <= max_lon)
        if outside or distance > 50:
            geography_outliers.append({
                "canonical_project_id": row["canonical_project_id"],
                "canonical_name": row["canonical_name"],
                "address": row.get("address"),
                "latitude": lat,
                "longitude": lon,
                "distance_from_center_km": round(distance, 1),
                "outside_region_bounds": outside,
            })

    field_coverage = {}
    for field in ("gba", "gla", "construction_start_year", "sales_start_year", "input_year"):
        applicable = [
            r for r in canonical_public
            if field in ROLE_REQUIRED_FIELDS.get(r.get("entity_role"), ())
        ]
        missing = [r for r in applicable if r.get(field) is None]
        by_channel = Counter()
        for row in missing:
            channels = row.get("market_channel") or ["no_market_channel"]
            for channel in channels:
                by_channel[channel] += 1
        field_coverage[field] = {
            "applicable": len(applicable),
            "not_applicable": len(canonical_public) - len(applicable),
            "present": len(applicable) - len(missing),
            "missing": len(missing),
            "coverage_pct": round(100 * (len(applicable) - len(missing)) / len(applicable), 1),
            "missing_by_source": dict(sorted(Counter(r.get("source") for r in missing).items())),
            "missing_by_channel": dict(sorted(by_channel.items())),
        }

    role_completeness = []
    for record in canonical_public:
        issues = role_completeness_issues(record)
        if issues:
            role_completeness.append({
                "canonical_project_id": record["canonical_project_id"],
                "canonical_name": record["canonical_name"],
                "entity_role": record.get("entity_role"),
                "issues": issues,
            })

    ambiguous_groups = {}
    for item in ambiguous:
        signature = json.dumps(
            {
                "channel": item["channel"],
                "name": norm(item.get("name")),
                "address": norm(item.get("address")),
                "matched_ids": item["matched_ids"],
            },
            ensure_ascii=False,
            sort_keys=True,
        )
        group = ambiguous_groups.setdefault(signature, {**item, "sources": []})
        group["sources"].append(item["source"])
    for group in ambiguous_groups.values():
        group["sources"] = sorted(set(group["sources"]))

    host_coordinate_candidates = []
    coworking_rows = [(p.name, row) for p in sorted(DATA.glob("coworking_20*.json")) for row in load(p)]
    for host in [r for r in layer if r.get("source") == "coworking_host_lookup"]:
        candidates = []
        for filename, row in coworking_rows:
            if norm(row.get("bc")) == norm(host.get("canonical_name")) and row.get("lat") is not None and row.get("lng") is not None:
                candidates.append((filename, row.get("lat"), row.get("lng"), row.get("name"), row.get("address")))
        points = sorted({(lat, lon) for _, lat, lon, _, _ in candidates})
        current = [x for x in candidates if x[0] == "coworking_202606.json"]
        current_points = sorted({(lat, lon) for _, lat, lon, _, _ in current})
        spread_m = 0.0
        for lat1, lon1 in points:
            for lat2, lon2 in points:
                spread_m = max(spread_m, haversine_km(lat1, lon1, lat2, lon2) * 1000)
        host_coordinate_candidates.append({
            "canonical_project_id": host["canonical_project_id"],
            "canonical_name": host["canonical_name"],
            "host_address": host.get("address"),
            "candidate_count": len(candidates),
            "unique_points": [{"lat": p[0], "lng": p[1]} for p in points],
            "spread_m": round(spread_m, 1),
            "latest_source": candidates[-1][0] if candidates else None,
            "latest_site": candidates[-1][3] if candidates else None,
            "latest_site_address": candidates[-1][4] if candidates else None,
            "current_candidate_count": len(current),
            "current_unique_points": [{"lat": p[0], "lng": p[1]} for p in current_points],
        })

    building_dates = load(DATA / "building_dates.json")
    report = {
        "generated_at": "2026-08-22",
        "read_only": True,
        "registry": {
            "rows": len(layer),
            "public_rows": len(public),
            "canonical_public_rows": len(canonical_public),
            "duplicate_rows_excluded_from_completeness_denominator": len(public) - len(canonical_public),
        },
        "historical_sources": {
            "observations_by_channel": dict(observed),
            "unique_normalized_names_by_channel": {k: len(v) for k, v in unique_source_names.items()},
            "unmatched_observation_count": len(unmatched),
            "unmatched_unique": list({json.dumps(x, ensure_ascii=False, sort_keys=True): x for x in unmatched}.values()),
            "ambiguous_observation_count": len(ambiguous),
            "ambiguous_unique": list({json.dumps(x, ensure_ascii=False, sort_keys=True): x for x in ambiguous}.values()),
            "ambiguous_identity_group_count": len(ambiguous_groups),
            "ambiguous_identity_groups": list(ambiguous_groups.values()),
        },
        "missing_coordinates": missing_coordinates,
        "geography_outliers": sorted(geography_outliers, key=lambda x: x["distance_from_center_km"], reverse=True),
        "field_coverage": field_coverage,
        "entity_roles": {
            "counts": dict(sorted(Counter(r.get("entity_role") for r in canonical_public).items())),
            "incomplete_record_count": len(role_completeness),
            "incomplete_records": role_completeness,
        },
        "building_identity": {
            "public_coworking_sites": sum(
                r.get("entity_role") == "coworking_site" for r in canonical_public
            ),
            "public_coworking_sites_with_building_id": sum(
                r.get("entity_role") == "coworking_site" and bool(r.get("canonical_building_id"))
                for r in canonical_public
            ),
            "internal_blocked_coworking_sites": [
                {"canonical_project_id": r["canonical_project_id"], "canonical_name": r["canonical_name"]}
                for r in layer
                if r.get("entity_role") == "coworking_site" and r.get("public_visibility") == "internal_only"
            ],
            "host_buildings": sum(r.get("entity_role") == "host_building" for r in layer),
        },
        "date_model": {
            "all_projects_has_only_commission_input_year": False,
            "construction_start_and_sales_start_in_layer_schema": True,
            "building_dates_rows_read_only": len(building_dates),
            "building_dates_with_canonical_project_id": sum(
                bool(value.get("canonical_project_id")) for value in building_dates.values()
            ),
            "stage_observation_implemented": (DATA / "stage_observations.json").exists(),
        },
        "coworking_host_coordinate_candidates": host_coordinate_candidates,
    }
    return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = audit()
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    summary = {
        "registry": report["registry"],
        "unmatched_observations": report["historical_sources"]["unmatched_observation_count"],
        "ambiguous_observations": report["historical_sources"]["ambiguous_observation_count"],
        "missing_coordinates": len(report["missing_coordinates"]),
        "geography_outliers": len(report["geography_outliers"]),
        "field_coverage": report["field_coverage"],
        "host_coordinate_candidates": Counter(
            "none" if x["candidate_count"] == 0 else "conflict" if x["spread_m"] > COORD_TOLERANCE_M else "usable"
            for x in report["coworking_host_coordinate_candidates"]
        ),
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
