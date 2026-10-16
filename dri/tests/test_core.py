import sys
import unittest
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from bot import should_run, mode_for, is_trusted, parse_json, make_cover

class Tests(unittest.TestCase):
    def test_dst_winter(self):
        self.assertTrue(should_run(datetime(2026,12,14,6,35,tzinfo=ZoneInfo("UTC"))))
        self.assertFalse(should_run(datetime(2026,12,14,5,35,tzinfo=ZoneInfo("UTC"))))
    def test_dst_summer(self):
        self.assertTrue(should_run(datetime(2026,7,20,5,35,tzinfo=ZoneInfo("UTC"))))
        self.assertFalse(should_run(datetime(2026,7,20,6,35,tzinfo=ZoneInfo("UTC"))))
    def test_sunday(self):
        self.assertEqual(mode_for(datetime(2026,10,18,7,35,tzinfo=ZoneInfo("Europe/Copenhagen"))),"weekly")
    def test_saturday(self):
        self.assertFalse(should_run(datetime(2026,10,17,7,35,tzinfo=ZoneInfo("Europe/Copenhagen"))))
    def test_sources(self):
        self.assertTrue(is_trusted("https://www.ecb.europa.eu/example"))
        self.assertFalse(is_trusted("https://reuters.com.evil.com/example"))
    def test_json(self):
        self.assertEqual(parse_json('{"a":1}'),{"a":1})
    def test_cover(self):
        import tempfile
        from PIL import Image
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/"cover.jpg"
            make_cover("DAGENS MARKEDER","Makro og renter",None,path)
            with Image.open(path) as im: self.assertEqual(im.size,(1080,1350))

if __name__=="__main__":
    unittest.main()
