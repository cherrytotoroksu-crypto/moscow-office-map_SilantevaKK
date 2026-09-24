"""Apply the source-backed coworking gap-fill wave dated 2026-09-24.

Only explicit records are changed.  Historical prices are not propagated
between quarters because they are time-varying.
"""
from __future__ import annotations

import json
from pathlib import Path

from validate_all_projects_layer import validate


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
CHECKED = "2026-09-24"
AFI_ADDRESS = "пл. Тверская Застава, 4"
AFI_COORDS = {"lat": 55.775682, "lng": 37.581191}


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def save(path: Path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def matching_rows(rows, *, row_id, name=None, bc=None):
    result = [row for row in rows if row.get("id") == row_id]
    if name is not None:
        result = [row for row in result if row.get("name") == name]
    if bc is not None:
        result = [row for row in result if row.get("bc") == bc]
    return result


def update_quarter(path: Path, updater):
    rows = load(path)
    count = updater(rows)
    save(path, rows)
    return count


def append_note(record, note):
    if note not in (record.get("qa_notes") or ""):
        record["qa_notes"] = ((record.get("qa_notes") or "").rstrip() + " " + note).strip()


def apply():
    counts = {}

    # AFI Gallery is the building at Tverskaya Zastava Sq., 4.  The previous
    # southern-Moscow point belonged to AFI Park Vorontsovsky.
    for period in ("202506", "202509", "202512", "202603", "202606"):
        path = DATA / f"coworking_{period}.json"

        def update_afi(rows, period=period):
            ids = (39, 40) if period == "202506" else (176,)
            matched = [row for row in rows if row.get("id") in ids and row.get("bc") == "AFI Gallery"]
            expected = 2 if period == "202506" else 1
            if len(matched) != expected:
                raise ValueError(f"{path.name}: expected {expected} AFI Gallery rows, got {len(matched)}")
            for row in matched:
                row["address"] = AFI_ADDRESS
                row.update(AFI_COORDS)
            return len(matched)

        counts[f"afi_{period}"] = update_quarter(path, update_afi)

    # The September 2026 NF Group listing quotes 70,000 RUB/place/month.
    path = DATA / "coworking_202606.json"

    def update_dubinin(rows):
        matched = matching_rows(rows, row_id=157, name="Multispace Дубинин", bc="Дубинин Скай")
        if len(matched) != 1:
            raise ValueError(f"{path.name}: expected one Multispace Dubinin row, got {len(matched)}")
        matched[0]["rate"] = 70000.0
        matched[0]["seats"] = 650
        return 1

    counts["dubinin_202606"] = update_quarter(path, update_dubinin)

    layer_path = DATA / "all_projects_layer.json"
    layer = load(layer_path)
    by_id = {row.get("canonical_project_id"): row for row in layer}

    for project_id in ("proj-176", "cwhost-hist-4b033613e3"):
        row = by_id[project_id]
        row["address"] = AFI_ADDRESS
        row["latitude"] = AFI_COORDS["lat"]
        row["longitude"] = AFI_COORDS["lng"]
        row["last_verified_at"] = CHECKED
        row["source_count"] = max(2, row.get("source_count") or 0)
        append_note(
            row,
            "AFI Gallery address/coordinates corrected 2026-09-24: official afigallery.ru identifies "
            "the complex at Tverskaya Zastava Sq., 4; the former point belonged to AFI Park Vorontsovsky.",
        )

    dubinin = by_id["proj-157"]
    dubinin.update({
        "address": "ул. Дубининская, вл. 39–41",
        "seats": 650,
        "rate": 70000.0,
        "last_verified_at": CHECKED,
        "source_count": max(2, dubinin.get("source_count") or 0),
    })
    append_note(
        dubinin,
        "Multispace Dubinin'Sky verified 2026-09-24: official multispace page reports 650+ workstations "
        "and address; current NF Group listing quotes 70000 RUB per place/month.",
    )

    errors = validate(layer)
    if errors:
        raise ValueError("coworking gap fill produced invalid layer:\n" + "\n".join(errors))
    save(layer_path, layer)
    return counts


def main():
    print(json.dumps(apply(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
