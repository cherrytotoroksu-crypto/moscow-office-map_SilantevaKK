"""Create a semantic audit of the 2026-09-24 worktree data changes.

The baseline is the current HEAD.  The report is intended for review before
staging: dates/statuses include provenance and reliability, derived geography
is recomputed, and coworking snapshots are compared row-by-row without
collapsing repeated tariff ids.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from collections import Counter, defaultdict
from pathlib import Path

from recompute_geo import compute_geo


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
QA = DATA / "qa"
REPORT = QA / "final_change_audit_20260924.json"
DATE_FIELDS = ("input_year", "input_date_kind", "input_quarter", "project_status")
GEO_FIELDS = ("zone", "submarket", "bizFormed", "bizForming")
COWORKING_FILES = tuple(f"coworking_{period}.json" for period in ("202506", "202509", "202512", "202603", "202606"))
URL_RE = re.compile(r"https?://[^\s,;)]+")


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def git_executable():
    candidate = os.environ.get("GIT_EXE") or shutil.which("git")
    if not candidate:
        raise RuntimeError("git executable not found; set GIT_EXE")
    return candidate


def load_head(relative_path: str):
    raw = subprocess.check_output(
        [git_executable(), "show", f"HEAD:{relative_path}"], cwd=ROOT
    )
    return json.loads(raw.decode("utf-8-sig"))


def record_key(row):
    return (row.get("canonical_project_id"), row.get("canonical_building_id"))


def values_from(item):
    values = []
    for key in ("sources", "source", "evidence"):
        value = item.get(key)
        if isinstance(value, list):
            values.extend(str(v) for v in value)
        elif value:
            values.append(str(value))
    return values


def provenance_index(current_rows, current_dates):
    sources = defaultdict(list)
    official_reports = defaultdict(set)
    official_names = {
        "gap_fill_stone_20260924.json",
        "gap_fill_official_plans_20260924.json",
        "project_status_sync_20260924.json",
    }
    for path in sorted(QA.glob("*20260924*.json")):
        if path.name == REPORT.name:
            continue
        doc = load(path)
        for item in doc.get("accepted", []):
            project_id = item.get("canonical_project_id")
            if not project_id:
                continue
            for source in values_from(item):
                if source not in sources[project_id]:
                    sources[project_id].append(source)
            if path.name in official_names:
                official_reports[project_id].add(path.name)

    for row in current_rows:
        project_id = row.get("canonical_project_id")
        for source in URL_RE.findall(row.get("qa_notes") or ""):
            if source not in sources[project_id]:
                sources[project_id].append(source)
    for value in current_dates.values():
        project_id = value.get("canonical_project_id")
        source = value.get("source")
        if project_id and source and source not in sources[project_id]:
            sources[project_id].append(source)
    return sources, official_reports


def reliability(project_id, sources, official_reports):
    url_count = len({url for source in sources for url in URL_RE.findall(source)})
    if official_reports.get(project_id):
        return "high: official/current primary source reviewed on page"
    if url_count >= 2:
        return "high: at least two cited sources"
    return "needs_review: fewer than two sources and no reviewed official-source report"


def audit_layer():
    before = load_head("data/all_projects_layer.json")
    after = load(DATA / "all_projects_layer.json")
    before_by_key = {record_key(row): row for row in before}
    current_dates = load(DATA / "building_dates.json")
    sources_by_project, official_reports = provenance_index(after, current_dates)

    date_changes = []
    field_counts = Counter()
    geo_changes = []
    geo_counts = Counter()
    geo_errors = []
    other_changes = []
    ignored = set(DATE_FIELDS) | set(GEO_FIELDS)

    for row in after:
        key = record_key(row)
        old = before_by_key.get(key)
        if old is None:
            continue
        changed_dates = {
            field: {"before": old.get(field), "after": row.get(field)}
            for field in DATE_FIELDS
            if old.get(field) != row.get(field)
        }
        if changed_dates:
            field_counts.update(changed_dates.keys())
            project_id = row.get("canonical_project_id")
            source_values = sources_by_project.get(project_id, [])
            date_changes.append({
                "canonical_project_id": project_id,
                "canonical_building_id": row.get("canonical_building_id"),
                "canonical_name": row.get("canonical_name"),
                "changes": changed_dates,
                "sources": source_values,
                "reliability": reliability(project_id, source_values, official_reports),
            })

        changed_geo = {
            field: {"before": old.get(field), "after": row.get(field)}
            for field in GEO_FIELDS
            if old.get(field) != row.get(field)
        }
        if changed_geo:
            computed = compute_geo(row.get("latitude"), row.get("longitude"))
            valid = True
            for field, change in changed_geo.items():
                geo_counts[field] += 1
                if change["before"] not in (None, "") or change["after"] != computed.get(field):
                    valid = False
                    geo_errors.append({"key": key, "field": field, "change": change, "computed": computed.get(field)})
            geo_changes.append({
                "canonical_project_id": row.get("canonical_project_id"),
                "canonical_building_id": row.get("canonical_building_id"),
                "canonical_name": row.get("canonical_name"),
                "coordinates": [row.get("latitude"), row.get("longitude")],
                "changes": changed_geo,
                "matches_point_in_polygon": valid,
            })

        changed_other = {}
        for field in sorted(set(old) | set(row)):
            if field in ignored or field == "qa_notes":
                continue
            if old.get(field) != row.get(field):
                changed_other[field] = {"before": old.get(field), "after": row.get(field)}
        if changed_other:
            other_changes.append({
                "canonical_project_id": row.get("canonical_project_id"),
                "canonical_building_id": row.get("canonical_building_id"),
                "canonical_name": row.get("canonical_name"),
                "changes": changed_other,
            })

    return {
        "dates_and_statuses": {
            "rows": len(date_changes),
            "field_counts": dict(field_counts),
            "changes": date_changes,
            "needs_review": [x for x in date_changes if x["reliability"].startswith("needs_review")],
        },
        "derived_geography": {
            "rule": "Fill previously empty values only, using scripts/recompute_geo.py point-in-polygon and existing coordinates.",
            "rows": len(geo_changes),
            "field_counts": dict(geo_counts),
            "all_changes_match_rule": not geo_errors,
            "errors": geo_errors,
            "sample_10": geo_changes[:10],
            "changes": geo_changes,
        },
        "other_layer_fields": {"rows": len(other_changes), "changes": other_changes},
    }


def audit_coworking():
    changes = []
    changed_protected_ids = []
    protected_anomalies = []
    for filename in COWORKING_FILES:
        before = load_head(f"data/{filename}")
        after = load(DATA / filename)
        if len(before) != len(after):
            raise ValueError(f"{filename}: row count changed {len(before)} -> {len(after)}")
        for index, (old, row) in enumerate(zip(before, after)):
            changed = {
                field: {"before": old.get(field), "after": row.get(field)}
                for field in sorted(set(old) | set(row))
                if old.get(field) != row.get(field)
            }
            if changed:
                item = {
                    "file": filename,
                    "row_index": index,
                    "id": row.get("id"),
                    "name": row.get("name"),
                    "bc": row.get("bc"),
                    "changes": changed,
                }
                changes.append(item)
                if row.get("id") in (84, 256):
                    changed_protected_ids.append(item)
            if filename == "coworking_202606.json":
                vacancy, seats = row.get("vacancy"), row.get("seats")
                if isinstance(vacancy, (int, float)) and isinstance(seats, (int, float)) and vacancy > seats:
                    protected_anomalies.append({
                        "id": row.get("id"), "name": row.get("name"), "bc": row.get("bc"),
                        "vacancy": vacancy, "seats": seats,
                        "vacancy_or_seats_changed": bool({"vacancy", "seats"} & set(changed)),
                    })
    return {
        "changed_rows": len(changes),
        "changes": changes,
        "duplicate_ids_84_256_changed": changed_protected_ids,
        "q2_2026_vacancy_gt_seats": protected_anomalies,
        "protected_issues_unchanged": not changed_protected_ids and not any(x["vacancy_or_seats_changed"] for x in protected_anomalies),
    }


def audit_building_dates():
    before = load_head("data/building_dates.json")
    after = load(DATA / "building_dates.json")
    changes = []
    for key in sorted(set(before) | set(after)):
        old, row = before.get(key, {}), after.get(key, {})
        changed = {
            field: {"before": old.get(field), "after": row.get(field)}
            for field in sorted(set(old) | set(row))
            if old.get(field) != row.get(field)
        }
        if changed:
            changes.append({"key": key, "changes": changed})
    return {"rows": len(changes), "changes": changes}


def main():
    report = {
        "checked_on": "2026-09-24",
        "baseline": "HEAD",
        "all_projects_layer": audit_layer(),
        "coworking_snapshots": audit_coworking(),
        "building_dates": audit_building_dates(),
    }
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "report": str(REPORT.relative_to(ROOT)),
        "date_field_counts": report["all_projects_layer"]["dates_and_statuses"]["field_counts"],
        "date_rows_needing_review": len(report["all_projects_layer"]["dates_and_statuses"]["needs_review"]),
        "geo_field_counts": report["all_projects_layer"]["derived_geography"]["field_counts"],
        "geo_rule_errors": len(report["all_projects_layer"]["derived_geography"]["errors"]),
        "coworking_changed_rows": report["coworking_snapshots"]["changed_rows"],
        "protected_coworking_issues_unchanged": report["coworking_snapshots"]["protected_issues_unchanged"],
        "building_dates_changed_rows": report["building_dates"]["rows"],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
