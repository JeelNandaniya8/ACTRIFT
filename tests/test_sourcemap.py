import unittest
from ghostdiff.sourcemap import SourceMap,vlq,map_locations

class MapsTests(unittest.TestCase):
    def test_decode(self):
        m=SourceMap({"version":3,"sources":["src/app.ts"],"names":["go"],"mappings":"AAAAA,K,CAAC;AACA"})
        self.assertEqual(m.lookup(1,1),{"path":"src/app.ts","line":1,"column":1,"symbol":"go"})
        self.assertIsNone(m.lookup(1,6))
        self.assertEqual(m.lookup(1,7)["column"],2)
        self.assertEqual(m.lookup(2,1)["line"],2)
        self.assertEqual(map_locations([{"path":"/app.js","line":1,"column":1}],{"/app.js":m})[0]["path"],"src/app.ts")
    def test_invalid(self):
        for value in ("g","!","ggggggggg"):
            with self.assertRaises(ValueError):vlq(value)
        with self.assertRaises(ValueError):SourceMap({"version":3,"sources":["https://example.com/a"],"mappings":"AAAA"})
