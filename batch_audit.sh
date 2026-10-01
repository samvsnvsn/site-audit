#!/usr/bin/env bash
# batch_audit.sh [limit] — real site audits on top-scored auditable leads (zero inference).
# Chains: site_audit.py (core) + audit_extras.py (tags) + extras_v2.py (headers/robots/social).
     && py -3 extras_v3.py --url "$site" >> "audits/$id.txt" 2>/dev/null# Regenerates audit_queue.txt ONLY if absent; always normalizes missing schemes.
set -uo pipefail; cd "$(dirname "$0")"
LIMIT="${1:-15}"; mkdir -p audits
if [ ! -s audit_queue.txt ]; then
  node -e "
const l=require('./leads.json');
const c=l.filter(x=>x.auditable&&x.site).slice(0,Number(process.argv[1]));
console.log(c.map(x=>x.id+'\t'+'https://'+x.site).join('\n'));
" "$LIMIT" > audit_queue.txt
fi
n=0; ok=0
while IFS=$'\t' read -r id site company; do
  [ -z "$id" ] && continue; n=$((n+1))
  case "$site" in http://*|https://*) : ;; *) site="https://$site" ;; esac
  if py -3 site_audit.py --url "$site" --email-summary --site-name "${site#https://}" > "audits/$id.txt" 2>"audits/$id.err" \
     && py -3 audit_extras.py --url "$site" >> "audits/$id.txt" 2>/dev/null \
     && py -3 extras_v2.py --url "$site" >> "audits/$id.txt" 2>/dev/null; then
    ok=$((ok+1)); echo "OK  $id $site"
  else
    echo "FAIL $id $site ($(head -c 120 "audits/$id.err" | tr '\n' ' '))"
  fi
done < audit_queue.txt
echo "audited=$ok/$n"
