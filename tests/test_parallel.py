import unittest
from ghostdiff.engine import Settings,compare

class ParallelPolicyTests(unittest.TestCase):
    def test_shared_origin_rejected(self):
        with self.assertRaises(ValueError):
            compare("http://127.0.0.1:3000/a","http://127.0.0.1:3000/b",Settings(parallel=True))
    def test_write_mode_rejected(self):
        with self.assertRaises(ValueError):
            compare("http://127.0.0.1:3000","http://127.0.0.1:3001",Settings(parallel=True,allow_writes=True))
    def test_invalid_flag(self):
        with self.assertRaises(ValueError):Settings(parallel="yes").validate()
