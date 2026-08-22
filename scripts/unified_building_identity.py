"""Conservative building-level identity helpers for the unified codifier.

Coordinates are corroboration only after an exact normalized building label
match. They are never used to select the nearest record.
"""
from __future__ import annotations

import re
import unicodedata
from collections import defaultdict


LINK_DECISION_DATE = "2026-08-22"


def normalize_label(value):
    text = unicodedata.normalize("NFKC", str(value or "")).lower().replace("ё", "е")
    text = re.sub(r"[^0-9a-zа-я]+", " ", text, flags=re.I)
    return re.sub(r"\s+", " ", text).strip()


def normalize_address(value):
    text = normalize_label(value)
    replacements = {
        "набережная": "наб",
        "проспект": "пр",
        "переулок": "пер",
        "улица": "ул",
        "строение": "с",
        "корпус": "к",
        "дом": "д",
    }
    tokens = [replacements.get(token, token) for token in text.split()]
    # Parenthetical district hints are not part of a postal address.
    return " ".join(token for token in tokens if token not in {"москва", "сити"})


def same_point(left, right, tolerance=1e-6):
    values = (
        left.get("latitude"), left.get("longitude"),
        right.get("lat"), right.get("lng"),
    )
    return None not in values and abs(values[0] - values[2]) <= tolerance and abs(values[1] - values[3]) <= tolerance


def link_coworking_sites(records, observations):
    """Return safe site->host links and rejected candidates.

    A link needs an exact normalized `flex_site_label == observation.bc ==
    host.canonical_name` chain plus address or coordinate corroboration. A
    non-unique host label is rejected. This is not nearest-point matching.
    """
    hosts = defaultdict(list)
    site_rows = []
    observations_by_bc = defaultdict(list)
    observations_by_name = defaultdict(list)
    for record in records:
        if record.get("entity_role") == "host_building":
            for value in [record.get("canonical_name"), *(record.get("aliases") or [])]:
                if normalize_label(value):
                    hosts[normalize_label(value)].append(record)
        elif record.get("entity_role") == "coworking_site":
            site_rows.append(record)
    for observation in observations:
        observations_by_bc[normalize_label(observation.get("bc"))].append(observation)
        observations_by_name[normalize_label(observation.get("name"))].append(observation)

    links = {}
    rejected = {}
    for site in site_rows:
        label = normalize_label(site.get("flex_site_label"))
        if label:
            obs_rows = observations_by_bc.get(label, [])
        else:
            name_keys = {
                normalize_label(value)
                for value in [site.get("raw_name"), site.get("canonical_name"), *(site.get("aliases") or [])]
                if normalize_label(value)
            }
            obs_rows = []
            for name_key in name_keys:
                obs_rows.extend(observations_by_name.get(name_key, []))
        candidate_hosts = []
        for obs in obs_rows:
            candidate_hosts.extend(hosts.get(normalize_label(obs.get("bc")), []))
        candidate_hosts = list({host["canonical_project_id"]: host for host in candidate_hosts}.values())
        if not candidate_hosts or not obs_rows:
            rejected[site["canonical_project_id"]] = "host label is absent/non-unique or has no observation"
            continue

        matches = []
        for host in candidate_hosts:
            host_address = normalize_address(host.get("address"))
            corroborating = []
            for obs in obs_rows:
                if host not in hosts.get(normalize_label(obs.get("bc")), []):
                    continue
                address_ok = bool(normalize_address(site.get("address"))) and (
                    normalize_address(site.get("address")) == normalize_address(obs.get("address"))
                    and (not host_address or host_address == normalize_address(obs.get("address")))
                )
                coordinate_ok = same_point(site, obs) and same_point(host, obs)
                if address_ok or coordinate_ok:
                    corroborating.append({"id": obs.get("id"), "address": address_ok, "coordinates": coordinate_ok})
            if corroborating:
                matches.append({
                    "canonical_building_id": host["canonical_building_id"],
                    "host_project_id": host["canonical_project_id"],
                    "evidence": corroborating,
                })
        unique_matches = {item["canonical_building_id"]: item for item in matches}
        if len(unique_matches) == 1:
            links[site["canonical_project_id"]] = next(iter(unique_matches.values()))
        elif len(unique_matches) > 1:
            rejected[site["canonical_project_id"]] = "multiple buildings corroborate; manual building split required"
        else:
            rejected[site["canonical_project_id"]] = "exact bc/name matched but address/coordinates did not corroborate"
    return links, rejected


def link_note(link):
    evidence_ids = ",".join(str(item.get("id")) for item in link["evidence"] if item.get("id") is not None)
    return (
        f"canonical_building_id linked {LINK_DECISION_DATE}: exact normalized bc/flex_site_label "
        f"plus address or coordinate corroboration in data/coworking_*.json id={evidence_ids}; "
        "no nearest-point matching; rule: scripts/unified_building_identity.py."
    )
