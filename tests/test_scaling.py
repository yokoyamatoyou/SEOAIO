import unittest
try:
    from seo_aio_streamlit import SEOAIOAnalyzer
except Exception:
    SEOAIOAnalyzer = None

@unittest.skipUnless(SEOAIOAnalyzer, "main module not available")
class TestScaling(unittest.TestCase):
    def setUp(self):
        # No API initialization for this test
        analyzer = object.__new__(SEOAIOAnalyzer)
        self.scale = analyzer._scale_to_100

    def test_scale_small(self):
        self.assertEqual(self.scale(7), 70)

    def test_scale_normal(self):
        self.assertEqual(self.scale(85), 85)

    def test_scale_over(self):
        self.assertEqual(self.scale(120), 100)

if __name__ == '__main__':
    unittest.main()
