"""Regressão de layout da faixa Black Friday na homepage."""
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

class BlackFridayHomeLayoutTest(unittest.TestCase):
    def test_image_stays_in_fixed_media_box(self):
        html = (ROOT / "index.html").read_text(encoding="utf-8")
        self.assertIn("bf-home-photo>img{display:block!important;position:absolute!important", html)
        self.assertIn("overflow:hidden!important;isolation:isolate", html)
        self.assertIn('class="bf-home-copy"', html)
        self.assertIn('class="bf-home-shop"', html)
        self.assertIn("flex:0 0 170px!important", html)
        self.assertIn("object-fit:contain!important", html)

if __name__ == "__main__":
    unittest.main()
