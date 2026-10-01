"""Regression tests for audit_extras.py (v1) and extras_v2.py (v2).
Runs a local HTTP fixture server - no internet required. Stdlib only.
  py -3 -m unittest test_extras -v
"""
import unittest, threading, socket, tempfile, os, io, contextlib, shutil
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler

HTML_TMPL = """<!doctype html><html><head><title>Fixture Site - Quality Co</title>
<meta name="description" content="We fix websites fast.">
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="canonical" href="LOCALBASE/">
<meta property="og:title" content="Fixture">
<meta property="og:image" content="LOCALBASE/og.png">
<meta name="twitter:card" content="summary"></head>
<body><h1>Quality Co</h1><img src="a.png" alt="A"><img src="b.png"></body></html>"""

ROBOTS = "User-agent: *\nDisallow: /\nSitemap: LOCALBASE/sitemap.xml\n"
SITEMAP = '<?xml version="1.0"?><urlset><url><loc>LOCALBASE/</loc></url></urlset>'
FAVICON = b"\x00\x00\x01\x00\x00\x01\x01\x00"

class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *a): pass

def make_server(directory):
    handler = lambda *a, **k: QuietHandler(*a, directory=directory, **k)
    srv = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    t = threading.Thread(target=srv.serve_forever, daemon=True); t.start()
    return srv

def setUpModule():
    global SRV_FULL, SRV_SPARSE, BASE_FULL, BASE_SPARSE, TMP
    TMP = tempfile.mkdtemp(prefix="sa-fixtures-")
    d_full = os.path.join(TMP, "full"); d_sparse = os.path.join(TMP, "sparse")
    os.makedirs(d_full); os.makedirs(d_sparse)
    html = HTML_TMPL.replace("LOCALBASE", "http://127.0.0.1")  # fixed below per-server
    for d, base, with_extras in ((d_full, None, True), (d_sparse, None, False)):
        pass
    # full fixture: everything present
    b_full = "http://127.0.0.1:%d" % 0  # placeholder, set after servers start
    SRV_FULL = make_server(d_full); SRV_SPARSE = make_server(d_sparse)
    BASE_FULL = "http://127.0.0.1:%d" % SRV_FULL.server_address[1]
    BASE_SPARSE = "http://127.0.0.1:%d" % SRV_SPARSE.server_address[1]
    with open(os.path.join(d_full, "index.html"), "w", encoding="utf-8") as f:
        f.write(HTML_TMPL.replace("LOCALBASE", BASE_FULL))
    with open(os.path.join(d_full, "robots.txt"), "w", encoding="utf-8") as f:
        f.write(ROBOTS.replace("LOCALBASE", BASE_FULL))
    with open(os.path.join(d_full, "sitemap.xml"), "w", encoding="utf-8") as f:
        f.write(SITEMAP.replace("LOCALBASE", BASE_FULL))
    with open(os.path.join(d_full, "favicon.ico"), "wb") as f:
        f.write(FAVICON)
    # sparse fixture: same html, NO robots/sitemap/favicon (regression: 404 must not kill v2)
    with open(os.path.join(d_sparse, "index.html"), "w", encoding="utf-8") as f:
        f.write(HTML_TMPL.replace("LOCALBASE", BASE_SPARSE))

def tearDownModule():
    global SRV_FULL, SRV_SPARSE, TMP
    try: SRV_FULL.shutdown(); SRV_SPARSE.shutdown()
    except Exception: pass
    shutil.rmtree(TMP, ignore_errors=True)

def v1_lines(url):
    import audit_extras
    return audit_extras.run(url)

def v2_out(url):
    import extras_v2
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        extras_v2.main(url)
    return buf.getvalue()

class TestExtrasV1(unittest.TestCase):
    def test_full_fixture_findings(self):
        out = "\n".join(v1_lines(BASE_FULL + "/index.html"))
        self.assertIn("Fixture Site - Quality Co", out)
        self.assertIn("We fix websites fast.", out)
        self.assertIn("viewport: present", out)
        self.assertIn("<h1>: 1", out)
        self.assertIn("images missing alt: 1/2", out)
        self.assertIn("canonical link: present", out)

class TestExtrasV2(unittest.TestCase):
    def test_all_present(self):
        out = v2_out(BASE_FULL + "/index.html")
        self.assertIn("robots.txt: present (lists Sitemap:)", out)
        self.assertIn("sitemap.xml: present", out)
        self.assertIn("favicon.ico: present", out)
        self.assertIn("og:title/og:image 2/2", out)
        self.assertIn("twitter:card: present", out)
    def test_404_tolerant(self):
        out = v2_out(BASE_SPARSE + "/index.html")
        self.assertIn("robots.txt: MISSING (HTTP 404)", out)
        self.assertIn("sitemap.xml: MISSING (HTTP 404)", out)
        self.assertIn("favicon.ico: MISSING (HTTP 404)", out)
    def test_no_crash_exit(self):
        # run() must never raise for a reachable page
        try:
            v2_out(BASE_SPARSE + "/index.html"); ok = True
        except Exception: ok = False
        self.assertTrue(ok)

if __name__ == "__main__":
    unittest.main()


def v3_out(url):
    import extras_v3
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        extras_v3.main(url)
    return buf.getvalue()


class TestExtrasV3(unittest.TestCase):
    def test_perf_metrics_present(self):
        out = v3_out(BASE_FULL + "/index.html")
        self.assertIn("load time:", out)
        self.assertIn("html size:", out)
        self.assertIn("compression:", out)
        self.assertIn("cache-control:", out)

    def test_link_sampling(self):
        out = v3_out(BASE_FULL + "/index.html")
        self.assertIn("link health (sampled", out)
        self.assertIn("broken links found:", out)

    def test_no_crash_on_unreachable_page(self):
        # a 404 page must not crash the module
        try:
            out = v3_out(BASE_FULL + "/nonexistent-page-xyz.html")
            ok = True
        except Exception:
            ok = False
        self.assertTrue(ok)
