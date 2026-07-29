"""Regression test: Moscow scope / city boundary guard.

Two non-Moscow rows ("Европейский Берег (Новосибирск)" — a Novosibirsk branch,
and "Астана, Сыганак ул. 60/4" — an Astana branch of the same "Практик" network)
were mixed into the Moscow dataset by an import error and had been parked on a
Red Square placeholder coordinate (55.755819, 37.617644). They are now tagged
out_of_scope with an explicit `city`, stripped of fabricated Moscow coordinates
and geo-fields, excluded from the rendered table, and removed from the quarterly
coworking file so they cannot appear on the map.

This test stops any such row from silently re-entering the active Moscow set.

The four rows that used to sit on the same Red Square placeholder point while
still being genuine Moscow addresses (Мой Кабинет / Атмосфера x3) were given
real house-level coordinates on 2026-07-29 (Codex COORDINATE_PLACEHOLDER_RECHECK,
see classifier.html NOTES). This test now asserts active_rows_still_on_placeholder
stays at 0 so a future data refresh cannot silently regress them back onto the
placeholder. See QUARANTINE_2026-07-29.md.
"""

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

# Moscow incl. TiNAO/New Moscow, with a small margin.
MOSCOW_LAT = (55.10, 56.05)
MOSCOW_LNG = (36.75, 38.00)

PLACEHOLDER = (55.755819, 37.617644)
PLACEHOLDER_EPS = 1e-6

# Entities proven to belong to other cities — must never be active again.
KNOWN_OUT_OF_SCOPE = {
    "Европейский Берег (Новосибирск)": "Новосибирск",
    "Астана": "Астана",
}

failures = []


def check(condition: bool, message: str) -> None:
    if not condition:
        failures.append(message)


def in_moscow(lat, lng) -> bool:
    return (MOSCOW_LAT[0] <= lat <= MOSCOW_LAT[1]) and (MOSCOW_LNG[0] <= lng <= MOSCOW_LNG[1])


def load_raw_data(html: str):
    start = html.index("const RAW_DATA = [")
    open_idx = html.index("[", start)
    close_idx = html.rindex("]", open_idx, html.index("const COLORMAP = {"))
    return json.loads(html[open_idx:close_idx + 1])


def main() -> None:
    html = (REPO_ROOT / "classifier.html").read_text(encoding="utf-8")
    raw_data = load_raw_data(html)

    # ---- the render path must filter out_of_scope out ------------------------
    check(
        "const ACTIVE_DATA = RAW_DATA.filter(r => !r.out_of_scope);" in html,
        "classifier.html no longer derives ACTIVE_DATA by filtering out_of_scope",
    )
    check(
        "for (const row of RAW_DATA)" not in html,
        "classifier.html still iterates RAW_DATA directly somewhere "
        "(must use ACTIVE_DATA so out-of-scope rows cannot render)",
    )

    active = [r for r in raw_data if not r.get("out_of_scope")]
    inactive = [r for r in raw_data if r.get("out_of_scope")]

    # ---- known non-Moscow entities are tagged and inactive -------------------
    for name_orig, city in KNOWN_OUT_OF_SCOPE.items():
        matches = [r for r in raw_data if r.get("name_orig") == name_orig]
        check(bool(matches), f"'{name_orig}' not found in RAW_DATA at all")
        for row in matches:
            check(
                row.get("out_of_scope") is True,
                f"'{name_orig}' is not tagged out_of_scope",
            )
            check(
                row.get("city") == city,
                f"'{name_orig}' city = {row.get('city')!r}, expected {city!r}",
            )
            check(
                row.get("lat") is None and row.get("lng") is None,
                f"'{name_orig}' still carries a fabricated coordinate "
                f"({row.get('lat')}, {row.get('lng')})",
            )
            for geo in ("ao", "raion", "zone", "submarket", "bizFormed"):
                check(
                    row.get(geo) is None,
                    f"'{name_orig}' still carries a fabricated Moscow {geo} = {row.get(geo)!r}",
                )

    # ---- every active row with coordinates must sit inside Moscow -----------
    for row in active:
        lat, lng = row.get("lat"), row.get("lng")
        if lat is None or lng is None:
            continue
        check(
            in_moscow(lat, lng),
            f"active row '{row.get('name')}' is outside Moscow bounds ({lat}, {lng})",
        )

    # ---- an out-of-scope row must never keep a coordinate -------------------
    for row in inactive:
        check(
            row.get("lat") is None and row.get("lng") is None,
            f"out_of_scope row '{row.get('name')}' still has a coordinate",
        )

    # ---- quarterly data files: nothing outside Moscow, no ghost re-entry ----
    for path in sorted((REPO_ROOT / "data").glob("buildings_*.json")) + \
                sorted((REPO_ROOT / "data").glob("coworking_2*.json")):
        # some quarterly files carry a UTF-8 BOM; utf-8-sig reads both variants
        records = json.loads(path.read_text(encoding="utf-8-sig"))
        for rec in records:
            name = rec.get("name", "")
            check(
                name not in KNOWN_OUT_OF_SCOPE,
                f"{path.name}: non-Moscow entity '{name}' is back in a quarterly file",
            )
            lat, lng = rec.get("lat"), rec.get("lng")
            if lat is None or lng is None:
                continue
            check(
                in_moscow(lat, lng),
                f"{path.name}: '{name}' is outside Moscow bounds ({lat}, {lng})",
            )

    placeholder_active = sum(
        1 for r in active
        if r.get("lat") is not None
        and abs(r["lat"] - PLACEHOLDER[0]) < PLACEHOLDER_EPS
        and abs(r["lng"] - PLACEHOLDER[1]) < PLACEHOLDER_EPS
    )

    check(
        placeholder_active == 0,
        f"{placeholder_active} active Moscow row(s) are back on the Red Square "
        "placeholder point — real coordinates were regressed",
    )

    if failures:
        for message in failures:
            print(f"FAIL: {message}")
        sys.exit(1)

    print(json.dumps({
        "raw_data_rows": len(raw_data),
        "active_moscow_rows": len(active),
        "out_of_scope_rows": len(inactive),
        "out_of_scope_cities": sorted({r.get("city") for r in inactive if r.get("city")}),
        "active_rows_still_on_placeholder": placeholder_active,
        "status": "PASS",
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
