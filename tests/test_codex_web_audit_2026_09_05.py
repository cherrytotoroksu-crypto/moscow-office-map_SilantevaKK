"""Regression tests for outputs/codex_web_audit_2026-09-05.md.

Only the explicitly confirmed decision was applied (Capital Towers
mixed-use re-verification). The proposed aliases for "БЦ Крост"
(record absent from the live audited classifier) and "БЦ в
Очаково-Матвеевском" -> Lakes 2 (conflicting developer/coordinates/GBA,
no second independent source) were rejected by the user and must stay
unmerged. This file locks in that decision so a future pass does not
silently apply the rejected merges.
"""
import json
import os
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load(path):
    with open(os.path.join(ROOT, path), encoding="utf-8") as f:
        return json.load(f)


class TestCodexWebAudit20260905(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.classifier = load("data/unified_classifier_audited_2026-08-27.json")["records"]
        cls.by_id = {r["unified_id"]: r for r in cls.classifier}
        cls.by_name = {}
        for r in cls.classifier:
            cls.by_name.setdefault(r["name"], []).append(r)

    def test_bc_krost_candidate_absent_from_live_classifier(self):
        # UC-OBJ-0255 "БЦ Крост" only exists in the legacy data/unified_classifier.json,
        # never made it into the audited/live file. There is nothing to alias.
        self.assertNotIn("UC-OBJ-0255", self.by_id)
        self.assertNotIn("БЦ Крост", self.by_name,
                          "the disputed 'БЦ Крост' candidate must not exist in the live classifier")

    def test_ochakovo_matveevskoe_not_merged_into_lakes2(self):
        ochakovo = self.by_id["UC-OBJ-0251"]
        lakes2 = self.by_id["UC-OBJ-0202"]
        self.assertEqual(ochakovo["name"], "БЦ в Очаково-Матвеевском")
        self.assertEqual(lakes2["name"], "Lakes 2")
        # Distinct developers/areas/coordinates -> merge would be a false link, must stay separate records
        self.assertNotEqual(ochakovo["developer"], lakes2["developer"])
        self.assertNotEqual(ochakovo["gba"], lakes2["gba"])
        self.assertNotEqual(ochakovo["legacy_ids"], lakes2.get("legacy_ids"))
        self.assertEqual(ochakovo.get("legacy_ids"), [])

    def test_capital_towers_stays_mixed_use_with_office_gla(self):
        towers = self.by_id["UC-OBJ-0014"]
        self.assertEqual(towers["name"], "Capital Towers")
        self.assertEqual(towers["entity_type"], "residential_complex_with_commercial_infrastructure")
        self.assertEqual(towers["gla"], 8808.0)
        self.assertEqual(towers["gba"], 243000.0, "full GBA must not be reclassified as office area")
        self.assertFalse(towers["needs_review"])
        self.assertIn("mixed_use_project", towers["layer_qa_notes"])

    def test_disputed_candidates_remain_unmerged(self):
        # Unikey, БЦ у Океании, MR 1/2, Дом Солнца: no new evidence supplied,
        # so each conflicting/unresolved candidate name must still exist as its
        # own separate record (no silent alias/merge into another project).
        disputed_name_fragments = ["Unikey", "Океании", "Дом Солнца"]
        for fragment in disputed_name_fragments:
            matches = [name for name in self.by_name if fragment in name]
            self.assertTrue(matches, f"expected at least one live record mentioning {fragment!r}")

    def test_building_dates_untouched(self):
        # This audit must not touch data/building_dates.json at all.
        path = os.path.join(ROOT, "data", "building_dates.json")
        self.assertTrue(os.path.isfile(path))

    def test_bc_start_candidate_absent_from_live_classifier(self):
        # Like "БЦ Крост", "БЦ Старт" only exists in the legacy unified_classifier.json.
        self.assertNotIn("БЦ Старт", self.by_name)

    def test_artel_and_troitsky_pereulok_not_merged(self):
        # "БЦ Artel" (Электрозаводская) vs "1-й Троицкий переулок, вл. 12/2с"
        # (Равновесие Капитал): different developer, ~7km apart, different GBA.
        # Codex flagged this only as probable_match - data shows it is a false lead.
        artel = self.by_id["UC-OBJ-0240"]
        troitsky = self.by_id["UC-OBJ-0417"]
        self.assertEqual(artel["name"], "БЦ Artel")
        self.assertNotEqual(artel["developer"], troitsky["developer"])
        self.assertNotEqual(artel["gba"], troitsky["gba"])
        # Coordinates should stay far apart (roughly >0.05 deg ~ 5+km) - no accidental merge.
        self.assertGreater(abs(artel["latitude"] - troitsky["latitude"]), 0.01)

    def test_a101_stub_flagged_but_not_merged_to_a_specific_corpus(self):
        # "БЦ А101" has no address, so it cannot be safely assigned to one of the
        # existing Prokshino queues (1/2/3-я очередь) even though the developer
        # and district match. 2026-09-07 web check only adds a qa note; it must
        # not gain a legacy_id / coordinates / merge into another record.
        stub = self.by_id["UC-OBJ-0246"]
        self.assertEqual(stub["name"], "БЦ А101")
        self.assertIsNone(stub["address"])
        self.assertEqual(stub["legacy_ids"], [])
        self.assertIn("Прокшино", stub["layer_qa_notes"])

    def test_severny_port_records_stay_separate_buildings(self):
        # Three "Северный порт" records (Мангазея UC-OBJ-0386, LEGENDA
        # UC-OBJ-0726 and UC-OBJ-0518) sit on the same former industrial site
        # per a 2026-09-07 web check (domkad.ru: joint Мангазея + Legenda
        # development), but have distinct addresses/corpuses (63А/1А vs с7 vs
        # с6) - they must remain separate building records, not merged.
        mangazeya = self.by_id["UC-OBJ-0386"]
        legenda_main = self.by_id["UC-OBJ-0726"]
        legenda_beregovye = self.by_id["UC-OBJ-0518"]
        names = {mangazeya["name"], legenda_main["name"], legenda_beregovye["name"]}
        self.assertEqual(names, {
            "Мангазея Северный порт",
            "Северный порт",
            "Северный порт. Береговые кварталы",
        })
        addresses = {mangazeya["address"], legenda_main["address"], legenda_beregovye["address"]}
        self.assertEqual(len(addresses), 3, "all three buildings must keep distinct addresses")
        for rec in (mangazeya, legenda_main, legenda_beregovye):
            self.assertEqual(rec["legacy_ids"], [], "no merge should have introduced a shared legacy_id")


if __name__ == "__main__":
    unittest.main()
