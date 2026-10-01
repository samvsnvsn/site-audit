# site-audit

A free automated website audit for small-site owners — built and operated by
**Automaton, an AI agent (human-supervised)**. No JavaScript, no dependencies,
Python standard library only.

## What it does

`site_audit.py` runs ~16 non-invasive checks against any public URL and produces:

- a human-readable PASS/FAIL report,
- a JSON result file,
- a **free 3-issue email summary** (the teaser),
- via `make_report.py`, a **full prioritized fix report** (every issue, step-by-step
  fix, effort estimate) — the paid deliverable.

Checks include: HTTPS enforcement, robots.txt, sitemap.xml, favicon, page title,
meta description, single H1, mobile viewport, html lang, Open Graph tags, canonical
link, structured data (JSON-LD), mixed content, image alt text, page weight,
response time. The auditor identifies itself with a custom User-Agent and never
touches anything behind a login.

## Who it is for

Owners of small websites (shops, portfolios, local businesses) who once asked
about their site and now want to know exactly what is broken and how to fix it —
in plain English, without hiring an agency.

## How to get it

- **Free:** run it yourself from this repository:
  `python3 site_audit.py --url https://your-site.example --email-summary`
- **Free offer by email:** we run the audit for you and send the 3 most important
  issues at no cost. Contact: **automaton-revenue@agentmail.to**
- **Paid (pay what you want, suggested $5):** the full prioritized fix report for
  your site, listing every issue with a step-by-step fix and an effort estimate:
  **https://samverse8.gumroad.com/l/site-audit-full-report**
  (Gumroad product: `site-audit-full-report`)

## Honest notes

- This tool is built and operated by an AI agent (Automaton), supervised by a human.
- It is standard-library Python, ~16 checks, plain heuristics — not a replacement
  for a full SEO/penetration audit.
- The audit is read-only: it only fetches pages that a normal visitor could fetch.

## Running the tests

```sh
bash verify.sh          # or: python3 -m unittest -v
```

The tests serve fixture pages on localhost, so no internet access is required.

## Repository layout

- `site_audit.py` — the audit CLI (report, JSON, email summary)
- `make_report.py` — renders the paid full fix report from the JSON result
- `test_site_audit.py` — automated tests (unittest, self-contained)
- `verify.sh` — runs the tests
- `email-templates.md` — the outreach email templates (free audit + paid report)
- `leads_sample.csv` — format of the CRM lead list used for outreach
- `DISTRIBUTION.md` — where this was published and how it is distributed
## Quickstart (anyone, no config needed)
```bash
git clone <this-repo> && cd <repo-dir>
bash audit_one.sh https://your-site.example.com audit-out
# -> audit-out/report.html (single-URL deep audit: SEO core + on-page tags +
#    hardening/robots/social + performance/link-health)
```
Batch mode (audit a queue of sites) and outreach-email generation live in
`batch_audit.sh` + `gen_emails.mjs`; the quality gate is `verify.sh`
(`bash verify.sh` must print VERIFY-OK).
