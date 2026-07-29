"""Regression test: River Park Коломенское — Q2 2026 office lots.

Guards the four mandated control totals for the 2026-07-06 CIAN snapshot, the
stability of the per-lot keys, and the rule that the lots stay attached to the
single existing River Park building card (no duplicate card).

Source of the snapshot:
  https://www.cian.ru/kupit-ofis-delovoy-centr-river-park-kolomenskiy-moskva-348603/
  captured 2026-07-06; per-lot listing URLs are stored on each row.

Scope rules applied when importing: deal_type == sale AND property_type == office
only — residential, retail, ПСН, rent, serviced offices and the secondary-market
lot are excluded by construction (they are not present in this entity).
"""

import json
import re
import sys
from decimal import Decimal
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
BUILDING_NAME = "River Park Коломенское"

EXPECTED_LOTS = 10
EXPECTED_AREA = Decimal("486.0")
EXPECTED_TOTAL = Decimal("200320395.1")
EXPECTED_WAVG = Decimal("412181.882921811")   # total / area, 9 dp
EXPECTED_SNAPSHOT = "2026-07-06"

LOT_KEY_RE = re.compile(r"^cian_\d+$")
WAVG_TOLERANCE = Decimal("0.000001")

failures = []


def check(condition: bool, message: str) -> None:
    if not condition:
        failures.append(message)


def main() -> None:
    lots = json.loads((REPO_ROOT / "data" / "lots_202606.json").read_text(encoding="utf-8"))
    buildings = json.loads((REPO_ROOT / "data" / "buildings_202606.json").read_text(encoding="utf-8"))

    check(BUILDING_NAME in lots, f"'{BUILDING_NAME}' missing from data/lots_202606.json")
    rows = lots.get(BUILDING_NAME, [])

    # ---- control total 1: lot count -----------------------------------------
    check(len(rows) == EXPECTED_LOTS, f"lot count = {len(rows)}, expected {EXPECTED_LOTS}")

    # ---- control totals 2-4: area, value, weighted average price -------------
    total_area = sum((Decimal(str(r["area"])) for r in rows), Decimal(0))
    total_value = sum((Decimal(str(r["total"])) for r in rows), Decimal(0))
    check(total_area == EXPECTED_AREA, f"sum(area) = {total_area}, expected {EXPECTED_AREA}")
    check(total_value == EXPECTED_TOTAL, f"sum(total) = {total_value}, expected {EXPECTED_TOTAL}")

    if total_area:
        wavg = total_value / total_area
        check(
            abs(wavg - EXPECTED_WAVG) < WAVG_TOLERANCE,
            f"weighted avg price = {wavg}, expected ~{EXPECTED_WAVG}",
        )

    # ---- per-row exactness: total == area * price, no rounding to millions ---
    for r in rows:
        exact = Decimal(str(r["area"])) * Decimal(str(r["price"]))
        stored = Decimal(str(r["total"]))
        check(
            exact == stored,
            f"{r.get('lot_key')}: total {stored} != area*price {exact}",
        )

    # ---- stable lot keys, no duplicates -------------------------------------
    keys = [r.get("lot_key") for r in rows]
    check(all(k is not None for k in keys), "some River Park rows have no lot_key")
    check(
        len(set(keys)) == len(keys),
        f"duplicate lot_key detected: "
        f"{sorted(k for k in set(keys) if keys.count(k) > 1)}",
    )
    for k in keys:
        check(bool(k and LOT_KEY_RE.match(k)), f"lot_key {k!r} does not match cian_<listing_id>")

    # ---- no aggregate placeholder left behind -------------------------------
    check(
        not any(r.get("block") == "aggregate_only" for r in rows),
        "an 'aggregate_only' placeholder row is still present",
    )

    # ---- provenance ----------------------------------------------------------
    for r in rows:
        check(
            r.get("source_snapshot") == EXPECTED_SNAPSHOT,
            f"{r.get('lot_key')}: source_snapshot = {r.get('source_snapshot')!r}, "
            f"expected {EXPECTED_SNAPSHOT!r}",
        )
        check(
            str(r.get("source_url", "")).startswith("https://www.cian.ru/"),
            f"{r.get('lot_key')}: missing/foreign source_url",
        )

    # ---- lots attached to exactly one existing building card ----------------
    cards = [b for b in buildings if b.get("name") == BUILDING_NAME]
    check(len(cards) == 1, f"expected exactly 1 River Park building card, found {len(cards)}")
    if len(cards) == 1:
        card = cards[0]
        check(
            card.get("lots") == EXPECTED_LOTS,
            f"building card lots = {card.get('lots')}, expected {EXPECTED_LOTS}",
        )
        check(
            Decimal(str(card.get("volume"))) == EXPECTED_AREA,
            f"building card volume = {card.get('volume')}, expected {EXPECTED_AREA}",
        )
        check(
            Decimal(str(card.get("weight"))) == EXPECTED_TOTAL,
            f"building card weight = {card.get('weight')}, expected {EXPECTED_TOTAL}",
        )

    if failures:
        for message in failures:
            print(f"FAIL: {message}")
        sys.exit(1)

    print(json.dumps({
        "building": BUILDING_NAME,
        "lots": len(rows),
        "area_m2": str(total_area),
        "total_rub": str(total_value),
        "weighted_avg_price": str(total_value / total_area),
        "distinct_lot_keys": len(set(keys)),
        "snapshot": EXPECTED_SNAPSHOT,
        "status": "PASS",
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
