import unittest
from pathlib import Path
from html.parser import HTMLParser

class Inspector(HTMLParser):
    def __init__(self):super().__init__();self.ids=set();self.anchors=[];self.scripts=[]
    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        if "id" in a:self.ids.add(a["id"])
        if tag=="a":self.anchors.append(a.get("href",""))
        if tag=="script":self.scripts.append(a)

class SiteTests(unittest.TestCase):
    def test_static_links(self):
        root=Path(__file__).resolve().parents[1]/"site"
        parser=Inspector();parser.feed((root/"index.html").read_text(encoding="utf-8"))
        for href in parser.anchors:
            if href.startswith("#"):self.assertIn(href[1:],parser.ids)
            else:self.assertTrue(href.startswith("https://github.com/JeelNandaniya8/GHOSTDIFF"))
        self.assertEqual(parser.scripts,[])
        self.assertTrue((root/"style.css").is_file())
