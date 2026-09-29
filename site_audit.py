#!/usr/bin/env python3
"""site-audit: a small, honest website audit for small-site owners.

Runs ~16 non-invasive checks against a public URL using only the Python
standard library, then prints a human-readable report, a JSON blob, and a
3-issue email summary (the free teaser for the paid full fix report).

Built and operated by Automaton, an AI agent (human-supervised).

Usage:
  python3 site_audit.py --url https://example.com
  python3 site_audit.py --url https://example.com --json report.json
  python3 site_audit.py --url https://example.com --email-summary
"""

from __future__ import annotations

import argparse
import json
import re
import socket
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from typing import List, Optional

USER_AGENT = "AutomatonSiteAudit/1.0 (+AI agent audit; contact: automaton-revenue@agentmail.to)"

TITLE_RE = re.compile(r"<title[^>]*>(.*?)</title>", re.I | re.S)
DESC_RE = re.compile(r'<meta[^>]+name=["\']description["\'][^>]*>', re.I)
VIEWPORT_RE = re.compile(r'<meta[^>]+name=["\']viewport["\'][^>]*>', re.I)
H1_RE = re.compile(r"<h1[\s>]", re.I)
IMG_RE = re.compile(r"<img\b[^>]*>", re.I)
ALT_RE = re.compile(r'alt\s*=\s*["\'][^"\']+["\']', re.I)
LDJSON_RE = re.compile(r'application/ld\+json', re.I)
CANONICAL_RE = re.compile(r'<link[^>]+rel=["\']canonical["\'][^>]*>', re.I)
HTTP_RES_RE = re.compile(r"""(src|href)\s*=\s*["']http://[^"']+["']""", re.I)
LANG_RE = re.compile(r"<html[^>]*\blang\s*=\s*[\"'][^\"']+[\"']", re.I)
OG_RE = re.compile(r'<meta[^>]+property=["\']og:', re.I)


@dataclass
class Issue:
    """One audit finding. severity in {high, medium, low, info}."""
    check: str
    severity: str
    finding: str
    fix: str


@dataclass
class AuditResult:
    url: str
    final_url: str = ""
    status: int = 0
    response_ms: int = 0
    page_bytes: int = 0
    checks: List[dict] = field(default_factory=list)
    issues: List[Issue] = field(default_factory=list)

    def add(self, check: str, passed: bool, detail: str,
            severity: Optional[str] = None, fix: str = "") -> None:
        self.checks.append({"check": check, "passed": bool(passed), "detail": detail})
        if not passed and severity:
            self.issues.append(Issue(check, severity, detail, fix))


def _fetch(url: str, timeout: int) -> tuple:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    start = time.monotonic()
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        body = resp.read(2_000_000)
        ms = int((time.monotonic() - start) * 1000)
        return resp.status, resp.geturl(), resp.headers, body, ms


def _try(url: str, timeout: int):
    try:
        return _fetch(url, timeout)
    except urllib.error.HTTPError as e:
        return e.code, url, e.headers or {}, b"", 0
    except (urllib.error.URLError, socket.timeout, ValueError, OSError):
        return None, url, {}, b"", 0


def audit_url(url: str, timeout: int = 10) -> AuditResult:
    """Run all checks against `url`. Network failures become one high issue."""
    res = AuditResult(url=url)
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        raise ValueError(f"not a valid http(s) URL: {url!r}")

    status, final_url, headers, body, ms = _try(url, timeout)
    if status is None:
        res.add("site reachable", False, f"could not fetch {url}", "high",
                "Check DNS/hosting; the site did not answer our request.")
        return res
    res.status, res.final_url, res.response_ms, res.page_bytes = status, final_url, ms, len(body)
    html = body.decode("utf-8", "replace")
    res.add("site reachable", 200 <= status < 400, f"HTTP {status} in {ms} ms, {len(body)} bytes",
            "high" if status >= 400 else None,
            f"Server returned HTTP {status}. Fix the page or hosting so it returns 200.")

    # 1. HTTPS enforced (http:// should redirect to https://)
    if parsed.scheme == "https":
        hs = urllib.parse.urlunparse(parsed._replace(scheme="http"))
        hstatus, hfinal, _, _, _ = _try(hs, timeout)
        redirected = bool(hfinal and hfinal.startswith("https://"))
        res.add("https enforced", redirected,
                f"http:// probe: HTTP {hstatus}, final={hfinal}",
                "medium",
                "Visitors typing your domain without https get an error or an insecure page. "
                "Add a redirect from http:// to https:// on your host.")

    # 2. robots.txt
    rstatus, _, _, rbody, _ = _try(urllib.parse.urljoin(final_url, "/robots.txt"), timeout)
    res.add("robots.txt", rstatus == 200 and bool(rbody.strip()), f"HTTP {rstatus}",
            "medium",
            "No robots.txt found. Search engines guess at crawl rules; add one that "
            "points to your sitemap.")

    # 3. sitemap.xml
    sstatus, _, _, _, _ = _try(urllib.parse.urljoin(final_url, "/sitemap.xml"), timeout)
    res.add("sitemap.xml", sstatus == 200, f"HTTP {sstatus}", "medium",
            "No /sitemap.xml found. Add one so search engines index every page you have.")

    # 4. favicon
    fstatus, _, _, _, _ = _try(urllib.parse.urljoin(final_url, "/favicon.ico"), timeout)
    has_favicon = fstatus == 200 or "icon" in html.lower()
    res.add("favicon", has_favicon, f"HTTP {fstatus}", "low",
            "No favicon found. Browsers show a generic icon on your tab and bookmarks.")

    if 200 <= status < 400:
        # 5. title
        m = TITLE_RE.search(html)
        title = (m.group(1).strip() if m else "")
        ok = 10 <= len(title) <= 65
        res.add("page title", ok, f"{len(title)} chars: {title[:60]!r}", "high",
                "Your <title> is missing or the wrong length (10-65 chars is ideal). "
                "It is the headline of your Google listing.")
        # 6. meta description
        dm = DESC_RE.search(html)
        desc = ""
        if dm:
            cm = re.search(r'content\s*=\s*["\']([^"\']*)["\']', dm.group(0), re.I)
            desc = cm.group(1) if cm else ""
        ok = 50 <= len(desc) <= 160
        res.add("meta description", ok, f"{len(desc)} chars", "medium",
                "Missing or poorly-sized meta description (50-160 chars). Google often "
                "shows it under your title in results.")
        # 7. single H1
        h1s = len(H1_RE.findall(html))
        res.add("single H1", h1s == 1, f"{h1s} H1 tags", "medium",
                "Exactly one H1 is expected on the page; you have "
                f"{h1s}. Keep the main headline as the only H1.")
        # 8. viewport / mobile
        res.add("mobile viewport", bool(VIEWPORT_RE.search(html)),
                "viewport meta present" if VIEWPORT_RE.search(html) else "no viewport meta",
                "high",
                "No <meta name=viewport> tag. On phones your site renders zoomed-out "
                "and Google ranks it lower.")
        # 9. html lang
        res.add("html lang", bool(LANG_RE.search(html)), "lang attribute",
                "low", 'Set <html lang="..."> so screen readers and translators '
                "know the page language.")
        # 10. Open Graph tags
        res.add("social preview (og:)", bool(OG_RE.search(html)),
                "og: tags" if OG_RE.search(html) else "no og: tags", "low",
                "Add Open Graph tags so links shared on social apps show a title, "
                "description and image instead of a bare URL.")
        # 11. canonical
        res.add("canonical link", bool(CANONICAL_RE.search(html)), "canonical",
                "low", "Add <link rel=canonical> to avoid duplicate-page confusion "
                "in search engines.")
        # 12. structured data
        res.add("structured data", bool(LDJSON_RE.search(html)), "ld+json",
                "low", "No schema.org JSON-LD found. Adding it can earn rich results "
                "(hours, ratings, breadcrumbs) in Google.")
        # 13. mixed content on https pages
        if final_url.startswith("https://"):
            mixed = HTTP_RES_RE.findall(html)
            res.add("no mixed content", not mixed,
                    f"{len(mixed)} http:// resources", "high",
                    "Your https page loads http:// resources. Browsers flag the page "
                    "'Not secure' and block some assets. Serve everything over https.")
        # 14. image alt attributes
        imgs = IMG_RE.findall(html)
        missing = [t for t in imgs if not ALT_RE.search(t)]
        res.add("image alt text", not missing or not imgs,
                f"{len(missing)}/{len(imgs)} images missing alt", "medium",
                f"{len(missing)} of {len(imgs)} <img> tags have no alt text. That hurts "
                "accessibility and image search.")
        # 15. page weight
        heavy = len(body) > 1_500_000
        res.add("page weight", not heavy, f"{len(body)} bytes", "medium",
                f"HTML alone is {len(body)/1_000_000:.1f} MB. Trim inline scripts/styles; "
                "mobile visitors on slow connections will bounce.")
        # 16. response time
        slow = ms > 2500
        res.add("response time", not slow, f"{ms} ms", "medium",
                f"First byte to full HTML took {ms} ms. Enable caching/CDN or trim the "
                "page; aim for under 2500 ms.")
    else:
        res.add("page content", False, f"page not usable: HTTP {status}", "high",
                "We audited only the HTTP response because the page did not return 200.")

    res.issues.sort(key=lambda i: {"high": 0, "medium": 1, "low": 2, "info": 3}[i.severity])
    return res


def passed_count(res: AuditResult) -> int:
    return sum(1 for c in res.checks if c["passed"])


def render_text(res: AuditResult) -> str:
    lines = [f"Site audit: {res.url}", f"Final URL: {res.final_url} (HTTP {res.status}, "
             f"{res.response_ms} ms, {res.page_bytes} bytes)", ""]
    for c in res.checks:
        lines.append(f"[{'PASS' if c['passed'] else 'FAIL'}] {c['check']}: {c['detail']}")
    lines.append("")
    lines.append(f"Score: {passed_count(res)}/{len(res.checks)} checks passed, "
                 f"{len(res.issues)} issue(s).")
    if res.issues:
        lines.append("")
        lines.append("Top issues:")
        for i, iss in enumerate(res.issues[:3], 1):
            lines.append(f"  {i}. ({iss.severity}) {iss.check} - {iss.finding}")
        lines.append("")
        lines.append("The full prioritized fix report (every issue, step-by-step fix, "
                     "effort estimate) is available on Gumroad - see README.")
    return "\n".join(lines)


def render_email_summary(res: AuditResult, site: str) -> str:
    """The free 3-issue summary email body (plain text)."""
    n = len(res.issues)
    lines = [
        f"Subject: Free audit of {site}: {n} issue{'s' if n != 1 else ''} found",
        "",
        "Hi,",
        "",
        f"You once asked us about your site, so we ran our automated audit on "
        f"{site} (built and operated by Automaton, an AI agent - human-supervised).",
        "",
        f"Result: {passed_count(res)}/{len(res.checks)} checks passed. "
        f"Here are the {min(3, n)} most important issues:",
        "",
    ]
    for i, iss in enumerate(res.issues[:3], 1):
        lines.append(f"{i}. [{iss.severity.upper()}] {iss.check}")
        lines.append(f"   Found: {iss.finding}")
        lines.append(f"   Fix:   {iss.fix}")
        lines.append("")
    if n > 3:
        lines.append(f"(+{n - 3} more issues found)")
    lines += [
        "Want the full prioritized fix report? It lists every issue with a",
        "step-by-step fix and an effort estimate. Pay what you want",
        "(suggested $5) on Gumroad - link in the README of the project page,",
        "or just reply to this email and we'll send it.",
        "",
        "- Automaton (AI agent, human-supervised)",
        "  automaton-revenue@agentmail.to",
    ]
    return "\n".join(lines)


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="Automated website audit (AI-built).")
    ap.add_argument("--url", required=True, help="site to audit, e.g. https://example.com")
    ap.add_argument("--timeout", type=int, default=10)
    ap.add_argument("--json", dest="json_path", help="write full result JSON here")
    ap.add_argument("--email-summary", action="store_true",
                    help="print the free 3-issue email body instead of the report")
    ap.add_argument("--site-name", default="", help="label used in the email summary")
    args = ap.parse_args(argv)

    try:
        res = audit_url(args.url, timeout=args.timeout)
    except ValueError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1

    if args.json_path:
        payload = {
            "url": res.url, "final_url": res.final_url, "status": res.status,
            "response_ms": res.response_ms, "page_bytes": res.page_bytes,
            "checks": res.checks,
            "issues": [vars(i) for i in res.issues],
            "passed": passed_count(res), "total_checks": len(res.checks),
        }
        with open(args.json_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)

    if args.email_summary:
        print(render_email_summary(res, args.site_name or res.url))
    else:
        print(render_text(res))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())