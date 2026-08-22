"""Attach building_dates to canonical ids and synchronize known date fields."""
import json
import re
import unicodedata
from collections import defaultdict
from pathlib import Path

from validate_all_projects_layer import validate


ROOT = Path(__file__).resolve().parents[1]
LAYER_PATH = ROOT / "data" / "all_projects_layer.json"
DATES_PATH = ROOT / "data" / "building_dates.json"
CHECKED = "2026-08-22"


def norm(value):
    value = unicodedata.normalize("NFKC", str(value or "")).lower().replace("ё", "е")
    value = re.sub(r"[^0-9a-zа-я]+", " ", value, flags=re.I)
    return re.sub(r"\s+", " ", value).strip()


def quarter_parts(value):
    if not value or not re.fullmatch(r"\d{6}", str(value)):
        return None, None
    month = int(str(value)[4:6])
    return int(str(value)[:4]), (month - 1) // 3 + 1


def append_note(record, note):
    if note not in (record.get("qa_notes") or ""):
        record["qa_notes"] = ((record.get("qa_notes") or "").rstrip() + " " + note).strip()


def synchronize_dates(layer, dates):
    index = defaultdict(list)
    for record in layer:
        if record.get("entity_role") != "office_project":
            continue
        for value in [record.get("canonical_name"), record.get("raw_name"), *(record.get("aliases") or [])]:
            if norm(value):
                index[norm(value)].append(record)

    matched = 0
    unmatched = []
    for key, date_record in dates.items():
        candidates = {r["canonical_project_id"]: r for r in index.get(norm(key), [])}
        if len(candidates) != 1:
            unmatched.append(key)
            continue
        record = next(iter(candidates.values()))
        date_record["canonical_project_id"] = record["canonical_project_id"]
        date_record["canonical_building_id"] = record.get("canonical_building_id")
        cs_year, cs_quarter = quarter_parts(date_record.get("construction_start_q"))
        sales_year, sales_quarter = quarter_parts(date_record.get("start_q"))
        input_year, input_quarter = quarter_parts(date_record.get("commission_q"))
        record["construction_start_year"] = date_record.get("construction_start_year", cs_year)
        record["construction_start_quarter"] = cs_quarter
        record["sales_start_year"] = date_record.get("sales_start_year", sales_year)
        record["sales_start_quarter"] = sales_quarter
        if record.get("input_year") is None and input_year is not None:
            record["input_year"] = input_year
            record["input_quarter"] = input_quarter
        append_note(
            record,
            f"Lifecycle dates synchronized {CHECKED} from data/building_dates.json key={key!r}; "
            f"underlying source and its check date remain in that record ({date_record.get('last_checked')}).",
        )
        matched += 1

    for record in layer:
        record.setdefault("construction_start_year", None)
        record.setdefault("construction_start_quarter", None)
        record.setdefault("sales_start_year", None)
        record.setdefault("sales_start_quarter", None)
    return matched, unmatched


def enrich_imperia(layer, dates):
    record = next(r for r in layer if r.get("canonical_project_id") == "cwhost-0001")
    record.update({
        "gba": 203191,
        "office_area": 121497,
        "construction_start_year": 2006,
        "construction_start_quarter": None,
        "input_year": 2011,
        "input_quarter": None,
        "input_date_kind": "confirmed",
        "last_verified_at": CHECKED,
        "source_count": max(4, record.get("source_count") or 0),
    })
    append_note(
        record,
        "Areas/dates verified 2026-08-22: moscow-city.guide/towers/bashnya-imperiya and "
        "imoscowcity.ru/tower/bashnya-imperiya independently report GBA 203191 m2, office area "
        "121497 m2 and completion 2011; imperia-tower.com confirms construction began 2006 and "
        "GBA about 203000 m2. office_area is not relabeled as GLA. Exact quarters remain null.",
    )
    dates["империя"] = {
        "canonical_project_id": record["canonical_project_id"],
        "canonical_building_id": record["canonical_building_id"],
        "construction_start_q": None,
        "construction_start_year": 2006,
        "start_q": None,
        "sales_start_year": None,
        "commission_q": None,
        "commission_year": 2011,
        "source": (
            "moscow-city.guide/towers/bashnya-imperiya; imoscowcity.ru/tower/bashnya-imperiya; "
            "imperia-tower.com — two sources agree on 203191 m2/121497 m2/2011, official project "
            "page corroborates 2006 start and ~203000 m2"
        ),
        "last_checked": CHECKED,
    }


def main():
    layer = json.loads(LAYER_PATH.read_text(encoding="utf-8-sig"))
    dates = json.loads(DATES_PATH.read_text(encoding="utf-8-sig"))
    enrich_imperia(layer, dates)
    matched, unmatched = synchronize_dates(layer, dates)
    errors = validate(layer)
    if errors:
        raise ValueError("date migration produced invalid layer:\n" + "\n".join(errors))
    LAYER_PATH.write_text(json.dumps(layer, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    DATES_PATH.write_text(json.dumps(dates, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"date_records": len(dates), "matched": matched, "unmatched": unmatched}, ensure_ascii=False))


if __name__ == "__main__":
    main()
