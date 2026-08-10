"""Регрессия на join-баг гибких офисов в codifier.html.

joinFlexRegistryFields() раньше строил ключ сопоставления как
`${row.network} (${row.bc})`, а data/all_projects_layer.json называет
записи по ПОЛНОМУ raw_name площадки ("WeWork Роза (Красная Роза)"), не по
бренду оператора ("WeWork (Красная Роза)"). Из-за этого 429 из 739 (58%)
квартальных coworking-строк во всех кварталах не находили пару — молча,
без ошибки, просто canonical_project_id оставался null. Обнаружено при
разборе подтверждённого пропуска СODE Novo (2026-08-12).

Исправление — новое поле flex_site_label (см.
scripts/build_all_projects_layer.py:derive_flex_site_label) и сопоставление
по row.bc напрямую (codifier.html:registryByFlexSiteLabelMap/
joinFlexRegistryFields), а не по network+bc.
"""
import json
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
REGISTRY_PATH = REPO_ROOT / "data" / "all_projects_layer.json"
COWORKING_PATH = REPO_ROOT / "data" / "coworking_202606.json"
CODIFIER_HTML = REPO_ROOT / "codifier.html"


def norm(s):
    if not s:
        return ""
    return " ".join(str(s).lower().replace("ё", "е").split())


@unittest.skipUnless(
    REGISTRY_PATH.exists() and COWORKING_PATH.exists(),
    "реестр или coworking_202606.json отсутствуют",
)
class FlexSiteLabelJoinRegressionTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry = json.loads(REGISTRY_PATH.read_text(encoding="utf-8-sig"))
        cls.coworking = json.loads(COWORKING_PATH.read_text(encoding="utf-8-sig"))
        cls.by_label = {}
        for r in cls.registry:
            label = r.get("flex_site_label")
            if label:
                cls.by_label[norm(label)] = r

    def test_flex_site_label_field_is_present_and_derived_correctly(self):
        """flex_site_label = canonical_name минус raw_name-префикс — не
        регэксп от конца строки (тот ломается на вложенных скобках вида
        "SOK (SOK Сити (3 и 4 этаж))")."""
        checked = 0
        for r in self.registry:
            label = r.get("flex_site_label")
            if label is None:
                continue
            raw_name = r["raw_name"]
            canonical_name = r["canonical_name"]
            self.assertEqual(canonical_name, f"{raw_name} ({label})", r["canonical_project_id"])
            checked += 1
        self.assertGreater(checked, 100, "ожидалось значительное число coworking-подобных записей с flex_site_label")

    def test_at_least_95_percent_of_q2_2026_coworking_rows_join_by_bc(self):
        """До фикса совпадало 42% (network+bc), после — ожидаем практически
        полное покрытие (допуск на единичные строки с пустым bc в исходных
        данных, это не баг джойна, а дырка в самих данных)."""
        total = 0
        matched = 0
        unmatched = []
        for row in self.coworking:
            bc = row.get("bc")
            if not bc:
                continue
            total += 1
            if norm(bc) in self.by_label:
                matched += 1
            else:
                unmatched.append((row.get("name"), bc))
        self.assertGreater(total, 0)
        ratio = matched / total
        self.assertGreaterEqual(
            ratio, 0.95,
            f"только {matched}/{total} ({ratio:.0%}) coworking-строк Q2 2026 сопоставились "
            f"по bc с реестром — джойн снова сломан. Несопоставленные: {unmatched[:15]}",
        )

    def test_code_novo_joins_by_bc_not_by_network_brand(self):
        """Ключевой пример регрессии: сеть 'СODE' используется 4 разными
        площадками — сопоставление обязано идти по конкретному bc, а не по
        общему бренду, иначе все 4 схлопнутся в одну запись реестра."""
        code_rows = [r for r in self.coworking if r.get("network") == "СODE"]
        self.assertGreaterEqual(len(code_rows), 2, "ожидалось несколько площадок сети СODE")
        resolved_ids = set()
        for row in code_rows:
            label = self.by_label.get(norm(row.get("bc")))
            self.assertIsNotNone(label, f"площадка СODE не сопоставлена: {row.get('name')} / {row.get('bc')}")
            resolved_ids.add(label["canonical_project_id"])
        self.assertEqual(
            len(resolved_ids), len(code_rows),
            f"площадки сети СODE схлопнулись в общий набор ID {resolved_ids} — "
            f"должны резолвиться в РАЗНЫЕ canonical_project_id, это разные здания",
        )
        novo_row = next(r for r in code_rows if r["name"] == "СODE Novo")
        novo_match = self.by_label[norm(novo_row["bc"])]
        self.assertEqual(novo_match["canonical_project_id"], "proj-149")

    def test_codifier_html_joins_by_bc_not_by_network_plus_bc(self):
        """Source-level защита: сама формула ключа в codifier.html не должна
        откатиться на `${row.network} (${row.bc})`."""
        html = CODIFIER_HTML.read_text(encoding="utf-8")
        self.assertNotIn("row.network && row.bc", html)
        idx = html.index("function joinFlexRegistryFields")
        body = html[idx: idx + 400]
        self.assertIn("row.bc", body)
        self.assertNotIn("row.network", body)


if __name__ == "__main__":
    unittest.main()
