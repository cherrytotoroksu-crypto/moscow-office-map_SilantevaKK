"""2026-08-19: building-level записи для зданий-хостов коворкингов.

Не Remain, не classifier — отдельный source="coworking_host_lookup" только
для заполнения cls (см. scripts/add_coworking_host_buildings.py и
outputs/coworking_missing_class_qa_2026-08-19.md). Регрессия на потерю
записей/утечку в квартальные объёмы + на то, что джойн коворкинг-карты
(index.html) НЕ читает эти записи — они не чинят цвет маркера на самой
карте, только доступны через общий слой/аналитику.
"""
import json
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))
from validate_all_projects_layer import validate as validate_layer

LAYER_PATH = REPO_ROOT / "data" / "all_projects_layer.json"
COWORKING_PATH = REPO_ROOT / "data" / "coworking_202606.json"
INDEX_HTML_PATH = REPO_ROOT / "index.html"


@unittest.skipUnless(LAYER_PATH.exists(), "all_projects_layer.json not present")
class CoworkingHostBuildingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.layer = json.loads(LAYER_PATH.read_text(encoding="utf-8-sig"))
        cls.hosts = [r for r in cls.layer if r.get("source") == "coworking_host_lookup"]

    def test_at_least_the_confirmed_hosts_are_present(self):
        self.assertGreaterEqual(len(self.hosts), 26)

    def test_host_records_have_confirmed_class_and_evidence(self):
        for r in self.hosts:
            self.assertIn(r["cls"], {"Prime", "A", "B+", "B"})
            self.assertIn("Источник:", r["qa_notes"])

    def test_host_records_never_enter_quarterly_volumes(self):
        for r in self.hosts:
            self.assertEqual(r["market_channel"], [])
            self.assertEqual(r["quarter_offer_refs"], [])
            self.assertFalse(r["quarter_offer_exists"])

    def test_host_records_are_not_classifier_derived(self):
        classifier_names = {r["canonical_name"] for r in self.layer if r["source"] == "classifier.html"}
        for r in self.hosts:
            self.assertNotIn(r["canonical_name"], classifier_names)

    def test_layer_still_passes_validator(self):
        self.assertEqual(validate_layer(self.layer), [])

    def test_coworking_map_join_still_does_not_read_the_general_layer(self):
        # Эти building-записи существуют ТОЛЬКО в общем слое — карта
        # коворкингов (loadCoworking) по-прежнему не должна их видеть,
        # иначе будет нарушен инвариант test_online_tables_invariants.py.
        html = INDEX_HTML_PATH.read_text(encoding="utf-8")
        # переиспользуем ту же проверку "тело функции не содержит all_projects_layer.json"
        import re
        match = re.search(r"async function loadCoworking\s*\([^)]*\)\s*\{", html)
        self.assertIsNotNone(match)
        depth = 0
        start = match.end() - 1
        end = None
        for i in range(start, len(html)):
            if html[i] == "{":
                depth += 1
            elif html[i] == "}":
                depth -= 1
                if depth == 0:
                    end = i
                    break
        body = html[start:end + 1]
        self.assertNotIn("all_projects_layer.json", body)


if __name__ == "__main__":
    unittest.main()
