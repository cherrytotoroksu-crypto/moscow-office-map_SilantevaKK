import unittest
from pathlib import Path


AUDIT = Path(__file__).resolve().parents[1] / "CODEX_AUDIT_REQUEST_2026-08-22.md"


class Audit007RecheckTest(unittest.TestCase):
    def test_stone_towers_remains_open_without_unsafe_merge(self):
        text = AUDIT.read_text(encoding="utf-8")
        section = text.split("## AUDIT-007", 1)[1].split("## AUDIT-008", 1)[0]
        self.assertIn("Статус: `OPEN`", section)
        self.assertIn("CIAN", section)
        self.assertIn("duplicate_of", section)
        self.assertIn("не назначен", section)


if __name__ == "__main__":
    unittest.main()
