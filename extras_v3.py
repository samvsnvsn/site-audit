#!/usr/bin/env py -3
"""extras_v3.py --url URL : performance + link-health checks (stdlib).
Measures load time, page size, compression, cache headers, and samples internal links.
404-tolerant: link failures are reported as findings, never crash the run."""
import sys, argparse, time, ssl, re, urllib.request, urllib.error
from urllib.parse import urlsplit, urljoin

def fetch(url, timeout=10, head=False):
    ctx = ssl.create_default_context(); ctx.check_hostname = False; ctx.verify_mode = ssl.CERT_NONE
    method = "HEAD" if head else "GET"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 site-audit/1"}, method=method)
    r = urllib.request.urlopen(req, timeout=timeout, context=ctx)
    body = b"" if head else r.read(1_000_000)
    return r.status, dict(r.headers), body

def link_status(url):
    try:
        st, _, _ = fetch(url, timeout=8, head=True); return st
    except urllib.error.HTTPError as e:
        return e.code
    except Exception:
        return None

def main(url):
    o = urlsplit(url); base = o.scheme + "://" + o.netloc
    out = ["\n=== PERF & LINK CHECKS (extras_v3) ==="]
    t0 = time.time()
    try:
        st, h, body = fetch(url)
    except Exception as e:
        out.append("- page fetch failed: " + type(e).__name__ + ": " + str(e))
        print("\n".join(out)); return
    dt = time.time() - t0
    kb = len(body) / 1024.0
    enc = h.get("Content-Encoding", "")
    out.append("- load time: %.2fs%s" % (dt, " (SLOW, over 2s budget)" if dt > 2.0 else " (ok)"))
    out.append("- html size: %.1f KB%s" % (kb, " (heavy, over 300KB)" if kb > 300 else ""))
    gz = "gzip" in enc.lower() or "br" in enc.lower()
    out.append("- compression: " + ("present (" + enc + ")" if gz else "NOT enabled (bandwidth waste)"))
    cc = h.get("Cache-Control", "")
    out.append("- cache-control: " + (cc if cc else "MISSING (no caching policy)"))
    # sample internal links
    links = re.findall(r'href=["\']([^"\']+)["\']', body.decode("utf-8", "replace"))
    internal = []
    for l in links:
        if l.startswith("#") or l.startswith("mailto:") or l.startswith("tel:"):
            continue
        u = urljoin(url, l)
        if urlsplit(u).netloc == o.netloc and u not in internal:
            internal.append(u)
    sample = internal[:5]
    if not sample:
        out.append("- internal links: none found to sample")
    else:
        out.append("- link health (sampled %d of %d internal):" % (len(sample), len(internal)))
        broken = 0
        for u in sample:
            s = link_status(u)
            if s is None:
                out.append("    ? unreachable: " + u[:70])
            elif s >= 400:
                broken += 1
                out.append("    BROKEN (HTTP " + str(s) + "): " + u[:70])
        if broken:
            out.append("- broken links found: " + str(broken) + " (fix these)")
        else:
            out.append("- broken links found: 0")
    print("\n".join(out))

if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--url", required=True)
    u = ap.parse_args().url
    try:
        main(u)
    except Exception as e:
        print("\n=== PERF & LINK CHECKS ===")
        print("- unavailable: " + type(e).__name__ + ": " + str(e))
    sys.exit(0)
