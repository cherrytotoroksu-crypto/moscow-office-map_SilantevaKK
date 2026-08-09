# -*- coding: utf-8 -*-
"""Ищет проекты без координат среди уже нанесённых зданий.

Скрипт ничего не исправляет автоматически. Он формирует воспроизводимый
отчёт-кандидатуру, объединяя квартальные buildings_*.json и канонический
all_projects_layer.json. Решение AUTO означает только безопасную кандидатуру
для переноса координат; запись всё равно должна попасть в журнал overrides.
"""
from __future__ import annotations

import csv
import json
import re
import statistics
import unicodedata
from collections import Counter, defaultdict
from difflib import SequenceMatcher
from pathlib import Path
from math import asin, cos, radians, sin, sqrt

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
OUT_JSON = ROOT / "outputs" / "future_project_match_audit.json"
OUT_CSV = ROOT / "outputs" / "future_project_match_audit.csv"


def clean_text(value):
    if value is None:
        return ""
    text = unicodedata.normalize("NFKC", str(value)).lower().replace("ё", "е")
    text = re.sub(r"[\"'`«»]", " ", text)
    text = re.sub(r"[^0-9a-zа-я]+", " ", text)
    return " ".join(text.split())


def norm_name(value):
    text = clean_text(value)
    replacements = {
        "business centre": " ", "business center": " ", "бизнес центр": " ",
        "деловой центр": " ", "офисный центр": " ", "бц": " ", "bc": " ",
        "tower": " башня ", "bldg": " корпус ", "building": " корпус ",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    return " ".join(text.split())


def norm_address(value):
    text = clean_text(value)
    replacements = {
        "город москва": " ", "г москва": " ", "москва": " ",
        "улица": "ул", "проспект": "пр", "проезд": "прд",
        "бульвар": "бул", "набережная": "наб", "переулок": "пер",
        "владение": "вл", "дом": "д", "строение": "стр",
        "корпус": "корп", "земельный участок": "зу",
    }
    for old, new in replacements.items():
        text = re.sub(rf"\b{re.escape(old)}\b", new, text)
    return " ".join(text.split())


def ratio(a, b):
    if not a or not b:
        return 0.0
    return SequenceMatcher(None, a, b).ratio()


def distance_m(a, b):
    lat1, lon1 = radians(a[0]), radians(a[1])
    lat2, lon2 = radians(b[0]), radians(b[1])
    dlat, dlon = lat2 - lat1, lon2 - lon1
    h = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    return 6371000 * 2 * asin(sqrt(h))


def coordinate_cluster_count(points, threshold_m=150):
    clusters = []
    for point in points:
        for cluster in clusters:
            if min(distance_m(point, other) for other in cluster) <= threshold_m:
                cluster.append(point)
                break
        else:
            clusters.append([point])
    return len(clusters)


def load_json(path):
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def add_candidate(store, row, source, quarter=None):
    lat = row.get("lat", row.get("latitude"))
    lng = row.get("lng", row.get("longitude"))
    if lat is None or lng is None:
        return
    name = row.get("name") or row.get("canonical_name") or row.get("raw_name")
    address = row.get("address")
    key = (norm_name(name), norm_address(address), round(float(lat), 6), round(float(lng), 6))
    item = store.setdefault(key, {
        "name": name, "address": address,
        "developer": row.get("developer"),
        "status": row.get("status") or row.get("project_status"),
        "lat": float(lat), "lng": float(lng),
        "ids": set(), "sources": set(), "quarters": set(), "occurrences": 0,
        "accepted_registry": False,
    })
    candidate_id = row.get("id") or row.get("canonical_building_id") or row.get("canonical_project_id")
    if candidate_id:
        item["ids"].add(str(candidate_id))
    item["sources"].add(source)
    if quarter:
        item["quarters"].add(quarter)
    item["occurrences"] += 1
    if source == "all_projects_layer" and row.get("verification_status") == "accepted":
        item["accepted_registry"] = True


def candidate_score(target, candidate):
    tn, cn = norm_name(target.get("name")), norm_name(candidate.get("name"))
    ta, ca = norm_address(target.get("address")), norm_address(candidate.get("address"))
    td, cd = clean_text(target.get("developer")), clean_text(candidate.get("developer"))
    exact_name = bool(tn and cn and tn == cn)
    exact_address = bool(ta and ca and ta == ca)
    contains_name = bool(tn and cn and min(len(tn), len(cn)) >= 6 and (tn in cn or cn in tn))
    name_ratio = ratio(tn, cn)
    address_ratio = ratio(ta, ca)
    score = max(name_ratio * 80, address_ratio * 85)
    if contains_name:
        score = max(score, 86)
    if exact_name:
        score = max(score, 96)
    if exact_address:
        score = max(score, 99)
    if td and cd and td == cd:
        score += 3
    if candidate.get("accepted_registry"):
        score += 1
    return min(round(score, 1), 100.0), {
        "exact_name": exact_name,
        "exact_address": exact_address,
        "contains_name": contains_name,
        "name_ratio": round(name_ratio, 3),
        "address_ratio": round(address_ratio, 3),
        "developer_match": bool(td and cd and td == cd),
    }


def main():
    future = load_json(DATA / "future_projects.json")
    targets = future["no_coords"]
    candidates = {}

    for row in future["projects"]:
        add_candidate(candidates, row, "future_projects_existing")

    for path in sorted(DATA.glob("buildings_*.json")):
        quarter = path.stem.removeprefix("buildings_")
        for row in load_json(path):
            add_candidate(candidates, row, "quarter_buildings", quarter)

    for row in load_json(DATA / "all_projects_layer.json"):
        add_candidate(candidates, row, "all_projects_layer")

    pool = list(candidates.values())
    results = []
    for target in targets:
        ranked = []
        for candidate in pool:
            score, reasons = candidate_score(target, candidate)
            if score < 45:
                continue
            ranked.append((score, candidate, reasons))
        ranked.sort(key=lambda x: (x[0], x[1]["occurrences"], x[1]["accepted_registry"]), reverse=True)
        top = ranked[:5]

        top_score = top[0][0] if top else 0
        runner_up = top[1][0] if len(top) > 1 else 0
        high = [x for x in ranked if x[0] >= 95]
        high_coords = {(round(x[1]["lat"], 6), round(x[1]["lng"], 6)) for x in high}
        high_coord_clusters = coordinate_cluster_count(list(high_coords))
        top_reasons = top[0][2] if top else {}
        target_name_tokens = norm_name(target.get("name")).split()
        generic_name = len(target_name_tokens) < 2
        strong_identity = top_reasons.get("exact_address") or (top_reasons.get("exact_name") and not generic_name)
        if top and top_score >= 95 and high_coord_clusters == 1 and strong_identity:
            decision = "AUTO"
        elif top and top_score >= 70:
            decision = "REVIEW"
        else:
            decision = "NO_MATCH"

        results.append({
            "id": target.get("id"), "name": target.get("name"),
            "address": target.get("address"), "developer": target.get("developer"),
            "status": target.get("status"), "decision": decision,
            "top_score": top_score, "runner_up_score": runner_up,
            "high_score_coordinate_count": len(high_coords),
            "high_score_coordinate_clusters_150m": high_coord_clusters,
            "top_reasons": top_reasons,
            "candidates": [{
                "score": score, "ids": sorted(c["ids"]),
                "name": c["name"], "address": c["address"],
                "developer": c["developer"], "status": c["status"],
                "lat": c["lat"], "lng": c["lng"],
                "occurrences": c["occurrences"],
                "quarters": sorted(c["quarters"]),
                "sources": sorted(c["sources"]),
                "accepted_registry": c["accepted_registry"],
                "reasons": reasons,
            } for score, c, reasons in top],
        })

    summary = Counter(r["decision"] for r in results)
    payload = {
        "generated_at": "2026-08-06",
        "target_count": len(targets),
        "candidate_pool_count": len(pool),
        "summary": dict(summary),
        "results": results,
    }
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    with OUT_CSV.open("w", encoding="utf-8-sig", newline="") as f:
        fields = ["id", "name", "address", "developer", "status", "decision", "top_score",
                  "candidate_ids",
                  "candidate_name", "candidate_address", "candidate_developer", "candidate_status",
                  "candidate_lat", "candidate_lng", "candidate_occurrences", "candidate_sources"]
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for r in results:
            c = r["candidates"][0] if r["candidates"] else {}
            writer.writerow({
                **{k: r.get(k) for k in fields if k in r},
                "candidate_ids": "; ".join(c.get("ids", [])),
                "candidate_name": c.get("name"), "candidate_address": c.get("address"),
                "candidate_developer": c.get("developer"), "candidate_status": c.get("status"),
                "candidate_lat": c.get("lat"), "candidate_lng": c.get("lng"),
                "candidate_occurrences": c.get("occurrences"),
                "candidate_sources": "; ".join(c.get("sources", [])),
            })

    print(json.dumps(payload["summary"], ensure_ascii=False))


if __name__ == "__main__":
    main()
