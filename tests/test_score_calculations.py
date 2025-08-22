import unittest
try:
    from seo_aio_streamlit import SEOAIOAnalyzer
except Exception:
    SEOAIOAnalyzer = None

@unittest.skipUnless(SEOAIOAnalyzer, "main module not available")
class TestScoreCalculations(unittest.TestCase):
    def setUp(self):
        analyzer = object.__new__(SEOAIOAnalyzer)
        self.title_score = analyzer._calculate_title_score
        self.meta_score = analyzer._calculate_meta_description_score
        self.head_score = analyzer._calculate_headings_score
        self.content_score = analyzer._calculate_content_score
        self.links_score = analyzer._calculate_links_score
        self.images_score = analyzer._calculate_images_score
        self.tech_score = analyzer._calculate_technical_score

    def test_title_score_perfect(self):
        self.assertEqual(self.title_score('a' * 50), 10)

    def test_meta_description_score_short(self):
        self.assertEqual(self.meta_score('a' * 50), 3)

    def test_headings_score_standard(self):
        headings = {'h1': 1, 'h2': 2}
        self.assertEqual(self.head_score(headings), 10)

    def test_content_score_balanced(self):
        self.assertAlmostEqual(self.content_score(500, 20), 8.6, places=1)

    def test_links_score_high(self):
        self.assertEqual(self.links_score(5, 3), 10)

    def test_images_score_mixed(self):
        self.assertEqual(self.images_score(1, 4), 2)

    def test_technical_score_none(self):
        self.assertAlmostEqual(self.tech_score(False, False, False), 5/3, places=2)

if __name__ == '__main__':
    unittest.main()
