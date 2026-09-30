#!/usr/bin/env bash
# verify.sh — quality gate for the outreach pipeline.
# PASS requires: lead/audit/email counts consistent, extras v1+v2 in EVERY audit,
# extras test suite green, HTML report buildable from a PII-free sample.
set -uo pipefail; cd "$(dirname "$0")"
fail(){ echo "VERIFY-FAIL: $1"; exit 1; }
L=$(node -e "console.log(require('./leads.json').length)" 2>/dev/null) || fail "leads.json missing/unreadable"
[ "$L" -gt 0 ] || fail "zero leads"
A=$(ls audits/*.txt 2>/dev/null | wc -l)
E=$(ls emails/*.md 2>/dev/null | wc -l)
echo "leads:$L audits:$A emails:$E"
[ "$A" -gt 0 ] || fail "no audits"
[ "$E" -eq "$A" ] || fail "email/audit count mismatch"
# extras must be present in EVERY audit (deep-audit guarantee)
v1=$(grep -l "EXTENDED CHECKS" audits/*.txt 2>/dev/null | wc -l)
v2=$(grep -l "EXTRA CHECKS (headers/robots/social)" audits/*.txt 2>/dev/null | wc -l)
echo "extras v1:$v1/$A v2:$v2/$A"
[ "$v1" -eq "$A" ] || fail "extras v1 missing from some audits"
[ "$v2" -eq "$A" ] || fail "extras v2 missing from some audits"
# test suite (extras regression, offline fixture server)
py -3 -m unittest test_extras 2>&1 | grep -q "^OK" || fail "test_extras suite failed"
# HTML report buildable (PII-free sample path)
py -3 site_audit.py --url https://example.com --email-summary --site-name example.com > /tmp/v-audit.txt 2>/dev/null
py -3 audit_extras.py --url https://example.com >> /tmp/v-audit.txt 2>/dev/null
py -3 extras_v2.py --url https://example.com >> /tmp/v-audit.txt 2>/dev/null
py -3 make_html_report.py --out /tmp/v-report.html /tmp/v-audit.txt > /dev/null 2>&1 || fail "HTML report generation failed"
grep -q "Site Audit Report" /tmp/v-report.html || fail "HTML report content check failed"
echo "VERIFY-OK"
