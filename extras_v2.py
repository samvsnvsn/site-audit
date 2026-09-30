#!/usr/bin/env py -3
"""extras_v2.py --url URL : security-header + crawlability + social-tag checks (stdlib).
Never dies on 404s — reports MISSING and continues."""
import sys, argparse, urllib.request, urllib.error, ssl, re
from urllib.parse import urlsplit
def fetch(url, timeout=10):
    ctx=ssl.create_default_context(); ctx.check_hostname=False; ctx.verify_mode=ssl.CERT_NONE
    req=urllib.request.Request(url,headers={"User-Agent":"Mozilla/5.0 site-audit/1"})
    r=urllib.request.urlopen(req,timeout=timeout,context=ctx)
    return r.status, dict(r.headers), r.read(120_000).decode("utf-8","replace")
def status_of(url):
    """Return (status|None, body|None) — HTTPError is a result, not a crash."""
    try:
        st,h,b=fetch(url); return st,b
    except urllib.error.HTTPError as e:
        return e.code,None
    except Exception:
        return None,None
def main(url):
    o=urlsplit(url); base=f"{o.scheme}://{o.netloc}"; out=["\n=== EXTRA CHECKS (headers/robots/social) ==="]
    try:
        _,h,_=fetch(url)
        for name,label in (("strict-transport-security","HSTS"),("content-security-policy","CSP"),
                           ("x-content-type-options","X-Content-Type-Options"),("x-frame-options","X-Frame-Options"),
                           ("referrer-policy","Referrer-Policy")):
            out.append(f"- {label}: {'present' if h.get(name) else 'MISSING (security-hardening gap)'}")
    except Exception as e: out.append(f"- headers unavailable: {type(e).__name__}")
    st,b=status_of(f"{base}/robots.txt")
    if st==200 and b is not None:
        out.append(f"- robots.txt: present{ ' (lists Sitemap:)' if 'sitemap' in b.lower() else '' }")
    else:
        out.append(f"- robots.txt: MISSING (HTTP {st if st else 'error'})")
    st,_=status_of(f"{base}/sitemap.xml")
    out.append(f"- sitemap.xml: {'present' if st==200 else f'MISSING (HTTP {st if st else \"error\"})'}")
    st,_=status_of(f"{base}/favicon.ico")
    out.append(f"- favicon.ico: {'present' if st==200 else f'MISSING (HTTP {st if st else \"error\"})'}")
    st,b=status_of(url)
    if b:
        m=re.findall(r'property=["\']og:(title|image)["\']',b)
        tw=re.findall(r'name=["\']twitter:card["\']',b)
        out.append(f"- Open Graph: og:title/og:image {len(m)}/2; twitter:card: {'present' if tw else 'missing'}")
    print("\n".join(out))
if __name__=="__main__":
    a=argparse.ArgumentParser(); a.add_argument("--url",required=True); u=a.parse_args().url
    try: main(u)
    except Exception as e: print(f"\n=== EXTRA CHECKS ===\n- unavailable: {type(e).__name__}: {e}")
    sys.exit(0)
