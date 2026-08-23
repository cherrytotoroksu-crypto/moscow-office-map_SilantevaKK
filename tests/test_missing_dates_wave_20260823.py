import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class MissingDatesWave20260823Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        rows = json.loads((ROOT / "data" / "all_projects_layer.json").read_text(encoding="utf-8-sig"))
        cls.by_id = {row["canonical_project_id"]: row for row in rows}

    def test_confirmed_years_and_no_fabricated_quarters(self):
        expected = {"proj-20": 2025, "proj-112": 2028, "proj-115": 2028}
        for project_id, year in expected.items():
            row = self.by_id[project_id]
            self.assertEqual(row["input_year"], year)
            self.assertIsNone(row["input_quarter"])
            self.assertEqual(row["input_date_kind"], "confirmed")

    def test_each_fix_has_source_and_check_date_in_notes(self):
        for project_id in ("proj-20", "proj-112", "proj-115"):
            notes = self.by_id[project_id]["qa_notes"]
            self.assertIn("Input year rechecked 2026-08-23", notes)
            self.assertIn("http", notes)

    def test_k_city_date_conflict_is_visible_and_not_normalized(self):
        row = self.by_id["proj-136"]
        self.assertIsNone(row["input_year"])
        self.assertIsNone(row["input_quarter"])
        self.assertIn("Q2 2028", row["qa_notes"])
        self.assertIn("Q4 2028", row["qa_notes"])
        self.assertIn("https://kobzon.city/team", row["qa_notes"])
        self.assertIn("https://realty.rbc.ru/amp/news/68871e7b9a7947fdd81a8716", row["qa_notes"])

    def test_mind_date_conflict_is_visible_and_not_normalized(self):
        row = self.by_id["proj-152"]
        self.assertIsNone(row["input_year"])
        self.assertIn("2029", row["qa_notes"])
        self.assertIn("2030", row["qa_notes"])
        self.assertIn("https://fortexgroup.ru/sPDF/bc/16380/", row["qa_notes"])
        self.assertIn("https://seregina-5.ru/", row["qa_notes"])

    def test_qoob_phase_date_conflict_is_visible_and_not_normalized(self):
        row = self.by_id["proj-171"]
        self.assertIsNone(row["input_year"])
        self.assertIn("2026", row["qa_notes"])
        self.assertIn("2025", row["qa_notes"])
        self.assertIn("https://ibcrealestate.ru/catalog/T96_15935/", row["qa_notes"])
        self.assertIn("https://ipg-estate.ru/msk/ofisnaia-nedvizhimost/biznes-centr-qoob-korpus-b-9380", row["qa_notes"])

    def test_slava_office_date_uncertainty_is_visible(self):
        row = self.by_id["proj-87"]
        self.assertIsNone(row["input_year"])
        self.assertIn("2024", row["qa_notes"])
        self.assertIn("https://slava-office.ru/", row["qa_notes"])
        self.assertIn("https://slava-moscow.com/news/pervaya-ochered-premialnogo-kompleksa-slava-poluchila-razreshenie-na-vvod-v-ekspluatatsiyu", row["qa_notes"])

    def test_afi_residential_date_is_not_transferred_to_office(self):
        row = self.by_id["proj-106"]
        self.assertIsNone(row["input_year"])
        self.assertIn("residential buildings", row["qa_notes"])
        self.assertIn("https://afi-development.com/news/zhk-afi-park-vorontsovskiy-vveden-v-ekspluatatsiyu", row["qa_notes"])
        self.assertIn("https://afi-v-park.ru/news/zaversheny-krovelnye-raboty-biznes-tsentra-vorontsovskiy", row["qa_notes"])

    def test_lunar_missing_date_is_explicitly_documented(self):
        row = self.by_id["proj-14"]
        self.assertIsNone(row["input_year"])
        self.assertIn("https://hutton.ru/offices/lunar", row["qa_notes"])
        self.assertIn("no commissioning date", row["qa_notes"])

    def test_bernikov_date_conflict_is_visible_and_not_normalized(self):
        row = self.by_id["proj-19"]
        self.assertIsNone(row["input_year"])
        self.assertIn("2007", row["qa_notes"])
        self.assertIn("2021", row["qa_notes"])
        self.assertIn("Conflict retained", row["qa_notes"])

    def test_meshchersky_date_conflict_is_visible_and_not_normalized(self):
        row = self.by_id["proj-73"]
        self.assertIsNone(row["input_year"])
        self.assertIn("2027", row["qa_notes"])
        self.assertIn("2028", row["qa_notes"])
        self.assertIn("Conflict retained", row["qa_notes"])

    def test_link_completion_year_and_quarter_are_confirmed(self):
        row = self.by_id["proj-150"]
        self.assertEqual(row["input_year"], 2028)
        self.assertEqual(row["input_quarter"], 4)
        self.assertEqual(row["input_date_kind"], "confirmed")
        self.assertIn("https://mr-bc-link.ru/", row["qa_notes"])
        self.assertIn("https://fortexgroup.ru/bc/link/prodazha-ofisa/179-1320066/", row["qa_notes"])

    def test_euler_date_conflict_is_visible_and_not_normalized(self):
        row = self.by_id["proj-250"]
        self.assertIsNone(row["input_year"])
        self.assertIsNone(row["input_quarter"])
        notes = row["qa_notes"]
        for value in ("Q3 2026", "Q2 2026", "Q3 2025"):
            self.assertIn(value, notes)
        for url in (
            "https://ibcrealestate.ru/catalog/T96_15661/",
            "https://www.cian.ru/sale/commercial/328659891/",
            "https://www.cian.ru/rent/commercial/328190998/",
        ):
            self.assertIn(url, notes)

    def test_river_park_office_commissioning_is_confirmed(self):
        row = self.by_id["proj-279"]
        self.assertEqual(row["input_year"], 2026)
        self.assertEqual(row["input_quarter"], 2)
        self.assertEqual(row["input_date_kind"], "confirmed")
        self.assertIn("office-business center", row["qa_notes"])
        self.assertIn("https://m.river-park.ru/info/news/27693/", row["qa_notes"])
        self.assertIn("51930", row["qa_notes"])

    def test_varshavskaya_commissioning_is_confirmed(self):
        row = self.by_id["proj-224"]
        self.assertEqual(row["input_year"], 2029)
        self.assertEqual(row["input_quarter"], 2)
        self.assertEqual(row["input_date_kind"], "confirmed")
        self.assertIn("https://ibcrealestate.ru/upload/iblock/864/", row["qa_notes"])
        self.assertIn("https://t.me/s/trendagent_msk/21855", row["qa_notes"])


if __name__ == "__main__":
    unittest.main()
