#!/usr/bin/env py -3
"""extras_v2.py --url URL : security-header + crawlability + social-tag checks (stdlib)."""
import sys, argparse, urllib.request, urllib.error, ssl
from urllib.parse import urlsplit
def fetch(url, timeout=10):
    ctx=ssl.create_default_context(); ctx.check_hostname=False; ctx.verify_mode=ssl.CERT_NONE
    req=urllib.request.Request(url,headers={"User-Agent":"Mozilla/5.0 site-audit/1"})
    r=urllib.request.urlopen(req,timeout=timeout,context=ctx)
    return r.status, dict(r.headers), r.read(120_000).decode("utf-8","replace")
def main(url):
    o=urlsplit(url); base=f"{o.scheme}://{o.netloc}"; out=["\n=== EXTRA CHECKS (headers/robots/social) ==="]
    try:
        _,h,_=fetch(url)
        for name,label in (("strict-transport-security","HSTS"),("content-security-policy","CSP"),
                           ("x-content-type-options","X-Content-Type-Options"),("x-frame-options","X-Frame-Options"),
                           ("referrer-policy","Referrer-Policy")):
            out.append(f"- {label}: {'present' if h.get(name) else 'MISSING (security-hardening gap)'}")
    except Exception as e: out.append(f"- headers unavailable: {type(e).__name__}")
    st,_,b=fetch(f"{base}/robots.txt")
    out.append(f"- robots.txt: {'present'+(' (lists Sitemap:)' if 'sitemap' in b.lower() else '') if st==200 else f'MISSING (HTTP {st})'}")
    try:
        st,_,_=fetch(f"{base}/sitemap.xml"); out.append(f"- sitemap.xml: {'present' if st==200 else f'MISSING (HTTP {st})'}")
    except Exception as e: out.append(f"- sitemap.xml: unavailable ({type(e).__name__})")
    try:
        st,h,_=fetch(f"{base}/favicon.ico"); out.append(f"- favicon.ico: {'present' if st==200 else f'MISSING (HTTP {st})'}")
    except Exception as e: out.append(f"- favicon.ico: unavailable ({type(e).__name__})")
    import re
    m=re.findall(r'property=["\']og:(title|image)["\']',b)
    tw=re.findall(r'name=["\']twitter:card["\']',b)
    out.append(f"- Open Graph: og:title/og:image {len(m)}/2; twitter:card: {'present' if tw else 'missing'}")
    print("\n".join(out))
if __name__=="__main__":
    a=argparse.ArgumentParser(); a.add_argument("--url",required=True); u=a.parse_args().url
    try: main(u)
    except Exception as e: print(f"\n=== EXTRA CHECKS ===\n- unavailable: {type(e).__name__}: {e}")
    sys.exit(0)
