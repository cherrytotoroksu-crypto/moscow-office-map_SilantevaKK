"""Regression tests for AUDIT-011: full-map completeness and geography."""
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from audit_all_projects_completeness import REGION_BOUNDS, audit
from add_coworking_host_buildings import HOSTS, current_host_coordinates


class AllProjectsCompletenessAuditTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = audit()

    def test_every_historical_observation_has_identity_safe_registry_match(self):
        self.assertEqual(self.report["historical_sources"]["unmatched_unique"], [])

    def test_every_public_canonical_record_has_coordinates(self):
        self.assertEqual(self.report["missing_coordinates"], [])

    def test_no_public_coordinate_is_outside_moscow_region_guardrail(self):
        self.assertEqual(
            self.report["geography_outliers"], [],
            f"guardrail bounds={REGION_BOUNDS}",
        )

    def test_each_coworking_host_has_a_current_coordinate_source(self):
        coordinates = current_host_coordinates()
        missing = [bc for bc, *_ in HOSTS if bc not in coordinates]
        self.assertEqual(missing, [])

    def test_coworking_site_area_and_construction_date_are_not_applicable(self):
        coverage = self.report["field_coverage"]
        site_count = self.report["entity_roles"]["counts"]["coworking_site"]
        self.assertEqual(coverage["gba"]["not_applicable"], site_count)
        self.assertEqual(coverage["gla"]["not_applicable"], site_count)
        self.assertEqual(coverage["input_year"]["not_applicable"], site_count)
        site_issues = [
            issue
            for record in self.report["entity_roles"]["incomplete_records"]
            if record["entity_role"] == "coworking_site"
            for issue in record["issues"]
        ]
        self.assertFalse(any(field in issue for issue in site_issues for field in ("gba", "gla", "input_year")))

    def test_role_counts_cover_every_canonical_public_record(self):
        counts = self.report["entity_roles"]["counts"]
        self.assertEqual(sum(counts.values()), self.report["registry"]["canonical_public_rows"])
        self.assertGreaterEqual(counts["host_building"], 61)
        self.assertGreater(counts["coworking_site"], 0)
        self.assertGreater(counts["office_project"], 0)

    def test_date_model_gap_is_reported_without_touching_building_dates(self):
        model = self.report["date_model"]
        self.assertTrue(model["construction_start_and_sales_start_in_layer_schema"])
        self.assertGreater(model["building_dates_rows_read_only"], 0)


if __name__ == "__main__":
    unittest.main()
