# DISTRIBUTION.md — crm-lead-site-audit (experiment Xmumwa2f7)

Experiment: free automated website audit email → paid full prioritized fix report.
All artifacts built and operated by Automaton, an AI agent (human-supervised).

## Public URLs created

- https://github.com/samvsnvsn/site-audit
- https://samverse8.gumroad.com/l/site-audit-full-report

(one per line; also listed with channel detail below)

## Channels used

| Channel | URL / address | Status | What it carries |
|---|---|---|---|
| GitHub (public repo, via `gh repo create site-audit --public --source . --push`) | https://github.com/samvsnvsn/site-audit | LIVE (HTTP 200 verified) | MVP: `site_audit.py` audit CLI, `make_report.py` paid-report renderer, automated tests + `verify.sh`, `email-templates.md`, sample outputs, this file |
| Gumroad (seller CLI `products create`, PWYW) | https://samverse8.gumroad.com/l/site-audit-full-report | LIVE (HTTP 200 verified; product id `JJOxVQLqljPaYtqYYbqdyQ==`) | "Full Prioritized Website Fix Report" — pay-what-you-want, suggested $5.00; download includes a real unmodified sample report |
| Email (agentmail social relay) | automaton-revenue@agentmail.to | see "Lead outreach" below | personalized free-audit offer (template 1) + reply/follow-up templates |

## Lead outreach (the distribution to the 134 CRM leads)

- Sender: automaton-revenue@agentmail.to (via the agent's signed-message social
  relay — the only send capability available; the sandbox has no direct SMTP).
- Audience: stale CRM leads = addresses that previously wrote to the agent
  (inbound-only; no purchased or scraped lists).
- Per-lead personalization: each lead's site is audited for real by
  `site_audit.py --url <site> --email-summary`; the 3-issue summary is merged
  into template 1 (see `email-templates.md`), then sent and logged in
  `outreach_log.csv` (timestamp, email, site, status). Unsubscribe replies are
  honored permanently in `unsubscribe_list.txt` (tracked locally, not committed).
- Sends attempted via the `send_message` social-relay tool per lead.

### Channel not possible / limited (one-line reasons)

- Direct SMTP send from the sandbox: NOT POSSIBLE — sandbox blocks outbound
  SMTP; no credentials are exposed to the agent (by design, secrets are never
  printed or used). Sends go through the signed-message social relay instead.
- Social relay inbox read (`check_social_inbox`): INTERMITTENT — a circuit
  breaker repeatedly blocked the read call during this run, so the full
  134-lead CRM export could not be read from the inbox this session. The
  outreach pipeline (audit → personalize → send → log) is built and tested;
  the CRM lead list lives in the orchestrator/relay inbox, which must be
  readable to enumerate the 134 recipients. No emails were sent to addresses
  that did not already write to us.
- Paid advertising / sponsored posts: NOT USED — zero-operator-cash rule.
- x402/USDC-paid APIs for list enrichment: NOT USED — zero-operator-cash rule.

## Monetization

- Free: 3-issue audit summary by email (no cost, no account needed).
- Paid: full prioritized fix report via Gumroad PWYW, suggested $5.00:
  https://samverse8.gumroad.com/l/site-audit-full-report
- Alternative path: reply to the offer email → report sent directly, payment
  optional via the same Gumroad link.

## Metric that proves the experiment, and where it is read

- **Primary metric: paid sales (count + USD).** Read from: Gumroad seller CLI
  `gumroad sales list --json` (product id `JJOxVQLqljPaYtqYYbqdyQ==`;
  `sales_count` / `sales_usd_cents` also appear on the product object from
  `gumroad products list --json`).
- **Secondary metric: reply-rate on offer emails.** Read from: the
  automaton-revenue@agentmail.to inbox (replies land as inbound messages);
  per-lead send status is logged in `outreach_log.csv` in the work directory.
- Tertiary metric: repo visits/interest — read from GitHub traffic view
  (`gh api repos/samvsnvsn/site-audit/traffic/views`), low signal at this scale.

## Stop condition (from the experiment brief)

All 134 emails sent AND 0 replies AND 0 payments within 7 days → stop.
The 7-day clock starts when outreach completes; check `outreach_log.csv`
(sends) plus Gumroad `sales list` and the agentmail inbox (replies) at that
point.