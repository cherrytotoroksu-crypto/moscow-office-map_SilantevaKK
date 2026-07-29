"""Regression test: 'Звенигородская от Гранель' Q2 2026 restoration.

Guards against the building silently dropping out of Q2 again (as it did before
this fix) or its Q2 lot aggregates drifting from the verified values sourced
from the "СРАВНЕНИЕ КВАРТАЛОВ" reconciliation sheet.
"""

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
BUILDING_NAME = "Звенигородская от Гранель"

EXPECTED_LOTS = 19
EXPECTED_VOLUME = 7233.27
EXPECTED_WEIGHT = 3108176690
EXPECTED_PRICE = 429705.60894312  # weight / volume

TOLERANCE = 0.01


def fail(message: str) -> None:
    print(f"FAIL: {message}")
    sys.exit(1)


def main() -> None:
    lots_path = REPO_ROOT / "data" / "lots_202606.json"
    buildings_path = REPO_ROOT / "data" / "buildings_202606.json"

    lots = json.loads(lots_path.read_text(encoding="utf-8"))
    buildings = json.loads(buildings_path.read_text(encoding="utf-8"))

    if BUILDING_NAME not in lots:
        fail(f"'{BUILDING_NAME}' is missing from data/lots_202606.json")

    rows = lots[BUILDING_NAME]
    if len(rows) != EXPECTED_LOTS:
        fail(f"lot count = {len(rows)}, expected {EXPECTED_LOTS}")

    total_area = sum(row["area"] for row in rows)
    if abs(total_area - EXPECTED_VOLUME) > TOLERANCE:
        fail(f"sum(area) = {total_area}, expected {EXPECTED_VOLUME}")

    total_value = sum(row["total"] for row in rows)
    if abs(total_value - EXPECTED_WEIGHT) > 1:
        fail(f"sum(total) = {total_value}, expected {EXPECTED_WEIGHT}")

    building = next((b for b in buildings if b.get("name") == BUILDING_NAME), None)
    if building is None:
        fail(f"'{BUILDING_NAME}' is missing from data/buildings_202606.json")

    if building.get("on_sale") != "да":
        fail(f"on_sale = {building.get('on_sale')!r}, expected 'да'")

    if building.get("lots") != EXPECTED_LOTS:
        fail(f"buildings_202606.json lots = {building.get('lots')}, expected {EXPECTED_LOTS}")

    if abs(building.get("volume", 0) - EXPECTED_VOLUME) > TOLERANCE:
        fail(f"buildings_202606.json volume = {building.get('volume')}, expected {EXPECTED_VOLUME}")

    if abs(building.get("weight", 0) - EXPECTED_WEIGHT) > 1:
        fail(f"buildings_202606.json weight = {building.get('weight')}, expected {EXPECTED_WEIGHT}")

    computed_price = total_value / total_area
    if abs(building.get("price", 0) - computed_price) > TOLERANCE:
        fail(
            f"buildings_202606.json price = {building.get('price')}, "
            f"expected weight/volume = {computed_price}"
        )

    if abs(computed_price - EXPECTED_PRICE) > 1:
        fail(f"computed price = {computed_price}, expected ~{EXPECTED_PRICE}")

    print(json.dumps({
        "building": BUILDING_NAME,
        "lots": len(rows),
        "volume": round(total_area, 2),
        "weight": round(total_value),
        "price": round(computed_price, 2),
        "status": "PASS",
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
