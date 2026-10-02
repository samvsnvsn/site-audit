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
#   5. allocate the next referral code from referral-codes.csv (first 5 leads
#      pre-logged as AUD-001..AUD-005), build the per-lead referral link
#      https://site-audit-landing.automaton-agent.workers.dev/?ref=<CODE>,
#      and inject it as {{REFERRAL_LINK}} into template 1 (email-templates.md)
#   6. honor unsubscribes in unsubscribe_list.txt
set -euo pipefail
cd "$(dirname "$0")"

LEADS="${1:-leads_sample.csv}"
LOG="outreach_log.csv"

if [ ! -f "$LEADS" ]; then
  echo "error: leads file $LEADS not found" >&2
  exit 1
fi

: > "$LOG.tmp"
echo "timestamp,email,site_url,status,lead_id,referral_code" >> "$LOG.tmp"

# Referral link format shared with email-templates.md Template 1 ({{REFERRAL_LINK}})
LANDING="https://site-audit-landing.automaton-agent.workers.dev"

# lookup_code <lead_id>: return the code pre-logged for this lead (crm:<id>) in
# referral-codes.csv. Codes exist ONLY for the first 5 CRM leads
# (AUD-001..AUD-005); this script allocates no new codes.
lookup_code() {
  awk -F, -v id="crm:$1" '$1==id {print $2; exit}' referral-codes.csv 2>/dev/null
}

tail -n +2 "$LEADS" | while IFS=, read -r email site_url first_name notes lead_id; do
  [ -z "$email" ] && continue
  # honor unsubscribes
  if [ -f unsubscribe_list.txt ] && grep -qxF "$email" unsubscribe_list.txt; then
    echo "$(date -Iseconds),$email,${site_url:-},skipped-unsubscribed" >> "$LOG.tmp"
    continue
  fi
  # 1) real audit -> 3-issue summary text
  summary=$(python3 site_audit.py --url "$site_url" --email-summary \
              --site-name "${site_url#https://}" 2>/dev/null || echo "audit failed")
  # 2) inject the lead's referral line into the email body (template 1 tail)
  referral_link=""
  if [ -n "$lead_id" ]; then
    code=$(lookup_code "$lead_id")
    if [ -n "$code" ]; then
      referral_link="${LANDING}/?ref=${code}"
    fi
  fi
  if [ -n "$referral_link" ]; then
    summary="${summary}

Know another site owner? Send them a free audit: ${referral_link}"
  fi
  # 3) send (hook must be provided by the operator harness; not in sandbox)
  if [ -n "${SEND_CMD:-}" ]; then
    printf '%s' "$summary" | eval "$SEND_CMD" \"$email\"
    echo "$(date -Iseconds),$email,${site_url:-},sent,${lead_id:-},${referral_link:-none}" >> "$LOG.tmp"
  else
    echo "$(date -Iseconds),$email,${site_url:-},prepared-no-send-hook,${lead_id:-},${referral_link:-none}" >> "$LOG.tmp"
  fi
done

mv "$LOG.tmp" "$LOG"
echo "done. log in $LOG"