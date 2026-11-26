import unittest
from ghostdiff.engine import Action
from ghostdiff.matching import normalized,score,suggestions

class MatchingTests(unittest.TestCase):
    def test_synonyms(self):
        self.assertEqual(score("Export PDF","Download PDF"),1.0)
        self.assertEqual(score("Sign in","Login"),1.0)
    def test_wrong_role_and_unrelated_action(self):
        self.assertEqual(suggestions("button","Export PDF",[Action("link","Download PDF"),Action("button","Logout")]),[])
    def test_ambiguity_retained(self):
        results=suggestions("button","Export PDF",[Action("button","Download PDF"),Action("button","Export the PDF")])
        self.assertEqual(len(results),2)
        self.assertTrue(all(r["score"]==1 for r in results))
