import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class LocalVendorAssetsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pages = {
            name: (ROOT / name).read_text(encoding="utf-8")
            for name in ("index.html", "analytics.html", "codifier.html", "classifier.html")
        }

    def test_critical_runtime_dependencies_do_not_use_cdns(self):
        forbidden = (
            "https://unpkg.com",
            "https://cdn.jsdelivr.net",
            "https://fonts.googleapis.com",
            "https://fonts.gstatic.com",
        )
        for name, source in self.pages.items():
            for host in forbidden:
                self.assertNotIn(host, source, f"{name} still depends on {host}")

    def test_required_local_assets_exist_and_are_not_empty(self):
        required = (
            "vendor/leaflet/leaflet.js",
            "vendor/leaflet/leaflet.css",
            "vendor/leaflet/images/layers.png",
            "vendor/leaflet/images/layers-2x.png",
            "vendor/leaflet/images/marker-icon.png",
            "vendor/leaflet.markercluster/leaflet.markercluster.js",
            "vendor/leaflet.markercluster/MarkerCluster.css",
            "vendor/leaflet.markercluster/MarkerCluster.Default.css",
            "vendor/leaflet-draw/leaflet.draw.js",
            "vendor/leaflet-draw/leaflet.draw.css",
            "vendor/leaflet-draw/images/spritesheet.svg",
            "vendor/chartjs/chart.umd.min.js",
            "vendor/chartjs/chartjs-plugin-datalabels.min.js",
            "vendor/xlsx/xlsx.full.min.js",
            "vendor/fonts/montserrat.css",
        )
        for relative in required:
            path = ROOT / relative
            self.assertTrue(path.is_file(), f"missing {relative}")
            self.assertGreater(path.stat().st_size, 100, f"empty or truncated {relative}")

    def test_css_relative_urls_resolve_to_local_files(self):
        stylesheets = (
            ROOT / "vendor/leaflet/leaflet.css",
            ROOT / "vendor/leaflet-draw/leaflet.draw.css",
            ROOT / "vendor/fonts/montserrat.css",
        )
        for stylesheet in stylesheets:
            source = stylesheet.read_text(encoding="utf-8")
            for raw_url in re.findall(r"url\(['\"]?([^)'\"]+)", source):
                if raw_url.startswith(("data:", "#")):
                    continue
                asset = (stylesheet.parent / raw_url).resolve()
                self.assertTrue(asset.is_file(), f"{stylesheet.name} references missing {raw_url}")

    def test_pages_reference_local_versioned_assets(self):
        index = self.pages["index.html"]
        analytics = self.pages["analytics.html"]
        codifier = self.pages["codifier.html"]
        self.assertIn('src="vendor/leaflet/leaflet.js"', index)
        self.assertIn("loadScript('vendor/chartjs/chart.umd.min.js')", index)
        self.assertIn("loadScript('vendor/chartjs/chart.umd.min.js')", analytics)
        self.assertIn("loadScript('vendor/xlsx/xlsx.full.min.js')", analytics)
        self.assertIn('src="vendor/xlsx/xlsx.full.min.js"', codifier)

    def test_vendored_packages_keep_license_metadata(self):
        licenses = (
            "vendor/leaflet/LICENSE",
            "vendor/leaflet-draw/package.json",
            "vendor/chartjs/LICENSE-chartjs.md",
            "vendor/chartjs/LICENSE-datalabels.md",
            "vendor/xlsx/LICENSE",
            "vendor/fonts/LICENSE",
        )
        for relative in licenses:
            self.assertTrue((ROOT / relative).is_file(), f"missing license metadata: {relative}")


if __name__ == "__main__":
    unittest.main()
