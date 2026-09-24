#!/usr/bin/env python3
"""Report coworking JSON completeness without modifying project data."""

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path

FIELDS = ("network", "district", "bc", "address", "vacancy", "seats", "rate", "lat", "lng")
IDENTITY_FIELDS = ("name", "network", "bc", "address", "seats", "lat", "lng")


def blank(value):
    return value is None or value == ""


def repeated_id_quality(rows):
    groups = defaultdict(list)
    for row in rows:
        if row.get("id") is not None:
            groups[row["id"]].append(row)
    repeated = [group for group in groups.values() if len(group) > 1]
    tariff_variant_rows = 0
    identity_conflict_groups = 0
    for group in repeated:
        identities = {
            tuple(row.get(field) for field in IDENTITY_FIELDS)
            for row in group
        }
        if len(identities) == 1:
            tariff_variant_rows += len(group) - 1
        else:
            identity_conflict_groups += 1
    return {
        "repeated_id_groups": len(repeated),
        "repeated_id_rows": sum(len(group) - 1 for group in repeated),
        "tariff_variant_rows": tariff_variant_rows,
        "identity_conflict_groups": identity_conflict_groups,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", type=Path, default=Path(__file__).resolve().parents[1] / "data")
    args = parser.parse_args()
    result = {"periods": {}, "totals": {
        "rows": 0,
        "missing": Counter(),
        "duplicate_ids": 0,
        "repeated_id_groups": 0,
        "tariff_variant_rows": 0,
        "identity_conflict_groups": 0,
    }}
    # Only quarterly snapshots have row-array shape.  Auxiliary files such as
    # coworking_geocode_cache.json are dictionaries and must not enter this
    # completeness denominator.
    for path in sorted(args.data_dir.glob("coworking_20*.json")):
        period = path.stem.rsplit("_", 1)[-1]
        rows = json.loads(path.read_text(encoding="utf-8-sig"))
        missing = Counter(field for row in rows for field in FIELDS if blank(row.get(field)))
        ids = [row.get("id") for row in rows if row.get("id") is not None]
        duplicate_ids = len(ids) - len(set(ids))
        repeated_quality = repeated_id_quality(rows)
        result["periods"][period] = {
            "rows": len(rows),
            "missing": dict(sorted(missing.items())),
            "duplicate_ids": duplicate_ids,
            **repeated_quality,
        }
        result["totals"]["rows"] += len(rows)
        result["totals"]["missing"].update(missing)
        result["totals"]["duplicate_ids"] += duplicate_ids
        result["totals"]["repeated_id_groups"] += repeated_quality["repeated_id_groups"]
        result["totals"]["tariff_variant_rows"] += repeated_quality["tariff_variant_rows"]
        result["totals"]["identity_conflict_groups"] += repeated_quality["identity_conflict_groups"]
    result["totals"]["missing"] = dict(sorted(result["totals"]["missing"].items()))
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
