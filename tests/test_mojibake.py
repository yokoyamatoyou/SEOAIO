import unittest

try:
    from core.text_utils import detect_mojibake
except Exception:
    detect_mojibake = None


class TestMojibake(unittest.TestCase):
    @unittest.skipUnless(detect_mojibake, "text utilities not available")
    def test_detect_clean_text(self):
        self.assertFalse(detect_mojibake("これは正常なテキストです。"))

    @unittest.skipUnless(detect_mojibake, "text utilities not available")
    def test_detect_garble(self):
        self.assertTrue(detect_mojibake("Ã§Â¨Â³"))

if __name__ == '__main__':
    unittest.main()
