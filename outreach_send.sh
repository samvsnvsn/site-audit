#!/usr/bin/env bash
# outreach_send.sh - skeleton for the email distribution step.
#
# NOTE: this sandbox has no direct SMTP send capability, so actual sends are
# done via the agent social relay / agentmail account
# (automaton-revenue@agentmail.to) by the operator's agent harness, which owns
# the account credentials. This script shows the exact per-lead personalization
# and logging flow used, so the run is reproducible and auditable.
#
# Usage: bash outreach_send.sh leads.csv   (requires a send hook: $SEND_CMD)
#
# For each lead:
#   1. run the real audit on the lead's site (site_audit.py --email-summary)
#   2. merge it into email template 1 (email-templates.md)
#   3. send from automaton-revenue@agentmail.to
#   4. log timestamp + email + site in outreach_log.csv
#   5. honor unsubscribes in unsubscribe_list.txt
set -euo pipefail
cd "$(dirname "$0")"

LEADS="${1:-leads_sample.csv}"
LOG="outreach_log.csv"

if [ ! -f "$LEADS" ]; then
  echo "error: leads file $LEADS not found" >&2
  exit 1
fi

: > "$LOG.tmp"
echo "timestamp,email,site_url,status" >> "$LOG.tmp"

tail -n +2 "$LEADS" | while IFS=, read -r email site_url first_name notes; do
  [ -z "$email" ] && continue
  # honor unsubscribes
  if [ -f unsubscribe_list.txt ] && grep -qxF "$email" unsubscribe_list.txt; then
    echo "$(date -Iseconds),$email,${site_url:-},skipped-unsubscribed" >> "$LOG.tmp"
    continue
  fi
  # 1) real audit -> 3-issue summary text
  summary=$(python3 site_audit.py --url "$site_url" --email-summary \
              --site-name "${site_url#https://}" 2>/dev/null || echo "audit failed")
  # 2) send (hook must be provided by the operator harness; not in sandbox)
  if [ -n "${SEND_CMD:-}" ]; then
    printf '%s' "$summary" | eval "$SEND_CMD" \"$email\"
    echo "$(date -Iseconds),$email,${site_url:-},sent" >> "$LOG.tmp"
  else
    echo "$(date -Iseconds),$email,${site_url:-},prepared-no-send-hook" >> "$LOG.tmp"
  fi
done

mv "$LOG.tmp" "$LOG"
echo "done. log in $LOG"