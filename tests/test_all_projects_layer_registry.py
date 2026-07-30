"""Regression test for the generated data/all_projects_layer.json registry.

Distinct from tests/test_validate_all_projects_layer.py, which only checks
the small hand-written sample fixture. This test checks the REAL registry
produced by scripts/build_all_projects_layer.py from classifier.html: right
record count, the Бадаевский shared-project-id rule, and that none of the
12 known display-name collisions got silently merged into one project.
"""
import json
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))
from validate_all_projects_layer import validate

REGISTRY_PATH = REPO_ROOT / "data" / "all_projects_layer.json"

# Same 12 names flagged by scripts/validate_classifier.py as sharing a
# display name across rows with different lat/lng/address (QUARANTINE_2026-07-29.md,
# "12 name-collision warnings"). Rule: not merged without an explicit ID scheme.
KNOWN_COLLISION_NAMES = [
    "Apollax Space (Новосущевский)",
    "Signature Столешников (Signature Столешников, 11)",
    "Smart Yard (на Волгоградском) (РТС Волгоградский)",
    "Регус (Пр. Мира, 40) (Проспект Мира, 40)",
    "Apollax Space (Технопарк)",
    "Apollax Space (Останкино)",
    "Apollax Space (Новослободская)",
    "Газетный (Газетный 17)",
    "Ходынка (Авиаконструктора Микояна)",
    "Apollax Space (Кузнецкий Мост)",
    "СODE Delegat (1-й Щемиловский 16с2)",
    "Manufaqtury Поклонка (Poklonka Place)",
]


@unittest.skipUnless(REGISTRY_PATH.exists(), "data/all_projects_layer.json not generated yet")
class AllProjectsLayerRegistryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.records = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))

    def test_registry_passes_validator(self):
        self.assertEqual(validate(self.records), [])

    def test_record_count_matches_active_raw_data(self):
        # 279 RAW_DATA rows - 2 out_of_scope (Новосибирск/Астана) = 277.
        self.assertEqual(len(self.records), 277)

    def test_badaevsky_shares_project_id_but_not_building_id(self):
        west = next(r for r in self.records if r["canonical_building_id"] == "badaevsky-west")
        east = next(r for r in self.records if r["canonical_building_id"] == "badaevsky-east")
        self.assertEqual(west["canonical_project_id"], "badaevsky")
        self.assertEqual(east["canonical_project_id"], "badaevsky")
        self.assertNotEqual(west["canonical_building_id"], east["canonical_building_id"])

    def test_known_name_collisions_are_not_silently_merged(self):
        for name in KNOWN_COLLISION_NAMES:
            matches = [r for r in self.records if r["canonical_name"] == name]
            self.assertGreaterEqual(
                len(matches), 2,
                f"expected >=2 rows for known collision {name!r}, found {len(matches)}"
            )
            ids = {r["canonical_project_id"] for r in matches}
            self.assertEqual(
                len(ids), len(matches),
                f"{name!r}: rows were merged into a shared canonical_project_id ({ids}) — not allowed without an explicit rule"
            )


if __name__ == "__main__":
    unittest.main()
