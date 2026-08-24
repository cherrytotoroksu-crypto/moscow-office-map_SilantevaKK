import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class Audit004IdentityRecheckTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = (ROOT / "CODEX_AUDIT_REQUEST_2026-08-22.md").read_text(encoding="utf-8")

    def test_identity_fixed_but_date_conflict_remains_explicit(self):
        section = self.text.split("## AUDIT-004", 1)[1].split("## AUDIT-005", 1)[0]
        self.assertIn("Статус: `FIXED`", section)
        self.assertIn("commission_q=202703", section)
        self.assertIn("low-confidence/planned", section)
        self.assertIn("Aktsprilojeniyami_Hodinskaya-2.pdf", section)


if __name__ == "__main__":
    unittest.main()
