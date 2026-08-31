import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class ResponsiveLayoutsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.index = (ROOT / "index.html").read_text(encoding="utf-8")
        cls.analytics = (ROOT / "analytics.html").read_text(encoding="utf-8")
        cls.codifier = (ROOT / "codifier.html").read_text(encoding="utf-8")
        cls.classifier = (ROOT / "classifier.html").read_text(encoding="utf-8")

    def test_all_primary_pages_declare_mobile_viewport(self):
        for source in (self.index, self.analytics, self.codifier, self.classifier):
            self.assertIn('name="viewport"', source)
            self.assertIn("width=device-width", source)

    def test_map_mobile_controls_have_touch_sized_targets(self):
        self.assertIn("#panelToggle { display: flex; top: 8px", self.index)
        self.assertIn("width:44px; height:44px", self.index)
        self.assertIn(".map-search input { min-height:44px; }", self.index)
        self.assertIn(".leaflet-bar a { width:36px; height:36px", self.index)

    def test_analytics_mobile_controls_and_spacing_are_compact(self):
        self.assertIn("@media (max-width: 480px)", self.analytics)
        self.assertIn("aside.controls select { min-height:44px; font-size:16px; }", self.analytics)
        self.assertIn("main.content { padding:12px; gap:10px; }", self.analytics)

    def test_codifier_confines_wide_content_to_local_scrollers(self):
        self.assertIn("html, body { max-width:100%; overflow-x:hidden; }", self.codifier)
        self.assertIn(".tabs, .subtabs {", self.codifier)
        self.assertIn("overflow-x:auto; overflow-y:hidden", self.codifier)
        self.assertIn(".segment-cards {", self.codifier)
        self.assertIn("scroll-snap-type:x proximity", self.codifier)
        self.assertIn("#pageSizeSelect { flex:1 0 100%; width:100%", self.codifier)

    def test_mobile_filter_panels_remain_inside_viewport(self):
        for source in (self.codifier, self.classifier):
            self.assertIn("left:8px !important; right:8px !important", source)
            self.assertIn("bottom:8px !important", source)
            self.assertIn("max-height:72vh", source)

    def test_classifier_releases_large_sticky_header_on_mobile(self):
        self.assertIn("header { position:relative; padding:12px 14px; }", self.classifier)
        self.assertIn(".toolbar input[type=text] { flex:1 0 100%", self.classifier)
        self.assertIn(".wrap { padding:10px 8px 28px", self.classifier)


if __name__ == "__main__":
    unittest.main()
