import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class OfficialProjectsGapFillWave8Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        rows = json.loads((ROOT / "data/all_projects_layer.json").read_text(encoding="utf-8"))
        cls.rows = {row.get("canonical_project_id"): row for row in rows}
        cls.dates = json.loads((ROOT / "data/building_dates.json").read_text(encoding="utf-8"))
        classifier = json.loads(
            (ROOT / "data/unified_classifier_audited_2026-08-27.json").read_text(encoding="utf-8")
        )
        cls.classifier = {row.get("unified_id"): row for row in classifier.get("records", [])}

    def test_mount_current_official_identity_and_date_are_applied(self):
        row = self.rows["proj-73"]
        self.assertEqual(row["canonical_name"], "MOUNT (Маунт)")
        self.assertEqual(row["developer"], "FORMA")
        self.assertEqual(row["address"], "Боровское шоссе, 2а")
        self.assertEqual((row["gba"], row["gla"]), (39161, 26050))
        self.assertEqual((row["input_year"], row["input_quarter"], row["input_date_kind"]), (2028, 1, "planned"))
        self.assertIn("БЦ Мещерский", row["aliases"])

    def test_afi_office_date_does_not_reuse_residential_2024_date(self):
        row = self.rows["proj-106"]
        self.assertEqual(row["project_status"], "Введён")
        self.assertEqual((row["input_year"], row["input_quarter"], row["input_date_kind"]), (2026, 1, "confirmed"))
        self.assertNotEqual(row["input_year"], 2024)

    def test_building_dates_are_synchronized(self):
        self.assertEqual((self.dates["mount (маунт)"]["commission_year"], self.dates["mount (маунт)"]["commission_q"]), (2028, "202803"))
        self.assertEqual((self.dates["afi парк воронцовский"]["commission_year"], self.dates["afi парк воронцовский"]["commission_q"]), (2026, "202603"))

    def test_classifier_matches_reviewed_identity_status_and_precision(self):
        mount = self.classifier["UC-OBJ-0124"]
        self.assertEqual((mount["name"], mount["developer"]), ("MOUNT (Маунт)", "FORMA"))
        self.assertEqual((mount["gba"], mount["gla"]), (39161, 26050))
        self.assertEqual((mount["commission_year"], mount["commission_quarter"]), (2028, 1))
        afi = self.classifier["UC-OBJ-0185"]
        self.assertEqual((afi["status"], afi["commission_year"], afi["commission_quarter"]), ("Сданный", 2026, 1))

    def test_ryabov_duplicate_is_not_silently_filled(self):
        unresolved = self.rows["proj-96"]
        confirmed = self.rows["proj-220"]
        self.assertIsNone(unresolved["input_year"])
        self.assertEqual((confirmed["input_year"], confirmed["input_quarter"]), (2029, 1))


if __name__ == "__main__":
    unittest.main()
