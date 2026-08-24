"""Apply the independently corroborated GLA correction from wave 03 recheck.

The missing-data backlog is separate from point AUDIT statuses. This migration
updates only Park Legends B+; Alcon III and Park Legends A remain deferred
because their exact-grain source values conflict.
"""
from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LAYER_PATH = ROOT / "data" / "all_projects_layer.json"
CHECKED = "2026-08-24"
PROJECT_ID = "proj-103"
GLA = 48000
SOURCES = [
    "https://media.kf.expert/lenta_analytics/0/625/NF%20Group_%D0%A0%D1%8B%D0%BD%D0%BE%D0%BA%20%D0%BE%D1%84%D0%B8%D1%81%D0%BD%D0%BE%D0%B9%20%D0%BD%D0%B5%D0%B4%D0%B2%D0%B8%D0%B6%D0%B8%D0%BC%D0%BE%D1%81%D1%82%D0%B8.%20%D0%9C%D0%BE%D1%81%D0%BA%D0%B2%D0%B0.%201%20%D0%BA%D0%B2.%202023_rus.pdf",
    "https://ibcrealestate.ru/upload/iblock/a03/yggwy9btmm425vg83wh732mh2nv6q55r.pdf",
]
NOTE = (
    "GLA rechecked 2026-08-24: NF Group Research explicitly reports Park "
    "Legends A/B GLA 43,320/48,000 m2; IBC Real Estate/JLL independently "
    "reports the B+ project at 48,000 m2. Applied only the independently "
    f"matching B+ value. Sources: {SOURCES[0]} ; {SOURCES[1]}"
)


def main() -> None:
    layer = json.loads(LAYER_PATH.read_text(encoding="utf-8-sig"))
    matches = [row for row in layer if row.get("canonical_project_id") == PROJECT_ID]
    if len(matches) != 1 or matches[0].get("canonical_name") != "Парк Легенд класс В+":
        raise ValueError("identity drift for proj-103")
    row = matches[0]
    if row.get("gba") != GLA:
        raise ValueError(f"unexpected proj-103 GBA: {row.get('gba')!r}")
    row["gla"] = GLA
    row["source_count"] = max(2, int(row.get("source_count") or 0))
    row["last_verified_at"] = CHECKED
    existing = str(row.get("qa_notes") or "").strip()
    if NOTE not in existing:
        row["qa_notes"] = f"{existing} {NOTE}".strip()
    LAYER_PATH.write_text(
        json.dumps(layer, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print("updated proj-103 GLA=48000")


if __name__ == "__main__":
    main()
