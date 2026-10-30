"""Каталог выгрузки лотов: ключи корпусов уникальны, у каждого парсера есть модуль, реестр и targets согласованы."""
import importlib.util
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRAPER = os.path.join(ROOT, "lot_scraper")


class LotScraperCatalogTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not os.path.exists(os.path.join(SCRAPER, "registry_q3.csv")):
            raise unittest.SkipTest("registry_q3.csv не создан (нет свода Q3 на этой машине)")
        sys.path.insert(0, SCRAPER)
        sys.path.insert(0, os.path.join(SCRAPER, "sites"))
        import engine
        cls.engine = engine

    def test_keys_unique(self):
        keys = [self.engine.key_of(t["project_id"], t["sub_id"]) for t in self.engine.T]
        self.assertEqual(len(keys), len(set(keys)))

    def test_every_target_has_parser_module(self):
        for t in self.engine.T:
            path = os.path.join(SCRAPER, "sites", t["site"] + ".py")
            self.assertTrue(os.path.exists(path), t["site"])

    def test_targets_are_in_registry(self):
        reg = {c["key"] for c in self.engine.catalog()}
        for t in self.engine.T:
            self.assertIn(self.engine.key_of(t["project_id"], t["sub_id"]), reg)

    def test_catalog_flags(self):
        cat = self.engine.catalog()
        self.assertEqual(sum(c["has_parser"] for c in cat), len(self.engine.T))


if __name__ == "__main__":
    unittest.main()
