import unittest
from ghostdiff.config import parse_config

class ConfigTests(unittest.TestCase):
    def test_restrict_config(self):
        data={"schema":"ghostdiff.config/v1","before":"http://localhost:3000","after":"http://localhost:3001","settings":{"depth":1},"bidirectional":True,"strict":False}
        self.assertEqual(parse_config(data)[2].depth,1)
        with self.assertRaises(ValueError):parse_config({**data,"settings":{"allow_writes":True}})
        with self.assertRaises(ValueError):parse_config({**data,"after":"https://example.com"})
        with self.assertRaises(ValueError):parse_config({**data,"strict":"true"})
