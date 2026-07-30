"""Validate the local external-observation layer without modifying source data.

Портировано из подготовленного Codex validate_remain_layer.py (2026-07-29) без
изменений по существу — только путь по умолчанию адаптирован под структуру
этого проекта.

Usage:
  python scripts/validate_remain_layer.py data/test_fixtures/remain_observations.sample.json

The validator intentionally does not require the optional jsonschema package.
It checks the invariants that protect the canonical quarterly database:
unique observations, field-level provenance, safe coordinates/dates, and no
synthetic lot payloads.
"""

from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path
from typing import Any

STATUSES = {"unverified", "under_review", "accepted", "blocked", "quarantine"}
CONFIDENCE = {"low", "medium", "high"}
GRAINS = {"project", "building", "unknown"}
REQUIRED = {"observation_id", "source", "observed_at", "external_name", "verification_status", "fields"}


def issue(row: int, message: str) -> str:
    return f"row {row}: {message}"


def validate(doc: Any) -> list[str]:
    errors: list[str] = []
    if not isinstance(doc, list):
        return ["root must be a JSON array"]

    seen: set[str] = set()
    for row, item in enumerate(doc, 1):
        if not isinstance(item, dict):
            errors.append(issue(row, "observation must be an object"))
            continue
        missing = REQUIRED - item.keys()
        if missing:
            errors.append(issue(row, f"missing required keys: {sorted(missing)}"))

        oid = item.get("observation_id")
        if not isinstance(oid, str) or not oid.strip():
            errors.append(issue(row, "observation_id must be a non-empty string"))
        elif oid in seen:
            errors.append(issue(row, f"duplicate observation_id: {oid}"))
        else:
            seen.add(oid)

        if item.get("source") != "remain_datalens":
            errors.append(issue(row, "source must be remain_datalens"))
        if not isinstance(item.get("external_name"), str) or not item.get("external_name", "").strip():
            errors.append(issue(row, "external_name must be non-empty"))
        if item.get("verification_status") not in STATUSES:
            errors.append(issue(row, "invalid verification_status"))
        if item.get("entity_grain", "unknown") not in GRAINS:
            errors.append(issue(row, "invalid entity_grain"))

        observed_at = item.get("observed_at")
        if isinstance(observed_at, str):
            try:
                date.fromisoformat(observed_at)
            except ValueError:
                errors.append(issue(row, "observed_at must be ISO date YYYY-MM-DD"))
        else:
            errors.append(issue(row, "observed_at must be a string"))

        fields = item.get("fields")
        if not isinstance(fields, dict):
            errors.append(issue(row, "fields must be an object"))
            continue
        for name, field in fields.items():
            if not isinstance(field, dict):
                errors.append(issue(row, f"field {name!r} must be an object"))
                continue
            if "raw_value" not in field:
                errors.append(issue(row, f"field {name!r} has no raw_value"))
            if field.get("confidence") not in CONFIDENCE:
                errors.append(issue(row, f"field {name!r} has invalid confidence"))
            if field.get("verification_status") not in STATUSES:
                errors.append(issue(row, f"field {name!r} has invalid verification_status"))
            if name in {"latitude", "longitude"}:
                value = field.get("normalized_value")
                if value is not None and not isinstance(value, (int, float)):
                    errors.append(issue(row, f"field {name!r} coordinate is not numeric"))
                elif name == "latitude" and value is not None and not (54.0 <= value <= 57.0):
                    errors.append(issue(row, f"field {name!r} outside Moscow-region sanity range"))
                elif name == "longitude" and value is not None and not (35.0 <= value <= 40.0):
                    errors.append(issue(row, f"field {name!r} outside Moscow-region sanity range"))

        # External observations may describe a project, but must never carry
        # synthetic quarterly lot rows or silently alter canonical totals.
        forbidden = {"lots", "lot_rows", "sale_lots", "deal_rows"} & item.keys()
        if forbidden:
            errors.append(issue(row, f"synthetic/detail payload forbidden: {sorted(forbidden)}"))

    return errors


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: python scripts/validate_remain_layer.py observations.json", file=sys.stderr)
        return 2
    path = Path(sys.argv[1])
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # pragma: no cover - CLI diagnostic
        print(f"ERROR: cannot read {path}: {exc}", file=sys.stderr)
        return 2
    errors = validate(payload)
    if errors:
        print(f"FAIL: {len(errors)} issue(s)")
        print("\n".join(errors))
        return 1
    print(f"PASS: {len(payload)} external observation(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
