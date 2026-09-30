#!/usr/bin/env bash
# run_pipeline.sh — one-command outreach pipeline (zero inference).
# Usage: run_pipeline.sh [CRM_PATH] [AUDIT_LIMIT]
set -uo pipefail; cd "$(dirname "$0")"
CRM_PATH="${1:-/c/Users/samvs/jev-work/automaton-r2/.automaton-r3/crm.json}"
LIMIT="${2:-15}"
echo "[1/4] extract leads from $CRM_PATH"
node extract_leads.mjs "$CRM_PATH" || exit 1
echo "[2/4] site audits (limit $LIMIT)"
rm -f audit_queue.txt
bash batch_audit.sh "$LIMIT" || true
echo "[3/4] generate personalized emails"
node gen_emails.mjs || exit 1
echo "[4/4] verify"
bash verify.sh
