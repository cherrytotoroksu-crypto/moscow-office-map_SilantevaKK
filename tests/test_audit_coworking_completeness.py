import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class AuditCoworkingCompletenessTest(unittest.TestCase):
    def test_auxiliary_cache_is_not_treated_as_quarter_snapshot(self):
        with tempfile.TemporaryDirectory() as tmp:
            data_dir = Path(tmp)
            (data_dir / "coworking_202606.json").write_text(
                json.dumps([{"id": 1, "network": "X"}]), encoding="utf-8"
            )
            (data_dir / "coworking_geocode_cache.json").write_text(
                json.dumps({"address": {"lat": 55.7, "lng": 37.6}}), encoding="utf-8"
            )
            result = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts" / "audit_coworking_completeness.py"),
                    "--data-dir",
                    str(data_dir),
                ],
                check=True,
                capture_output=True,
                text=True,
                encoding="utf-8",
            )
            report = json.loads(result.stdout)
            self.assertEqual(report["totals"]["rows"], 1)
            self.assertEqual(set(report["periods"]), {"202606"})

    def test_tariff_rows_are_not_reported_as_identity_conflicts(self):
        with tempfile.TemporaryDirectory() as tmp:
            data_dir = Path(tmp)
            common = {
                "id": 84,
                "name": "Manufaqtury Поклонка",
                "network": "Manufaqtury",
                "district": "ЗАО",
                "bc": "Poklonka Place",
                "address": "ул. Поклонная, 3",
                "seats": 843,
                "lat": 55.736,
                "lng": 37.533,
            }
            rows = [
                {**common, "vacancy": 200, "rate": 46000},
                {**common, "vacancy": 24, "rate": 71200},
            ]
            (data_dir / "coworking_202512.json").write_text(
                json.dumps(rows, ensure_ascii=False), encoding="utf-8"
            )
            result = subprocess.run(
                [sys.executable, str(ROOT / "scripts" / "audit_coworking_completeness.py"), "--data-dir", str(data_dir)],
                check=True,
                capture_output=True,
                text=True,
                encoding="utf-8",
            )
            report = json.loads(result.stdout)
            self.assertEqual(report["totals"]["tariff_variant_rows"], 1)
            self.assertEqual(report["totals"]["identity_conflict_groups"], 0)


if __name__ == "__main__":
    unittest.main()
