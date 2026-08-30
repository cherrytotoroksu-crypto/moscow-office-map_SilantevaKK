"""Controlled sync, read-only mapping step (steps 2-3 of the 2026-08-30 sync
request): match data/unified_classifier_audited_2026-08-27.json (714 rows,
per-record QA source of truth for classifier.html) against
data/all_projects_layer.json (393 rows after fix_coworking_id_sync_merges.py,
the project/building registry) WITHOUT merging or writing to either file.

Matching contract (per the request):
  - normalized name + normalized address + corpus/tower token + legacy_ids
    are the matching keys.
  - coordinates are corroboration only, never a tie-breaker on their own.
  - a classifier row with no active market_channel (no live quarterly sale/
    rent/coworking offer) or entity_type=residential_complex_with_commercial_infrastructure
    is out of scope for the quarterly office-buildings layer by definition
    -> excluded_from_quarterly_layer, not "unmatched".

Output statuses: exact_match, probable_match, conflict, new_record,
excluded_from_quarterly_layer.

Run: python scripts/build_classifier_registry_mapping.py
Writes: outputs/classifier_registry_mapping_2026-08-30.json (full report)
        outputs/classifier_registry_mapping_2026-08-30_summary.md (counts)
"""
from __future__ import annotations

import json
import re
from collections import defaultdict
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
from unified_building_identity import normalize_label, normalize_address  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
CLASSIFIER_PATH = ROOT / "data" / "unified_classifier_audited_2026-08-27.json"
REGISTRY_PATH = ROOT / "data" / "all_projects_layer.json"
OUT_JSON = ROOT / "outputs" / "classifier_registry_mapping_2026-08-30.json"
OUT_MD = ROOT / "outputs" / "classifier_registry_mapping_2026-08-30_summary.md"

CORPUS_RE = re.compile(
    r"(?:башня|корпус|корп|к|очередь|оч|блок|литер)\.?\s*([ivx]+|\d+)",
    re.IGNORECASE,
)
ROMAN = {"i": 1, "ii": 2, "iii": 3, "iv": 4, "v": 5, "vi": 6}


def corpus_token(*texts):
    """Best-effort corpus/tower/phase token, or None if the name/address
    carries no such qualifier. Used only to disambiguate SAME-name
    candidates, never to match on its own."""
    for text in texts:
        if not text:
            continue
        m = CORPUS_RE.search(str(text))
        if m:
            tok = m.group(1).lower()
            return str(ROMAN.get(tok, tok))
    return None


def coord_close(a, b, tolerance_deg=0.001):  # ~110m at Moscow's latitude
    la, lo = a.get("latitude"), a.get("longitude")
    lb, lob = b.get("latitude"), b.get("longitude")
    if None in (la, lo, lb, lob):
        return False
    return abs(la - lb) <= tolerance_deg and abs(lo - lob) <= tolerance_deg


def main():
    classifier = json.loads(CLASSIFIER_PATH.read_text(encoding="utf-8"))["records"]
    registry = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))

    for r in registry:
        r["_norm_name"] = normalize_label(r.get("canonical_name"))
        r["_norm_addr"] = normalize_address(r.get("address"))
        r["_corpus"] = corpus_token(r.get("canonical_name"), r.get("address"))

    by_name = defaultdict(list)
    for r in registry:
        by_name[r["_norm_name"]].append(r)

    legacy_lookup = {}
    for r in registry:
        for lid in (r.get("legacy_ids") or []):
            legacy_lookup[str(lid)] = r

    report = []
    for c in classifier:
        entry = {
            "unified_id": c.get("unified_id"),
            "canonical_no": c.get("canonical_no"),
            "name": c.get("name"),
            "address": c.get("address"),
        }

        market_channel = c.get("market_channel") or []
        entity_type = c.get("entity_type")
        if not market_channel or entity_type == "residential_complex_with_commercial_infrastructure":
            entry["status"] = "excluded_from_quarterly_layer"
            entry["reason"] = (
                "no active quarterly market_channel" if not market_channel
                else f"entity_type={entity_type} (not an office project)"
            )
            report.append(entry)
            continue

        c_norm_name = normalize_label(c.get("name"))
        c_norm_addr = normalize_address(c.get("address"))
        c_corpus = corpus_token(c.get("name"), c.get("address"))

        # 1) direct legacy_id hit (classifier legacy_ids reference an old
        #    proj-N/UC-id already present in the registry's own legacy_ids)
        legacy_hit = None
        for lid in (c.get("legacy_ids") or []):
            if str(lid) in legacy_lookup:
                legacy_hit = legacy_lookup[str(lid)]
                break

        candidates = by_name.get(c_norm_name, [])

        if legacy_hit is not None and (not candidates or legacy_hit in candidates):
            entry["status"] = "exact_match"
            entry["matched_project_id"] = legacy_hit["canonical_project_id"]
            entry["match_basis"] = "legacy_id"
            report.append(entry)
            continue

        if len(candidates) == 1:
            reg = candidates[0]
            addr_match = c_norm_addr and reg["_norm_addr"] and c_norm_addr == reg["_norm_addr"]
            corpus_match = (c_corpus is None and reg["_corpus"] is None) or (c_corpus == reg["_corpus"])
            if addr_match and corpus_match:
                entry["status"] = "exact_match"
                entry["matched_project_id"] = reg["canonical_project_id"]
                entry["match_basis"] = "name+address" + ("+corpus" if c_corpus else "")
                entry["coord_corroborated"] = coord_close(c, reg)
            else:
                entry["status"] = "probable_match"
                entry["candidate_project_id"] = reg["canonical_project_id"]
                entry["mismatch"] = ([] if addr_match else ["address"]) + ([] if corpus_match else ["corpus"])
                entry["coord_corroborated"] = coord_close(c, reg)
            report.append(entry)
            continue

        if len(candidates) > 1:
            # same normalized name, multiple registry rows - disambiguate by
            # corpus token only; coordinates are corroboration, not a
            # tie-breaker (per the sync request).
            corpus_hits = [r for r in candidates if c_corpus is not None and r["_corpus"] == c_corpus]
            if len(corpus_hits) == 1:
                reg = corpus_hits[0]
                addr_match = c_norm_addr and reg["_norm_addr"] and c_norm_addr == reg["_norm_addr"]
                entry["status"] = "exact_match" if addr_match else "probable_match"
                entry["matched_project_id" if addr_match else "candidate_project_id"] = reg["canonical_project_id"]
                entry["match_basis"] = "name+corpus+address" if addr_match else "name+corpus (address differs)"
                report.append(entry)
                continue
            entry["status"] = "conflict"
            entry["candidate_project_ids"] = [r["canonical_project_id"] for r in candidates]
            entry["reason"] = "multiple registry rows share this normalized name; corpus token did not disambiguate"
            report.append(entry)
            continue

        # 0 name candidates - check coordinate corroboration only to flag a
        # possible conflict for human review, never to auto-match.
        near = [r for r in registry if coord_close(c, r)]
        if near:
            entry["status"] = "conflict"
            entry["candidate_project_ids"] = [r["canonical_project_id"] for r in near]
            entry["reason"] = "no name match, but coordinates are within ~110m of registry row(s) - needs human review"
        else:
            entry["status"] = "new_record"
            entry["reason"] = "no registry row with matching name or nearby coordinates"
        report.append(entry)

    counts = defaultdict(int)
    for e in report:
        counts[e["status"]] += 1

    OUT_JSON.parent.mkdir(exist_ok=True)
    OUT_JSON.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    lines = [
        "# Classifier <-> registry mapping report (2026-08-30)",
        "",
        f"- classifier rows (source): {len(classifier)}",
        f"- registry rows (target): {len(registry)}",
        "",
        "| status | count |",
        "|---|---|",
    ]
    for status in ("exact_match", "probable_match", "conflict", "new_record", "excluded_from_quarterly_layer"):
        lines.append(f"| {status} | {counts.get(status, 0)} |")
    lines.append(f"| **total** | **{len(report)}** |")
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print("\n".join(lines))
    print(f"\nfull report: {OUT_JSON}")


if __name__ == "__main__":
    main()
