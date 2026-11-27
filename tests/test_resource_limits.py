import os
import unittest
from ghostdiff.engine import BoundedEvents,Settings,compare
from ghostdiff.demo import serve

class EventLimits(unittest.TestCase):
    def test_bounded_sample_and_reset(self):
        events=BoundedEvents(2)
        for i in range(1000): events.append(i)
        self.assertEqual(events,[0,1])
        self.assertTrue(events.overflow)
        events.clear()
        self.assertEqual(events,[])
        self.assertFalse(events.overflow)

@unittest.skipUnless(os.environ.get("GHOSTDIFF_BROWSER_TESTS")=="1","requires browser")
class BrowserLimits(unittest.TestCase):
    def test_error_flood_is_not_verified(self):
        good=b"""<html><body><button onclick="document.querySelector('p').textContent='Done'">Run</button><p>Ready</p></body></html>"""
        bad=b"""<html><body><button onclick="document.querySelector('p').textContent='Done';for(let i=0;i<30;i++){setTimeout(()=>{throw Error('fixture')},0)}">Run</button><p>Ready</p></body></html>"""
        with serve(good) as a,serve(bad) as b:
            r=compare(a,b,Settings(depth=1,budget=2,settle_ms=500))
        row=r["paths"][1]
        self.assertEqual(row["status"],"inconclusive")
        self.assertEqual(row["after"][0]["reason"],"Browser event observation limit exceeded")

    def test_oversized_named_inventory(self):
        html=("<html><body>"+"".join(f"<button>Action {i}</button>" for i in range(257))+"</body></html>").encode()
        with serve(html) as a,serve(html) as b:
            r=compare(a,b,Settings(depth=1,budget=2,settle_ms=50))
        self.assertEqual(r["summary"],{"inconclusive":1})
        self.assertIn("256",r["paths"][0]["before"][0]["reason"])
