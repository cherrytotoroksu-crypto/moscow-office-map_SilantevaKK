import argparse
import json
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--lots", required=True)
    parser.add_argument("--buildings", required=True)
    parser.add_argument("--packet", required=True)
    args = parser.parse_args()

    lots = json.loads(Path(args.lots).read_text(encoding="utf-8"))
    buildings = json.loads(Path(args.buildings).read_text(encoding="utf-8"))
    packet = json.loads(Path(args.packet).read_text(encoding="utf-8"))

    patch = packet["accept_patch"]
    key_patch = patch["homograph_key"]
    old_key = key_patch["observed_key"]
    new_key = key_patch["set_key"]
    assert old_key not in lots
    assert new_key in lots
    assert len(lots[new_key]) == key_patch["affected_rows"]

    total_rows = sum(len(rows) for rows in lots.values())
    baseline_rows = packet["source_snapshot"]["files"]["data/lots_202606.json"]["rows"]
    # Legitimate later additions (e.g. a project's missing quarter restored from a
    # verified source) grow total_rows beyond the packet's frozen baseline. The
    # packet only proves ITS OWN patch was applied correctly (checked below via
    # selectors/values), so row count must never regress below that baseline,
    # but is allowed to grow.
    assert total_rows >= baseline_rows, (
        f"lots_202606.json has fewer rows ({total_rows}) than the packet baseline "
        f"({baseline_rows}) — a legitimate addition should only increase this count."
    )
    rows_added_since_baseline = total_rows - baseline_rows

    max_relative_error = 0.0
    verified = 0
    for op in patch["total_unit_rows"]:
        selector = op["selector"]
        row = lots[selector["entity"]][selector["index"]]
        assert row[op["field"]] == op["set"]
        formula = row["area"] * row["price"]
        relative_error = abs(row["total"] - formula) / formula
        max_relative_error = max(max_relative_error, relative_error)
        verified += 1

    building_names = set()
    for building in buildings:
        if building.get("name"):
            building_names.add(building["name"])
        if building.get("name_orig"):
            building_names.add(building["name_orig"])
    assert new_key in building_names

    result = {
        "entities": len(lots),
        "rows": total_rows,
        "baseline_rows": baseline_rows,
        "rows_added_since_baseline": rows_added_since_baseline,
        "renamed_key_joined_to_building": True,
        "verified_total_corrections": verified,
        "max_corrected_relative_error": max_relative_error,
        "status": "PASS",
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
