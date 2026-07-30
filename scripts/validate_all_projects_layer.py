"""Validate the "all offices projects" layer without touching quarterly_supply.

Usage:
  python scripts/validate_all_projects_layer.py data/test_fixtures/all_projects_layer.sample.json

Не требует пакета jsonschema (по тому же принципу, что и
scripts/validate_remain_layer.py) — проверяет инварианты, которые защищают
модель: уникальность записей, правило Бадаевского (общий canonical_project_id,
разные canonical_building_id — это НЕ дубль), координаты в разумных пределах
Москвы, обязательную причину при project_status='Ещё не вышел в продажу',
непустой canonical_building_id при entity_grain='building', и то, что
запись не тащит встроенные лоты (это должно жить в quarterly_supply, не здесь).
"""

from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path
from typing import Any

PROJECT_STATUSES = {"В продаже", "Продажи завершены", "Ещё не вышел в продажу", "Не применяется"}
CONSTRUCTION_STATUSES = {"Проектируется", "Строится", "Введён", "Заморожен", "Отменён", "Не установлен"}
VERIFICATION_STATUSES = {"unverified", "under_review", "accepted", "blocked", "quarantine"}
CONFIDENCE = {"low", "medium", "high"}
GRAINS = {"project", "building"}
AREA_SCOPES = {"project", "building", "phase", "unknown"}
MARKET_CHANNELS = {"sale", "rent", "coworking", "bts", "off_market"}
GEOMETRY_QUALITY = {"house_exact", "geocoded_approx", "centroid", "unverified", "unknown"}
QA_STATUSES = {"ok", "conflict", "duplicate_suspect", "missing_required", "quarantine"}
PUBLIC_VISIBILITY = {"public", "internal_only"}
OFFER_NOT_STARTED_REASONS = {"Проектная стадия", "Нет подтверждённых лотов", "Продажи не раскрыты"}

REQUIRED = {
    "canonical_project_id", "entity_grain", "raw_name", "canonical_name",
    "project_status", "construction_status", "source", "source_date",
    "verification_status", "confidence", "public_visibility",
}

# Каналы, которые нельзя смешивать в одном агрегате (см. REMAIN_INTEGRATION_HANDOFF).
FORBIDDEN_KEYS = {"lots", "lot_rows", "sale_lots", "deal_rows", "rent_lots"}

MOSCOW_LAT = (54.0, 57.0)
MOSCOW_LNG = (35.0, 40.0)


def issue(row: int, message: str) -> str:
    return f"row {row}: {message}"


def validate(doc: Any) -> list[str]:
    errors: list[str] = []
    if not isinstance(doc, list):
        return ["root must be a JSON array"]

    seen_building_ids: dict[str, int] = {}
    project_grain_by_id: dict[str, set] = {}

    for row, item in enumerate(doc, 1):
        if not isinstance(item, dict):
            errors.append(issue(row, "record must be an object"))
            continue

        missing = REQUIRED - item.keys()
        if missing:
            errors.append(issue(row, f"missing required keys: {sorted(missing)}"))

        forbidden = FORBIDDEN_KEYS & item.keys()
        if forbidden:
            errors.append(issue(row, f"embedded lot payload forbidden here (belongs in quarterly_supply): {sorted(forbidden)}"))

        grain = item.get("entity_grain")
        if grain not in GRAINS:
            errors.append(issue(row, f"invalid entity_grain: {grain!r}"))

        cpid = item.get("canonical_project_id")
        if not isinstance(cpid, str) or not cpid.strip():
            errors.append(issue(row, "canonical_project_id must be a non-empty string"))

        cbid = item.get("canonical_building_id")
        if grain == "building" and not cbid:
            errors.append(issue(row, "entity_grain=building requires a non-null canonical_building_id"))

        # Дубли: одинаковый canonical_building_id дважды — реальная ошибка.
        # Одинаковый canonical_project_id у РАЗНЫХ canonical_building_id (Бадаевский) — это НЕ дубль.
        if cbid:
            key = f"{cpid}::{cbid}"
            if key in seen_building_ids:
                errors.append(issue(row, f"duplicate canonical_building_id {cbid!r} for project {cpid!r} (also row {seen_building_ids[key]})"))
            else:
                seen_building_ids[key] = row
        elif grain == "project":
            if cpid in seen_building_ids:
                errors.append(issue(row, f"duplicate project-level canonical_project_id {cpid!r} (also row {seen_building_ids[cpid]})"))
            else:
                seen_building_ids[cpid] = row

        # Если один canonical_project_id встречается и как 'project', и как 'building' —
        # не ошибка сама по себе (может быть отдельная строка-итог + корпуса), но стоит видеть в предупреждениях.
        project_grain_by_id.setdefault(cpid, set()).add(grain)

        raw_name = item.get("raw_name")
        canonical_name = item.get("canonical_name")
        if not isinstance(raw_name, str) or not raw_name.strip():
            errors.append(issue(row, "raw_name must be a non-empty string"))
        if not isinstance(canonical_name, str) or not canonical_name.strip():
            errors.append(issue(row, "canonical_name must be a non-empty string"))

        pstatus = item.get("project_status")
        if pstatus not in PROJECT_STATUSES:
            errors.append(issue(row, f"invalid project_status: {pstatus!r}"))
        if pstatus == "Ещё не вышел в продажу":
            reason = item.get("offer_not_started_reason")
            if reason not in OFFER_NOT_STARTED_REASONS:
                errors.append(issue(row, "project_status='Ещё не вышел в продажу' requires a valid offer_not_started_reason"))

        cstatus = item.get("construction_status")
        if cstatus not in CONSTRUCTION_STATUSES:
            errors.append(issue(row, f"invalid construction_status: {cstatus!r}"))

        vstatus = item.get("verification_status")
        if vstatus not in VERIFICATION_STATUSES:
            errors.append(issue(row, f"invalid verification_status: {vstatus!r}"))

        confidence = item.get("confidence")
        if confidence not in CONFIDENCE:
            errors.append(issue(row, f"invalid confidence: {confidence!r}"))

        visibility = item.get("public_visibility")
        if visibility not in PUBLIC_VISIBILITY:
            errors.append(issue(row, f"invalid public_visibility: {visibility!r}"))

        # unverified-записи не должны утекать в публичный слой без явного пересмотра.
        if visibility == "public" and vstatus == "unverified":
            errors.append(issue(row, "public_visibility='public' with verification_status='unverified' — should be internal_only until reviewed"))

        source_date = item.get("source_date")
        if isinstance(source_date, str):
            try:
                date.fromisoformat(source_date)
            except ValueError:
                errors.append(issue(row, "source_date must be ISO date YYYY-MM-DD"))
        else:
            errors.append(issue(row, "source_date must be a string"))

        lat = item.get("latitude")
        lng = item.get("longitude")
        if lat is not None:
            if not isinstance(lat, (int, float)) or not (MOSCOW_LAT[0] <= lat <= MOSCOW_LAT[1]):
                errors.append(issue(row, f"latitude {lat!r} outside Moscow-region sanity range"))
        if lng is not None:
            if not isinstance(lng, (int, float)) or not (MOSCOW_LNG[0] <= lng <= MOSCOW_LNG[1]):
                errors.append(issue(row, f"longitude {lng!r} outside Moscow-region sanity range"))

        geom_q = item.get("geometry_quality")
        if geom_q is not None and geom_q not in GEOMETRY_QUALITY:
            errors.append(issue(row, f"invalid geometry_quality: {geom_q!r}"))

        area_scope = item.get("area_scope")
        if area_scope is not None and area_scope not in AREA_SCOPES:
            errors.append(issue(row, f"invalid area_scope: {area_scope!r}"))
        has_area = any(item.get(k) is not None for k in ("gba", "gla", "office_area"))
        if has_area and area_scope in (None, "unknown"):
            # Не ошибка (реальные данные часто именно такие), но именно это и есть повод для qa_status=conflict.
            if item.get("qa_status") == "ok":
                errors.append(issue(row, "has area (gba/gla/office_area) with area_scope unknown but qa_status='ok' — should be flagged, not 'ok'"))

        channels = item.get("market_channel")
        if channels is not None:
            if not isinstance(channels, list) or any(c not in MARKET_CHANNELS for c in channels):
                errors.append(issue(row, f"invalid market_channel: {channels!r}"))

        qa_status = item.get("qa_status")
        if qa_status is not None and qa_status not in QA_STATUSES:
            errors.append(issue(row, f"invalid qa_status: {qa_status!r}"))

        external_only = item.get("external_only")
        if external_only is True and visibility == "public" and vstatus in ("unverified", "under_review"):
            errors.append(issue(row, "external_only record not yet reviewed should not be public_visibility='public'"))

    return errors


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: python scripts/validate_all_projects_layer.py records.json", file=sys.stderr)
        return 2
    path = Path(sys.argv[1])
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # pragma: no cover - CLI diagnostic
        print(f"ERROR: cannot read {path}: {exc}", file=sys.stderr)
        return 2
    errors = validate(payload)
    if errors:
        print(f"FAIL: {len(errors)} issue(s)")
        print("\n".join(errors))
        return 1
    print(f"PASS: {len(payload)} project/building record(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
