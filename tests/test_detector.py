import unittest
from core.industry_detector import IndustryDetector

class TestIndustryDetector(unittest.TestCase):
    def setUp(self):
        self.detector = IndustryDetector()

    def test_analyze_industries_basic(self):
        title = "最新のAIを活用したクラウドサービス"
        content = "AWSやDockerなどのテクノロジーを利用するシステム開発"
        result = self.detector.analyze_industries(title, content)
        self.assertEqual(result.primary_industry, "IT・テクノロジー")
        self.assertGreater(result.confidence_score, 0)
        self.assertIn("クラウド", result.industry_keywords)

if __name__ == '__main__':
    unittest.main()
