#!/usr/bin/env python3
"""Tests for site_audit.py. Self-contained: serves fixture pages on localhost,
so no internet access is needed. Run via verify.sh or: python3 -m unittest -v
"""

import json
import os
import sys
import threading
import unittest
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from site_audit import audit_url, passed_count, render_email_summary, render_text  # noqa: E402

GOOD_PAGE = """<!doctype html><html lang="en"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="description" content="A hand-written description of this tidy little site that is long enough to pass.">
<meta property="og:title" content="Good Small Site">
<meta property="og:description" content="Handmade widgets.">
<link rel="canonical" href="http://127.0.0.1:{port}/">
<script type="application/ld+json">{{"@context":"http://schema.org"}}</script>
<title>Good Small Site - Handmade Widgets</title>
</head><body><h1>Handmade Widgets</h1>
<p>Fine widgets since forever. <a href="http://127.0.0.1:{port}/more">more</a></p>
<img src="w.jpg" alt="A widget">
</body></html>"""

BAD_PAGE = """<!doctype html><html><head><title>x</title></head><body>
<h1>One</h1><h1>Two</h1>
<img src="a.jpg"><img src="b.jpg">
</body></html>"""


MIN_PAGE = """<!doctype html><html lang=en><head><meta charset=utf-8><meta name=viewport content="width=device-width,initial-scale=1"><title>Minified Example Site</title><meta name=description content="A minified page whose attributes are not quoted, which is valid HTML5 and common today."><meta property=og:title content=Min><link rel=canonical href=/min></head><body><h1>Hi</h1><img src=a.png alt=logo></body></html>"""


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):  # noqa: N802
        path = urllib.parse.urlparse(self.path).path
        port = self.server.server_address[1]
        if path == "/robots.txt":
            body = b"User-agent: *\nAllow: /\n"
            self._send(200, body, "text/plain")
        elif path == "/sitemap.xml":
            self._send(200, b"<urlset></urlset>", "application/xml")
        elif path == "/favicon.ico":
            self._send(200, b"\x89PNG", "image/png")
        elif path == "/":
            self._send(200, GOOD_PAGE.format(port=port).encode(), "text/html")
        elif path == "/min":
            self._send(200, MIN_PAGE.encode(), "text/html")
        elif path == "/bad":
            self._send(200, BAD_PAGE.encode(), "text/html")
        else:
            self._send(404, b"nope", "text/plain")

    def _send(self, code, body, ctype):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *a):  # silence
        pass


class TestSiteAudit(unittest.TestCase):
    server = None
    base = None

    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        cls.base = f"http://127.0.0.1:{cls.server.server_address[1]}"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()

    def test_minified_unquoted_attributes_are_understood(self):
        res = audit_url(self.base + "/min", timeout=5)
        by = {c["check"]: c["passed"] for c in res.checks}
        for name in ("mobile viewport", "html lang", "meta description", "social preview (og:)", "canonical link", "image alt text"):
            self.assertTrue(by[name], name)

    def test_good_page_passes(self):
        res = audit_url(self.base + "/", timeout=5)
        names = {c["check"]: c["passed"] for c in res.checks}
        for check in ("site reachable", "robots.txt", "sitemap.xml", "favicon",
                      "page title", "meta description", "single H1",
                      "mobile viewport", "html lang", "structured data",
                      "image alt text", "page weight", "response time"):
            self.assertIn(check, names, f"missing check: {check}")
        self.assertTrue(names["site reachable"])
        self.assertTrue(names["page title"], str(names))
        self.assertTrue(names["meta description"])
        self.assertTrue(names["single H1"])
        self.assertTrue(names["mobile viewport"])
        self.assertTrue(names["image alt text"])
        self.assertEqual(res.issues, [])

    def test_bad_page_flags_issues(self):
        res = audit_url(self.base + "/bad", timeout=5)
        names = {c["check"]: c["passed"] for c in res.checks}
        self.assertFalse(names["page title"])
        self.assertFalse(names["single H1"])       # two H1s
        self.assertFalse(names["mobile viewport"])
        self.assertFalse(names["html lang"])
        self.assertFalse(names["meta description"])
        self.assertFalse(names["image alt text"])  # 2 images, no alt
        self.assertFalse(names["canonical link"])
        self.assertFalse(names["structured data"])
        self.assertGreaterEqual(len(res.issues), 8)

    def test_missing_404_page(self):
        res = audit_url(self.base + "/missing", timeout=5)
        names = {c["check"]: c["passed"] for c in res.checks}
        self.assertFalse(names["site reachable"])
        self.assertEqual(res.issues[0].severity, "high")

    def test_unreachable_site(self):
        # port 1 on localhost: nothing listening, fast refusal
        res = audit_url("http://127.0.0.1:1/", timeout=2)
        self.assertFalse(res.checks[0]["passed"])
        self.assertEqual(res.issues[0].severity, "high")

    def test_invalid_url_raises(self):
        with self.assertRaises(ValueError):
            audit_url("not-a-url")

    def test_score_and_summary(self):
        res = audit_url(self.base + "/bad", timeout=5)
        total = len(res.checks)
        self.assertGreater(total, 10)
        self.assertLessEqual(passed_count(res), total)
        text = render_text(res)
        self.assertIn("Score:", text)
        self.assertIn("Top issues:", text)
        mail = render_email_summary(res, "example.test")
        self.assertIn("Subject: Free audit of example.test", mail)
        self.assertIn("automaton-revenue@agentmail.to", mail)
        # at most 3 issues in the free summary
        numbered = [ln for ln in mail.splitlines() if ln[:2] in ("1.", "2.", "3.")]
        self.assertEqual(len(numbered), 3)

    def test_json_payload_shape(self):
        res = audit_url(self.base + "/", timeout=5)
        payload = {
            "url": res.url, "checks": res.checks,
            "issues": [vars(i) for i in res.issues],
            "passed": passed_count(res), "total_checks": len(res.checks),
        }
        s = json.dumps(payload)
        self.assertIn('"total_checks"', s)
        self.assertIsInstance(payload["passed"], int)


if __name__ == "__main__":
    unittest.main(verbosity=2)