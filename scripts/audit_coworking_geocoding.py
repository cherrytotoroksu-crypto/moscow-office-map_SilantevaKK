"""
Read-only аудит гео/id-стабильности гибких офисов (data/coworking_{quarter}.json).

Проверяет по каждому кварталу и по всем кварталам вместе:
  - дубли id внутри одного файла (буквально повторяющиеся строки id);
  - одинаковые координаты у РАЗНЫХ id (подозрение на искусственное дробление
    одного сайта на несколько записей);
  - один и тот же id, но разные координаты в разных кварталах — считает
    расстояние (haversine) и классифицирует:
        <= 100 м   — ok (геокодирование туда-сюда, шум)
        > 100 м    — conflict
        > 300 м    — quarantine
        > 1000 м   — hard_error
  - несовпадение адреса при смене координат тем же id.

Не меняет data/. Пишет quarantine_coworking_geocoding.csv/json.
"""
import csv
import json
import math
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = REPO_ROOT / "data"

CONFLICT_M = 100
QUARANTINE_M = 300
HARD_ERROR_M = 1000


def haversine_m(lat1, lon1, lat2, lon2):
    R = 6371000
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlmb / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


def load_quarter(path):
    with open(path, encoding="utf-8-sig") as f:
        data = json.load(f)
    return [r for r in data if isinstance(r, dict)]


def classify(distance_m):
    if distance_m <= CONFLICT_M:
        return "ok"
    if distance_m <= QUARANTINE_M:
        return "conflict"
    if distance_m <= HARD_ERROR_M:
        return "quarantine"
    return "hard_error"


def main():
    files = sorted(DATA_DIR.glob("coworking_*.json"))
    by_quarter = {}
    for f in files:
        q = f.stem.replace("coworking_", "")
        try:
            by_quarter[q] = load_quarter(f)
        except Exception as e:
            print(f"SKIP {f.name}: {e}")

    findings = []

    # 1. дубли id внутри одного файла
    for q, rows in by_quarter.items():
        seen = {}
        for r in rows:
            rid = r.get("id")
            seen.setdefault(rid, []).append(r)
        for rid, group in seen.items():
            if len(group) > 1:
                findings.append({
                    "type": "duplicate_id_within_quarter", "quarter": q, "id": rid,
                    "count": len(group),
                    "names": [g.get("name") for g in group],
                    "addresses": [g.get("address") for g in group],
                    "coords": [[g.get("lat"), g.get("lng")] for g in group],
                })

    # 2. одинаковые координаты у разных id, в пределах одного квартала
    for q, rows in by_quarter.items():
        by_coord = {}
        for r in rows:
            lat, lng = r.get("lat"), r.get("lng")
            if lat is None or lng is None:
                continue
            key = (round(lat, 5), round(lng, 5))
            by_coord.setdefault(key, []).append(r)
        for coord, group in by_coord.items():
            ids = {g.get("id") for g in group}
            if len(ids) > 1:
                findings.append({
                    "type": "same_coord_different_ids", "quarter": q, "coord": list(coord),
                    "ids": sorted(ids, key=lambda x: (x is None, x)),
                    "names": [g.get("name") for g in group],
                    "networks": [g.get("network") for g in group],
                    "addresses": [g.get("address") for g in group],
                })

    # 3. один id, координаты дрейфуют между кварталами
    id_history = {}
    for q in sorted(by_quarter.keys()):
        for r in by_quarter[q]:
            rid = r.get("id")
            if rid is None:
                continue
            id_history.setdefault(rid, []).append((q, r))

    for rid, history in id_history.items():
        if len(history) < 2:
            continue
        for i in range(1, len(history)):
            q_prev, r_prev = history[i - 1]
            q_cur, r_cur = history[i]
            lat1, lng1 = r_prev.get("lat"), r_prev.get("lng")
            lat2, lng2 = r_cur.get("lat"), r_cur.get("lng")
            if None in (lat1, lng1, lat2, lng2):
                continue
            dist = haversine_m(lat1, lng1, lat2, lng2)
            severity = classify(dist)
            if severity != "ok":
                findings.append({
                    "type": "coordinate_drift_same_id", "id": rid,
                    "quarter_from": q_prev, "quarter_to": q_cur,
                    "distance_m": round(dist, 1), "severity": severity,
                    "name_from": r_prev.get("name"), "name_to": r_cur.get("name"),
                    "address_from": r_prev.get("address"), "address_to": r_cur.get("address"),
                    "same_address": (r_prev.get("address") or "").strip() == (r_cur.get("address") or "").strip(),
                    "coord_from": [lat1, lng1], "coord_to": [lat2, lng2],
                })

    out_json = REPO_ROOT / "qa_quarantine_coworking_geocoding.json"
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump({
            "note": "Read-only аудит. data/coworking_*.json НЕ менялись. "
                    "Пороги: conflict>100м, quarantine>300м, hard_error>1000м (см. заголовок скрипта).",
            "quarters_checked": sorted(by_quarter.keys()),
            "findings": findings,
        }, f, ensure_ascii=False, indent=2)

    out_csv = REPO_ROOT / "qa_quarantine_coworking_geocoding.csv"
    with open(out_csv, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["type", "id", "quarter/quarter_from", "quarter_to", "distance_m", "severity", "detail"])
        for item in findings:
            w.writerow([
                item["type"],
                item.get("id", ""),
                item.get("quarter", item.get("quarter_from", "")),
                item.get("quarter_to", ""),
                item.get("distance_m", ""),
                item.get("severity", ""),
                json.dumps(item, ensure_ascii=False),
            ])

    def safe_print(s):
        print(s.encode("utf-8", "replace").decode(sys.stdout.encoding or "utf-8", "replace"))

    by_type = {}
    for f_ in findings:
        by_type.setdefault(f_["type"], 0)
        by_type[f_["type"]] += 1
    safe_print(f"Кварталов проверено: {len(by_quarter)}")
    safe_print(f"Всего находок: {len(findings)}")
    for t, n in by_type.items():
        safe_print(f"  {t}: {n}")
    hard_errors = [f_ for f_ in findings if f_.get("severity") == "hard_error"]
    safe_print(f"\nhard_error (>{HARD_ERROR_M} м между кварталами, тот же id):")
    for f_ in hard_errors:
        safe_print(f"  id={f_['id']} {f_['quarter_from']}->{f_['quarter_to']}: {f_['distance_m']} м, "
                    f"{f_['name_from']!r} @ {f_['address_from']!r} -> {f_['name_to']!r} @ {f_['address_to']!r}")
    print(f"\nWritten: {out_json.name}, {out_csv.name}")


if __name__ == "__main__":
    main()
