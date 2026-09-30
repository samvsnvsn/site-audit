#!/usr/bin/env py -3
"""extras_v2.py --url URL : security-header + crawlability + social-tag checks (stdlib).
Never dies on 404s - reports MISSING and continues."""
import sys, argparse, urllib.request, urllib.error, ssl, re
from urllib.parse import urlsplit

def fetch(url, timeout=10):
    ctx = ssl.create_default_context(); ctx.check_hostname = False; ctx.verify_mode = ssl.CERT_NONE
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 site-audit/1"})
    r = urllib.request.urlopen(req, timeout=timeout, context=ctx)
    return r.status, dict(r.headers), r.read(120_000).decode("utf-8", "replace")

def status_of(url):
    try:
        st, h, b = fetch(url); return st, b
    except urllib.error.HTTPError as e:
        return e.code, None
    except Exception:
        return None, None

def present_or_missing(label, ok, detail):
    if ok:
        return "- " + label + ": present"
    return "- " + label + ": MISSING (" + detail + ")"

def main(url):
    o = urlsplit(url); base = o.scheme + "://" + o.netloc
    out = ["\n=== EXTRA CHECKS (headers/robots/social) ==="]
    try:
        _, h, _ = fetch(url)
        for name, label in (("strict-transport-security", "HSTS"),
                            ("content-security-policy", "CSP"),
                            ("x-content-type-options", "X-Content-Type-Options"),
                            ("x-frame-options", "X-Frame-Options"),
                            ("referrer-policy", "Referrer-Policy")):
            if h.get(name):
                out.append("- " + label + ": present")
            else:
                out.append("- " + label + ": MISSING (security-hardening gap)")
    except Exception as e:
        out.append("- headers unavailable: " + type(e).__name__)
    st, b = status_of(base + "/robots.txt")
    if st == 200 and b is not None:
        line = "- robots.txt: present"
        if "sitemap" in b.lower():
            line += " (lists Sitemap:)"
        out.append(line)
    else:
        out.append(present_or_missing("robots.txt", False, "HTTP " + str(st)))
    st, _ = status_of(base + "/sitemap.xml")
    out.append(present_or_missing("sitemap.xml", st == 200, "HTTP " + str(st)))
    st, _ = status_of(base + "/favicon.ico")
    out.append(present_or_missing("favicon.ico", st == 200, "HTTP " + str(st)))
    st, b = status_of(url)
    if b:
        m = re.findall(r'property=["\']og:(title|image)["\']', b)
        tw = re.findall(r'name=["\']twitter:card["\']', b)
        out.append("- Open Graph: og:title/og:image " + str(len(m)) + "/2; twitter:card: " +
                   ("present" if tw else "missing"))
    print("\n".join(out))

if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--url", required=True)
    u = ap.parse_args().url
    try:
        main(u)
    except Exception as e:
        print("\n=== EXTRA CHECKS ===")
        print("- unavailable: " + type(e).__name__ + ": " + str(e))
    sys.exit(0)
