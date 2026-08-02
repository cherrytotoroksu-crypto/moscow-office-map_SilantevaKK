"""
Аудит KPI "Продажа офисов" по data/lots_{quarter}.json.

Не меняет исходные файлы. Печатает таблицу сверки по всем кварталам и
(для указанного квартала, по умолчанию 202606) пишет qa_quarantine_lots_
<quarter>.json с найденными дублями/подозрительными строками и причиной,
без удаления их из data/.

Запуск:
    python scripts/audit_sale_lots_kpi.py            # все кварталы, quarantine для 202606
    python scripts/audit_sale_lots_kpi.py 202603      # quarantine для другого квартала
"""
import json
import sys
from collections import Counter
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = REPO_ROOT / "data"

# Порог для "подозрительно большого лота" — не подтверждённая причина
# исключения, только флаг для ручной проверки (см. отчёт).
MEGA_LOT_THRESHOLD_M2 = 3000
# Порог схожести двух зданий, чтобы считать их дублем разных названий
# одного и того же дома: доля площадей, совпадающих с точностью до 1 м²
# (лоты источника даны то округлённо, то нет — 58854.6 vs 58854.0).
DUP_BUILDING_MIN_OVERLAP = 0.9


def load_raw(quarter_id):
    path = DATA_DIR / f"lots_{quarter_id}.json"
    with open(path, encoding="utf-8-sig") as f:
        return json.load(f)


def flatten(raw):
    rows = []
    for building, lots in raw.items():
        for lot in lots:
            rows.append({"building": building, **lot})
    return rows


def find_exact_duplicate_rows(raw):
    """Строки, буквально повторяющиеся 2+ раза внутри одного здания."""
    dupes = []
    for building, lots in raw.items():
        counts = Counter(json.dumps(l, sort_keys=True) for l in lots)
        for key, n in counts.items():
            if n > 1:
                dupes.append({"building": building, "row": json.loads(key), "extra_count": n - 1})
    return dupes


def find_duplicate_buildings(raw):
    """Здания с почти идентичным набором площадей лотов под разными
    названиями (вероятно один и тот же дом, записанный дважды)."""
    names = list(raw.keys())
    areas = {
        b: sorted(round(l["area"], 0) for l in lots if l.get("area"))
        for b, lots in raw.items()
    }
    pairs = []
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            a, b = names[i], names[j]
            sa, sb = areas[a], areas[b]
            if len(sa) < 5 or abs(len(sa) - len(sb)) > 2:
                continue
            matched = 0
            sb_pool = list(sb)
            for v in sa:
                for k, w in enumerate(sb_pool):
                    if abs(v - w) <= 1:
                        matched += 1
                        del sb_pool[k]
                        break
            overlap = matched / min(len(sa), len(sb))
            if overlap >= DUP_BUILDING_MIN_OVERLAP:
                pairs.append({
                    "building_a": a, "building_b": b,
                    "lots_a": len(sa), "lots_b": len(sb),
                    "matched_areas": matched, "overlap_ratio": round(overlap, 3),
                    "area_sum_a": sum(sa), "area_sum_b": sum(sb),
                })
    return pairs


def find_mega_lots(raw, threshold=MEGA_LOT_THRESHOLD_M2):
    out = []
    for building, lots in raw.items():
        for lot in lots:
            a = lot.get("area")
            if a and a > threshold:
                out.append({"building": building, **lot})
    return out


def find_uniform_size_clusters(raw, min_count=5):
    """Здания, где N>=min_count лотов имеют ОДИНАКОВУЮ площадь — похоже на
    схематичные/нерасшифрованные строки, а не индивидуальные лоты."""
    out = []
    for building, lots in raw.items():
        areas = [l.get("area") for l in lots if l.get("area")]
        counts = Counter(areas)
        for area, n in counts.items():
            if n >= min_count:
                out.append({"building": building, "area": area, "count": n})
    return out


def reconcile_quarter(quarter_id):
    raw = load_raw(quarter_id)
    rows = flatten(raw)
    exact_dupes = find_exact_duplicate_rows(raw)
    dup_buildings = find_duplicate_buildings(raw)
    mega_lots = find_mega_lots(raw)
    uniform_clusters = find_uniform_size_clusters(raw)

    total_area = sum((r.get("area") or 0) for r in rows)
    total_value = sum((r.get("total") or 0) for r in rows)
    weighted_price = total_value / total_area if total_area else None

    return {
        "quarter": quarter_id,
        "raw_rows": len(rows),
        "buildings_raw": len(raw),
        "area_sum_raw": round(total_area, 1),
        "value_sum_raw": round(total_value, 1),
        "weighted_price_raw": round(weighted_price, 2) if weighted_price else None,
        "exact_duplicate_rows": sum(d["extra_count"] for d in exact_dupes),
        "exact_duplicate_groups": len(exact_dupes),
        "suspected_duplicate_buildings": len(dup_buildings),
        "duplicate_buildings_detail": dup_buildings,
        "mega_lots_over_threshold": len(mega_lots),
        "mega_lots_area_sum": round(sum(l.get("area") or 0 for l in mega_lots), 1),
        "uniform_size_clusters": uniform_clusters,
    }


def main():
    quarters = sorted(p.stem.replace("lots_", "") for p in DATA_DIR.glob("lots_*.json"))
    target_quarter = sys.argv[1] if len(sys.argv) > 1 else "202606"

    print(f"{'квартал':<8} {'зданий':>7} {'строк':>7} {'площадь, м2':>14} {'ц.взв, руб/м2':>14} {'points дублей':>14} {'дубли-здания':>13} {'мега-лотов':>11}")
    table = []
    for q in quarters:
        r = reconcile_quarter(q)
        table.append(r)
        print(f"{q:<8} {r['buildings_raw']:>7} {r['raw_rows']:>7} {r['area_sum_raw']:>14,.1f} "
              f"{(r['weighted_price_raw'] or 0):>14,.0f} {r['exact_duplicate_rows']:>14} "
              f"{r['suspected_duplicate_buildings']:>13} {r['mega_lots_over_threshold']:>11}")

    target = next(r for r in table if r["quarter"] == target_quarter)
    def safe_print(s):
        print(s.encode("utf-8", "replace").decode(sys.stdout.encoding or "utf-8", "replace"))

    safe_print("\n=== Подозреваемые здания-дубли (" + target_quarter + ") ===")
    for d in target["duplicate_buildings_detail"]:
        safe_print(f"  {d['building_a']!r} <-> {d['building_b']!r}: "
              f"{d['matched_areas']}/{min(d['lots_a'], d['lots_b'])} площадей совпадают "
              f"(overlap={d['overlap_ratio']}), суммы {d['area_sum_a']:.1f} vs {d['area_sum_b']:.1f} m2")

    safe_print(f"\n=== Однородные кластеры (>=5 лотов одинаковой площади), {target_quarter} ===")
    for c in target["uniform_size_clusters"]:
        safe_print(f"  {c['building']!r}: {c['count']} лотов по {c['area']} m2")

    out_path = REPO_ROOT / f"qa_quarantine_lots_{target_quarter}.json"
    quarantine = {
        "quarter": target_quarter,
        "generated_by": "scripts/audit_sale_lots_kpi.py",
        "note": "Диагностика: source data/lots_*.json НЕ менялись. Дубли зданий и мега-лоты "
                "здесь только ПОМЕЧЕНЫ для ручного подтверждения, не исключены из расчётов.",
        "exact_duplicate_rows": find_exact_duplicate_rows(load_raw(target_quarter)),
        "suspected_duplicate_buildings": target["duplicate_buildings_detail"],
        "mega_lots_over_threshold_m2": MEGA_LOT_THRESHOLD_M2,
        "mega_lots": find_mega_lots(load_raw(target_quarter)),
        "uniform_size_clusters": target["uniform_size_clusters"],
    }
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(quarantine, f, ensure_ascii=False, indent=2)
    print(f"\nQuarantine написан: {out_path.name}")


if __name__ == "__main__":
    main()
