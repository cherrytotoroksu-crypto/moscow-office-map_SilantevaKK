"""
Applies confirmed coordinate/address corrections to data/coworking_202606.json
for the 10 previously-unconfirmed hard-error ids from current_state_audit.md.

Method for each: WebSearch (operator's own site / listing aggregator) +
WebFetch (coordinates from Yandex Maps / 2GIS page), same method already
used for QA-013/014/015 in qa_handoff.json. Sources cited per id below.

2 of the 10 turned out to be ALREADY CORRECT in 202606 (id 156, 238) - the
"jump" was 202603 being wrong, not 202606. No changes for those two.

8 needed a fix. Each gets a BRAND NEW id (9001-9008) instead of reusing the
old one, per instruction "присвой разные id, чтобы не путаться" - the old
id stays on the (now known-wrong) historical rows in earlier quarters
untouched, so nothing about old snapshots is silently rewritten, and the
new id can't be confused with the old contaminated lineage. old_id is kept
on the row as `prev_id` for traceability.

Writes a .bak copy of the original file before editing. Does not touch any
other quarter's file.
"""
import json
import shutil
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
TARGET = REPO_ROOT / "data" / "coworking_202606.json"

# old_id -> (new_id, lat, lng, address_or_None, source_note)
FIXES = {
    118: (9001, 55.699467, 37.625595,
          None,
          "Yandex Maps listing for Meeting Point, Варшавское ш. 9с1 (Даниловская мануфактура) — "
          "https://yandex.com/maps/org/meeting_point/163476730515"),
    119: (9002, 55.757718, 37.617069,
          None,
          "Yandex Maps listing for Meeting Point, ул. Охотный Ряд, 2 (Гостиница Москва) — "
          "https://yandex.com/maps/org/meeting_point/1370191343/"),
    211: (9003, 55.696007, 37.625513,
          None,
          "Yandex Maps house page, Новоданиловская наб., 10 (Даниловский Форт) — "
          "https://yandex.com/maps/213/moscow/house/novodanilovskaya_naberezhnaya_10/"),
    213: (9004, 55.711687, 37.581632,
          None,
          "Yandex Maps listing for Рабочая Станция (Парк Горького), Ленинский пр-т, 30А — "
          "https://yandex.com/maps/org/rabochaya_stantsiya_park_gorkogo/1247847303/"),
    218: (9005, 55.776527, 37.679404,
          "Спартаковская площадь, 16/15с6",
          "Real address differs from what was stored ('Бауманская ул. 15' — informal/wrong street). "
          "2GIS listing for Smart Yard, Спартаковская площадь, 16/15с6 (Басманный двор) — "
          "https://2gis.ru/moscow/firm/... via WebSearch 'Smart Yard коворкинг Бауманская улица 15'"),
    222: (9006, 55.692387, 37.529017,
          None,
          "2GIS listing for Regus/Регус Капитолий, Вернадского пр-кт, 6 — "
          "https://2gis.ru/moscow/firm/70000001036400312"),
    235: (9007, 55.728652, 37.645578,
          None,
          "2GIS listing for Know Where, Кожевническая ул., 14 (БЦ Black and White) — "
          "https://2gis.ru/moscow/firm/70000001062720925"),
    256: (9008, 55.730426, 37.634793,
          "Павелецкая площадь, 2с1",
          "Yandex Maps house page for Павелецкая площадь, 2с1 (matches the coordinate the corrupted "
          "202603 row already had before a 202606 data-cleanup pass accidentally moved it ~2km) — "
          "search 'Павелецкая площадь, 2' координаты yandex maps"),
}

# Confirmed-correct-as-is in 202606 — no data change, just documented.
NO_CHANGE_CONFIRMED_GOOD = {
    156: "Multispace Павелецкая, 1-й Щипковский пер. 5 area — 202606 coord (55.722593,37.632035) "
         "matches Yandex house-page coord (55.722532,37.631990) within 10m. 202603 was wrong (Dinamo area).",
    238: "KW Симонов, ул. Ленинская Слобода, 26с5 — 202606 coord (55.711316,37.652777) matches "
         "2GIS listing (55.711269,37.652752) within 6m. 202603 had the known bad stub + blank address.",
}


def main():
    backup = TARGET.with_suffix(TARGET.suffix + ".bak_geocoding_fix")
    if not backup.exists():
        shutil.copy2(TARGET, backup)
        print(f"Backup written: {backup.name}")

    with open(TARGET, "rb") as f:
        raw_bytes = f.read()
    has_bom = raw_bytes.startswith(b"\xef\xbb\xbf")

    with open(TARGET, encoding="utf-8-sig") as f:
        rows = json.load(f)

    changed = []
    for row in rows:
        old_id = row.get("id")
        if old_id in FIXES:
            new_id, lat, lng, address, note = FIXES[old_id]
            before = {"id": old_id, "address": row.get("address"), "lat": row.get("lat"), "lng": row.get("lng")}
            row["prev_id"] = old_id
            row["id"] = new_id
            row["lat"] = lat
            row["lng"] = lng
            if address is not None:
                row["address"] = address
            row["geocoding_fix_source"] = note
            changed.append({"before": before, "after": {"id": new_id, "address": row.get("address"),
                                                          "lat": lat, "lng": lng}})

    out_bytes = json.dumps(rows, ensure_ascii=False, indent=2).encode("utf-8")
    if has_bom:
        out_bytes = b"\xef\xbb\xbf" + out_bytes
    with open(TARGET, "wb") as f:
        f.write(out_bytes)

    print(f"Изменено строк: {len(changed)}")
    for c in changed:
        print(f"  id {c['before']['id']} -> {c['after']['id']}: "
              f"({c['before']['lat']},{c['before']['lng']}) -> ({c['after']['lat']},{c['after']['lng']})")
    print(f"\nБез изменений (подтверждено корректно): {sorted(NO_CHANGE_CONFIRMED_GOOD.keys())}")


if __name__ == "__main__":
    main()
