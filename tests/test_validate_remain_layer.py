import copy
import json
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))
from validate_remain_layer import validate

SAMPLE = json.loads(
    (REPO_ROOT / "data" / "test_fixtures" / "remain_observations.sample.json").read_text(encoding="utf-8")
)


class RemainLayerValidationTests(unittest.TestCase):
    def test_sample_is_valid(self):
        self.assertEqual(validate(SAMPLE), [])

    def test_duplicate_observation_id_is_rejected(self):
        payload = SAMPLE + [copy.deepcopy(SAMPLE[0])]
        errors = validate(payload)
        self.assertTrue(any("duplicate observation_id" in error for error in errors))

    def test_synthetic_lot_payload_is_rejected(self):
        payload = copy.deepcopy(SAMPLE)
        payload[0]["lots"] = []
        errors = validate(payload)
        self.assertTrue(any("synthetic/detail payload forbidden" in error for error in errors))

    def test_coordinate_outside_moscow_sanity_range_is_rejected(self):
        payload = copy.deepcopy(SAMPLE)
        # первый образец без latitude в fields — используем запись a101, где есть числовое поле
        payload[0]["fields"]["developer"] = {
            "raw_value": "x", "confidence": "low", "verification_status": "unverified"
        }
        payload[0]["fields"]["latitude"] = {
            "raw_value": 60.0, "normalized_value": 60.0,
            "confidence": "low", "verification_status": "unverified"
        }
        errors = validate(payload)
        self.assertTrue(any("latitude" in error and "outside" in error for error in errors))

    def test_unknown_status_is_rejected(self):
        payload = copy.deepcopy(SAMPLE)
        payload[0]["verification_status"] = "trusted"
        errors = validate(payload)
        self.assertTrue(any("invalid verification_status" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
