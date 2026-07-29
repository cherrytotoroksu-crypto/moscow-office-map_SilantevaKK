"""Regression test: CHALET Пятницкая 40 — planned completion Q2 2028.

Guards the 2026-07-29 correction against regressing to any of the superseded
values ("2026", Q4 2026 / 202612, or "IV квартал 2027"), and against the project
being silently promoted to a delivered status or a later construction stage
without dated evidence.

Sources for the asserted values:
  * https://chalet40.moscow/about — "Срок сдачи: 2 кв. 2028 г."
  * https://mskguru.ru/news/15028-v-zamoskvoreche-startovalo-stroitelystvo-bk-pyatnickaya-40-shale
    (11.03.2026) — construction permit received, works starting.
"""

import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

BUILDING_NAME = "CHALET Пятницкая 40"
DATES_KEY = "chalet пятницкая 40"

EXPECTED_COMPLETION_YEAR = 2028
EXPECTED_COMPLETION_QUARTER = 2
EXPECTED_COMMISSION_Q = "202806"          # YYYYMM, month 06 == Q2
EXPECTED_CONSTRUCTION_START_Q = "202603"
EXPECTED_STATUS_Q2_2026 = "Строится"      # construction
EXPECTED_STAGE = "Начальный этап строительства"
EXPECTED_STAGE_AS_OF = "202606"

# Values that must never come back as the *current* planned completion.
SUPERSEDED_COMMISSION_VALUES = {"202612", "202712", "2026", "2027"}

PIPELINE_CUTOFF_YEAR = 2030               # "плановый ввод до 2030 включительно"

failures = []


def check(condition: bool, message: str) -> None:
    if not condition:
        failures.append(message)


def quarter_of(yyyymm: str) -> int:
    month = int(str(yyyymm)[4:6])
    return (month + 2) // 3


def load_classifier_block(html: str, decl: str, open_ch: str, close_ch: str, next_decl: str):
    start = html.index(decl)
    open_idx = html.index(open_ch, start)
    close_idx = html.rindex(close_ch, open_idx, html.index(next_decl))
    return json.loads(html[open_idx:close_idx + 1])


def main() -> None:
    # ---- data/building_dates.json -------------------------------------------
    dates = json.loads((REPO_ROOT / "data" / "building_dates.json").read_text(encoding="utf-8"))
    check(DATES_KEY in dates, f"'{DATES_KEY}' missing from data/building_dates.json")
    entry = dates.get(DATES_KEY, {})

    commission_q = entry.get("commission_q")
    check(
        commission_q == EXPECTED_COMMISSION_Q,
        f"building_dates commission_q = {commission_q!r}, expected {EXPECTED_COMMISSION_Q!r}",
    )
    check(
        commission_q not in SUPERSEDED_COMMISSION_VALUES,
        f"building_dates commission_q regressed to superseded value {commission_q!r}",
    )
    if commission_q and len(str(commission_q)) == 6:
        check(
            int(str(commission_q)[:4]) == EXPECTED_COMPLETION_YEAR,
            f"completion_year = {str(commission_q)[:4]}, expected {EXPECTED_COMPLETION_YEAR}",
        )
        check(
            quarter_of(commission_q) == EXPECTED_COMPLETION_QUARTER,
            f"completion_quarter = {quarter_of(commission_q)}, expected {EXPECTED_COMPLETION_QUARTER}",
        )

    check(
        entry.get("construction_start_q") == EXPECTED_CONSTRUCTION_START_Q,
        f"construction_start_q = {entry.get('construction_start_q')!r}, "
        f"expected {EXPECTED_CONSTRUCTION_START_Q!r}",
    )
    check(
        entry.get("stage") == EXPECTED_STAGE,
        f"stage = {entry.get('stage')!r}, expected {EXPECTED_STAGE!r}",
    )
    check(
        entry.get("stage_as_of") == EXPECTED_STAGE_AS_OF,
        f"stage_as_of = {entry.get('stage_as_of')!r}, expected {EXPECTED_STAGE_AS_OF!r}",
    )

    # ---- data/buildings_202606.json (Q2 2026 quarterly snapshot) -------------
    buildings = json.loads((REPO_ROOT / "data" / "buildings_202606.json").read_text(encoding="utf-8"))
    building = next((b for b in buildings if b.get("name") == BUILDING_NAME), None)
    check(building is not None, f"'{BUILDING_NAME}' missing from data/buildings_202606.json")
    if building is not None:
        check(
            str(building.get("year")) == str(EXPECTED_COMPLETION_YEAR),
            f"buildings_202606 year = {building.get('year')!r}, expected {EXPECTED_COMPLETION_YEAR}",
        )
        check(
            building.get("status") == EXPECTED_STATUS_Q2_2026,
            f"buildings_202606 status = {building.get('status')!r}, "
            f"expected {EXPECTED_STATUS_Q2_2026!r} (must not be promoted to delivered)",
        )

    # ---- classifier.html RAW_DATA -------------------------------------------
    html = (REPO_ROOT / "classifier.html").read_text(encoding="utf-8")
    raw_data = load_classifier_block(html, "const RAW_DATA = [", "[", "]", "const COLORMAP = {")
    row = next((r for r in raw_data if r.get("name") == BUILDING_NAME), None)
    check(row is not None, f"'{BUILDING_NAME}' missing from classifier.html RAW_DATA")
    if row is not None:
        check(
            row.get("commission_q") == EXPECTED_COMMISSION_Q,
            f"classifier commission_q = {row.get('commission_q')!r}, expected {EXPECTED_COMMISSION_Q!r}",
        )
        check(
            row.get("construction_start_q") == EXPECTED_CONSTRUCTION_START_Q,
            f"classifier construction_start_q = {row.get('construction_start_q')!r}, "
            f"expected {EXPECTED_CONSTRUCTION_START_Q!r}",
        )
        check(
            row.get("status") == EXPECTED_STATUS_Q2_2026,
            f"classifier status = {row.get('status')!r}, expected {EXPECTED_STATUS_Q2_2026!r}",
        )

        # ---- pipeline selection: planned completion through 2030 inclusive ---
        pipeline = [
            r for r in raw_data
            if r.get("commission_q")
            and len(str(r["commission_q"])) == 6
            and int(str(r["commission_q"])[:4]) <= PIPELINE_CUTOFF_YEAR
        ]
        check(
            any(r.get("name") == BUILDING_NAME for r in pipeline),
            f"'{BUILDING_NAME}' not selected by the 'planned completion through "
            f"{PIPELINE_CUTOFF_YEAR} inclusive' filter",
        )

    if failures:
        for message in failures:
            print(f"FAIL: {message}")
        sys.exit(1)

    print(json.dumps({
        "building": BUILDING_NAME,
        "completion_year": EXPECTED_COMPLETION_YEAR,
        "completion_quarter": EXPECTED_COMPLETION_QUARTER,
        "commission_q": EXPECTED_COMMISSION_Q,
        "construction_start_q": EXPECTED_CONSTRUCTION_START_Q,
        "q2_2026_status": EXPECTED_STATUS_Q2_2026,
        "stage": EXPECTED_STAGE,
        "in_pipeline_through_2030": True,
        "status": "PASS",
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
