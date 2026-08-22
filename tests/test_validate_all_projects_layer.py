import copy
import json
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))
from validate_all_projects_layer import role_completeness_issues, validate

SAMPLE = json.loads(
    (REPO_ROOT / "data" / "test_fixtures" / "all_projects_layer.sample.json").read_text(encoding="utf-8")
)


def find(records, canonical_building_id):
    for r in records:
        if r.get("canonical_building_id") == canonical_building_id:
            return r
    raise KeyError(canonical_building_id)


class AllProjectsLayerValidationTests(unittest.TestCase):
    def test_sample_is_valid(self):
        self.assertEqual(validate(SAMPLE), [])

    def test_badaevsky_shared_project_id_is_not_a_duplicate(self):
        # Два корпуса Бадаевского с одним canonical_project_id — это правило,
        # не баг. Сам факт, что sample проходит валидацию (см. выше), уже
        # это подтверждает; здесь дополнительно проверяем сами записи.
        west = find(SAMPLE, "badaevsky-west")
        east = find(SAMPLE, "badaevsky-east")
        self.assertEqual(west["canonical_project_id"], east["canonical_project_id"])
        self.assertNotEqual(west["canonical_building_id"], east["canonical_building_id"])
        self.assertEqual(validate([west, east]), [])

    def test_duplicate_canonical_building_id_is_rejected(self):
        payload = copy.deepcopy(SAMPLE)
        dup = copy.deepcopy(find(payload, "badaevsky-west"))
        payload.append(dup)
        errors = validate(payload)
        self.assertTrue(any("duplicate canonical_building_id" in e for e in errors))

    def test_offer_not_started_requires_reason(self):
        payload = copy.deepcopy(SAMPLE)
        rec = next(r for r in payload if r["canonical_project_id"] == "chalet-pyatnitskaya-40")
        rec["offer_status"] = "Ещё не вышел в продажу"
        rec["offer_not_started_reason"] = None
        errors = validate(payload)
        self.assertTrue(any("offer_not_started_reason" in e for e in errors))

    def test_coordinate_outside_moscow_is_rejected(self):
        payload = copy.deepcopy(SAMPLE)
        payload[0]["latitude"] = 60.0
        errors = validate(payload)
        self.assertTrue(any("latitude" in e and "outside" in e for e in errors))

    def test_embedded_lots_are_forbidden(self):
        payload = copy.deepcopy(SAMPLE)
        payload[0]["lots"] = []
        errors = validate(payload)
        self.assertTrue(any("embedded lot payload forbidden" in e for e in errors))

    def test_unverified_public_record_is_rejected(self):
        payload = copy.deepcopy(SAMPLE)
        payload[0]["public_visibility"] = "public"
        payload[0]["verification_status"] = "unverified"
        errors = validate(payload)
        self.assertTrue(any("should be internal_only" in e for e in errors))

    def test_unknown_project_status_is_rejected(self):
        payload = copy.deepcopy(SAMPLE)
        payload[0]["project_status"] = "На паузе"
        errors = validate(payload)
        self.assertTrue(any("invalid project_status" in e for e in errors))

    def test_unknown_offer_status_is_rejected(self):
        payload = copy.deepcopy(SAMPLE)
        payload[0]["offer_status"] = "На паузе"
        errors = validate(payload)
        self.assertTrue(any("invalid offer_status" in e for e in errors))

    def test_unknown_entity_role_is_rejected(self):
        payload = copy.deepcopy(SAMPLE)
        payload[0]["entity_role"] = "workspace"
        errors = validate(payload)
        self.assertTrue(any("invalid entity_role" in e for e in errors))

    def test_coworking_site_does_not_require_host_building_area_or_dates(self):
        record = copy.deepcopy(SAMPLE[0])
        record["entity_role"] = "coworking_site"
        record["market_channel"] = ["coworking"]
        record["canonical_building_id"] = "test-host-building"
        record["gba"] = None
        record["gla"] = None
        record["input_year"] = None
        self.assertEqual(role_completeness_issues(record), [])

    def test_office_project_area_and_dates_remain_required_for_completeness(self):
        record = copy.deepcopy(SAMPLE[0])
        record["entity_role"] = "office_project"
        record["gba"] = None
        record["gla"] = None
        record["input_year"] = None
        issues = role_completeness_issues(record)
        self.assertTrue(any("gba" in issue for issue in issues))
        self.assertTrue(any("gla" in issue for issue in issues))
        self.assertTrue(any("input_year" in issue for issue in issues))

    def test_project_status_is_lifecycle_not_offer(self):
        # Регресс на переименование 2026-07-31: project_status обязан быть
        # жизненным циклом (Проектируется/.../Не установлен), а не статусом
        # предложения — раньше в этом проекте было названо наоборот.
        lifecycle_values = {"Проектируется", "Строится", "Введён", "Заморожен", "Отменён", "Не установлен"}
        offer_values = {"В продаже", "Продано / снято", "Ещё не вышел в продажу", "Не применяется"}
        for r in SAMPLE:
            self.assertIn(r["project_status"], lifecycle_values)
            self.assertIn(r["offer_status"], offer_values)


if __name__ == "__main__":
    unittest.main()
