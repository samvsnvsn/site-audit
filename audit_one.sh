#!/usr/bin/env bash
# audit_one.sh URL [outdir] — single-URL deep audit for anyone. No leads.json required.
# Runs the full 4-module chain and produces audit.txt + report.html.
# Usage: bash audit_one.sh https://example.com audit-out
set -uo pipefail
URL="${1:?usage: bash audit_one.sh https://example.com [outdir]}"
OUT="${2:-audit-out}"
mkdir -p "$OUT"
case "$URL" in http://*|https://*) : ;; *) URL="https://$URL" ;; esac
host=$(py -3 -c "import urllib.parse,sys;print(urllib.parse.urlsplit(sys.argv[1]).netloc)" "$URL")
py -3 site_audit.py --url "$URL" --email-summary --site-name "$host" > "$OUT/audit.txt" 2>"$OUT/err.log" \
  || { echo "core audit failed:"; head -c 200 "$OUT/err.log"; exit 1; }
py -3 audit_extras.py --url "$URL" >> "$OUT/audit.txt" 2>/dev/null
py -3 extras_v2.py   --url "$URL" >> "$OUT/audit.txt" 2>/dev/null
py -3 extras_v3.py   --url "$URL" >> "$OUT/audit.txt" 2>/dev/null
py -3 make_html_report.py --out "$OUT/report.html" "$OUT/audit.txt"
echo "DONE -> $OUT/report.html"
