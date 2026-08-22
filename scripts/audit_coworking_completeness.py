#!/usr/bin/env python3
"""Report coworking JSON completeness without modifying project data."""

import argparse
import json
from collections import Counter
from pathlib import Path

FIELDS = ("network", "district", "bc", "address", "vacancy", "seats", "rate", "lat", "lng")


def blank(value):
    return value is None or value == ""


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", type=Path, default=Path(__file__).resolve().parents[1] / "data")
    args = parser.parse_args()
    result = {"periods": {}, "totals": {"rows": 0, "missing": Counter(), "duplicate_ids": 0}}
    for path in sorted(args.data_dir.glob("coworking_*.json")):
        period = path.stem.rsplit("_", 1)[-1]
        rows = json.loads(path.read_text(encoding="utf-8-sig"))
        missing = Counter(field for row in rows for field in FIELDS if blank(row.get(field)))
        ids = [row.get("id") for row in rows if row.get("id") is not None]
        duplicate_ids = len(ids) - len(set(ids))
        result["periods"][period] = {
            "rows": len(rows),
            "missing": dict(sorted(missing.items())),
            "duplicate_ids": duplicate_ids,
        }
        result["totals"]["rows"] += len(rows)
        result["totals"]["missing"].update(missing)
        result["totals"]["duplicate_ids"] += duplicate_ids
    result["totals"]["missing"] = dict(sorted(result["totals"]["missing"].items()))
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
