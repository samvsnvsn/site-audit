#!/usr/bin/env py -3
"""audit_extras.py --url URL : extended best-effort site checks (stdlib only).
Appends an 'EXTENDED CHECKS' section. Exit 0 always (extras never break audits)."""
import sys, argparse, urllib.request, ssl
from html.parser import HTMLParser

class P(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.title=[]; self.in_title=0; self.descriptions=[]; self.viewports=[]
        self.h1=[]; self.in_h1=0; self.imgs=0; self.imgs_noalt=0; self.canonical=[]
    def handle_starttag(self,t,a):
        d=dict(a)
        if t=="title": self.in_title=1
        elif t=="meta":
            if d.get("name","").lower()=="description" and d.get("content"): self.descriptions.append(d["content"])
            if d.get("name","").lower()=="viewport": self.viewports.append(d.get("content",""))
        elif t=="h1": self.in_h1=1
        elif t=="img":
            self.imgs+=1
            if not d.get("alt","").strip(): self.imgs_noalt+=1
        elif t=="link" and d.get("rel","").lower()=="canonical" and d.get("href"): self.canonical.append(d["href"])
    def handle_endtag(self,t):
        if t=="title": self.in_title=0
        elif t=="h1": self.in_h1=0
    def handle_data(self,x):
        if self.in_title: self.title.append(x)
        if self.in_h1: self.h1.append(x)

def run(url):
    ctx=ssl.create_default_context(); ctx.check_hostname=False; ctx.verify_mode=ssl.CERT_NONE
    req=urllib.request.Request(url,headers={"User-Agent":"Mozilla/5.0 site-audit/1"})
    r=urllib.request.urlopen(req,timeout=15,context=ctx)
    raw=r.read(500_000).decode("utf-8","replace")
    ct=r.headers.get("Content-Type","")
    out=[]
    if not ct.startswith("text/html"):
        out.append(f"- non-HTML content-type: {ct or 'unknown'} (skip tag checks)"); return out
    p=P(); p.feed(raw)
    title="".join(p.title).strip()
    out.append(f"- <title>: {'MISSING' if not title else repr(title[:90])} ({len(title)} chars{' — over 60, SERP clipping risk' if len(title)>60 else ''})")
    out.append(f"- meta description: {'MISSING' if not p.descriptions else repr(p.descriptions[0][:90])} ({len(p.descriptions[0]) if p.descriptions else 0} chars{' — over 160, SERP clipping risk' if p.descriptions and len(p.descriptions[0])>160 else ''})")
    out.append(f"- meta viewport: {'MISSING (mobile-unfriendly)' if not p.viewports else 'present'}")
    out.append(f"- <h1>: {len(p.h1)} ({'MISSING — weak SEO signal' if not p.h1 else 'ok'})")
    if p.imgs: out.append(f"- images missing alt: {p.imgs_noalt}/{p.imgs} ({'accessibility gap' if p.imgs_noalt else 'all have alt'})")
    out.append(f"- canonical link: {'MISSING' if not p.canonical else 'present ('+p.canonical[0][:70]+')'}")
    import re
    http_urls=re.findall(r'src=["\']http://[^"\']+|href=["\']http://[^"\']+',raw)
    if "https://" in url: out.append(f"- mixed-content refs (http:// assets over https page): {len(http_urls)}")
    return out

if __name__=="__main__":
    ap=argparse.ArgumentParser(); ap.add_argument("--url",required=True)
    a=ap.parse_args()
    print("\n=== EXTENDED CHECKS (audit_extras) ===")
    try:
        for line in run(a.url): print(line)
    except Exception as e:
        print(f"- extended checks unavailable: {type(e).__name__}: {e}")
    sys.exit(0)
