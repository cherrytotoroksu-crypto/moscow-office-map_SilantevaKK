"""Regression for merging the legacy data/future_projects.json (705 records)
into the «Все проекты» map alongside data/all_projects_layer.json (2026-09-08,
explicit user decision to maximize map coverage rather than only the strict
374-record registry).

index.html's loadFutureProjects() does the actual merge client-side (JS) —
never writing back into either JSON file — using normalizeNameKey() +
metersBetween() (<80m) to skip any future_projects.json entry that already
matches a live (non-duplicate_of) all_projects_layer.json record by name or
coordinate. These tests re-run the same matching rule in Python against the
committed data to lock in: the threshold constant matches the JS, known
overlapping projects are actually skipped, and a spot-checked genuinely-new
project is not accidentally filtered out.
"""
import json
import math
import os
import re
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INDEX_HTML = os.path.join(ROOT, "index.html")
REGISTRY = os.path.join(ROOT, "data", "all_projects_layer.json")
LEGACY = os.path.join(ROOT, "data", "future_projects.json")


def load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def normalize_name_key(s):
    if not s:
        return ""
    return re.sub(r"[^a-zа-я0-9]+", "", s.lower())


def meters_between(lat1, lng1, lat2, lng2):
    d_lat = (lat1 - lat2) * 111000
    d_lng = (lng1 - lng2) * 111000 * math.cos(math.radians(lat1))
    return math.hypot(d_lat, d_lng)


@unittest.skipUnless(os.path.isfile(REGISTRY) and os.path.isfile(LEGACY),
                      "data/all_projects_layer.json or data/future_projects.json not generated yet")
class ProjectsModeLegacyMergeTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry = load_json(REGISTRY)
        cls.legacy = load_json(LEGACY)
        with open(INDEX_HTML, encoding="utf-8") as f:
            cls.html = f.read()
        cls.live = [r for r in cls.registry if not r.get("duplicate_of")]
        cls.name_keys = set()
        cls.coords = []
        for r in cls.live:
            cls.name_keys.add(normalize_name_key(r.get("canonical_name")))
            cls.name_keys.add(normalize_name_key(r.get("raw_name")))
            for alias in r.get("aliases") or []:
                cls.name_keys.add(normalize_name_key(alias))
            if r.get("latitude") is not None and r.get("longitude") is not None:
                cls.coords.append((r["latitude"], r["longitude"]))

    def _is_near_registry(self, lat, lng, threshold_m=80):
        if lat is None or lng is None:
            return False
        return any(meters_between(lat, lng, rlat, rlng) < threshold_m for rlat, rlng in self.coords)

    def _unmatched_legacy(self):
        candidates = self.legacy["projects"] + self.legacy["no_coords"]
        unmatched = []
        for p in candidates:
            if normalize_name_key(p.get("name")) in self.name_keys:
                continue
            if self._is_near_registry(p.get("lat"), p.get("lng")):
                continue
            unmatched.append(p)
        return unmatched

    def test_js_threshold_constant_matches_python_reimplementation(self):
        self.assertIn("COORD_MATCH_THRESHOLD_M = 80", self.html)

    def test_capital_towers_legacy_row_is_not_duplicated(self):
        """Capital Towers is a deliberate exclusion from the registry (mixed-use,
        see Codex web audit 2026-09-05) — its future_projects.json row must
        still surface as a legacy addition, not silently vanish, since it is
        genuinely absent from the live registry."""
        by_name = {p.get("name"): p for p in self.legacy["projects"] + self.legacy["no_coords"]}
        self.assertIn("Capital Towers", by_name)
        unmatched_names = {p.get("name") for p in self._unmatched_legacy()}
        self.assertIn("Capital Towers", unmatched_names)

    def test_known_registry_projects_are_excluded_from_legacy_additions(self):
        """A101 Prokshino appears in the live registry (proj-216, generic point) —
        legacy rows sharing that coordinate must not double up as new pins."""
        registry_a101 = next(
            (r for r in self.live if r.get("canonical_name") == "А101 Прокшино"), None
        )
        self.assertIsNotNone(registry_a101, "expected proj-216 'А101 Прокшино' in the live registry")
        unmatched = self._unmatched_legacy()
        for p in unmatched:
            if p.get("lat") is None or p.get("lng") is None:
                continue
            dist = meters_between(p["lat"], p["lng"], registry_a101["latitude"], registry_a101["longitude"])
            self.assertGreaterEqual(
                dist, 80,
                f"legacy row {p.get('id')} ({p.get('name')!r}) at {dist:.0f}m from proj-216 should have been matched",
            )

    def test_legacy_additions_are_a_substantial_but_bounded_share(self):
        """Sanity bound so a future data refresh that silently duplicates most
        of the registry (near-0 new) or floods the map (near-705 new) fails
        loudly instead of quietly shipping bad data."""
        total_candidates = len(self.legacy["projects"]) + len(self.legacy["no_coords"])
        unmatched = self._unmatched_legacy()
        self.assertGreater(len(unmatched), total_candidates * 0.3)
        self.assertLess(len(unmatched), total_candidates * 0.95)

    def test_verified_not_office_legacy_rows_are_excluded_from_the_map(self):
        """2026-09-08, revised: three waves of web verification originally
        excluded ~44 legacy candidates, but most were excluded on "found a
        residential complex" alone — without checking whether that project
        also has a separate office building/podium (mixed-use is common;
        see Capital Towers in Codex web audit 2026-09-05, kept precisely
        because it has an 8808 sqm office component despite being mostly
        residential). Those "residential, office not specifically ruled
        out" rows were reinstated onto the map. Only rows where sources
        confirmed the site is something else entirely (mall/metro/data
        center/warehouse/media studio/sports facility) or the named project
        does not exist at all remain excluded."""
        excluded_ids = [
            "OBJ-0146", "OBJ-0645", "OBJ-0367", "OBJ-0141", "OBJ-0307",
            "OBJ-0352", "OBJ-0431", "OBJ-0491", "OBJ-0495", "OBJ-0552",
            "OBJ-0185", "OBJ-0191", "OBJ-0404", "OBJ-0461", "OBJ-0463",
            "OBJ-0464", "OBJ-0471", "OBJ-0241", "OBJ-0242",
        ]
        match = re.search(r"LEGACY_VERIFIED_NOT_OFFICE\s*=\s*new Set\(\[(.*?)\]\);", self.html, re.S)
        self.assertIsNotNone(match, "LEGACY_VERIFIED_NOT_OFFICE not found in index.html")
        block = match.group(1)
        for oid in excluded_ids:
            self.assertIn(f"'{oid}'", block, f"{oid} missing from LEGACY_VERIFIED_NOT_OFFICE")
        all_ids = re.findall(r"'(OBJ-\d{4})'", block)
        self.assertEqual(len(all_ids), len(set(all_ids)), "duplicate id in LEGACY_VERIFIED_NOT_OFFICE")
        self.assertEqual(len(all_ids), len(excluded_ids), "unexpected extra id in LEGACY_VERIFIED_NOT_OFFICE")
        # and confirm the exclusion check actually runs before the dedup logic
        loop_match = re.search(r"for \(const p of legacyCandidates\)\s*\{(.*?)\n\s*\}", self.html, re.S)
        self.assertIsNotNone(loop_match)
        self.assertIn("LEGACY_VERIFIED_NOT_OFFICE.has(p.id)", loop_match.group(1))

    def test_reinstated_mixed_use_candidates_are_not_excluded(self):
        """The "residential complex found, office not checked" rows must be
        back on the map (default legacy_supplement/needs_review), not
        silently dropped — reinstating them is the whole point of the fix."""
        reinstated_ids = [
            "OBJ-0212", "OBJ-0258", "OBJ-0534", "OBJ-0162", "OBJ-0225",
            "OBJ-0234", "OBJ-0247", "OBJ-0289", "OBJ-0300", "OBJ-0386",
            "OBJ-0454", "OBJ-0483", "OBJ-0551", "OBJ-0555", "OBJ-0558",
            "OBJ-0240", "OBJ-0244", "OBJ-0186", "OBJ-0344", "OBJ-0509",
            "OBJ-0518", "OBJ-0723", "OBJ-0724", "OBJ-0726", "OBJ-0631",
        ]
        match = re.search(r"LEGACY_VERIFIED_NOT_OFFICE\s*=\s*new Set\(\[(.*?)\]\);", self.html, re.S)
        self.assertIsNotNone(match)
        block = match.group(1)
        for oid in reinstated_ids:
            self.assertNotIn(f"'{oid}'", block, f"{oid} should have been reinstated, not left excluded")

    def test_legacy_merge_reads_both_files_without_writing_to_either(self):
        # loadFutureProjects() must GET both JSON files and never issue a
        # write-shaped call (fetch with method PUT/POST, or any localStorage
        # persistence) — the merge is display-only, recomputed on every load.
        match = re.search(r"async function loadFutureProjects\s*\([^)]*\)\s*\{", self.html)
        self.assertIsNotNone(match)
        depth = 0
        start = match.end() - 1
        end = start
        for i in range(start, len(self.html)):
            if self.html[i] == "{":
                depth += 1
            elif self.html[i] == "}":
                depth -= 1
                if depth == 0:
                    end = i + 1
                    break
        body = self.html[start:end]
        self.assertIn("all_projects_layer.json", body)
        self.assertIn("future_projects.json", body)
        self.assertNotIn("method:", body)
        self.assertNotIn("localStorage", body)


if __name__ == "__main__":
    unittest.main()
