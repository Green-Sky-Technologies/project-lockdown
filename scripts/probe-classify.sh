#!/usr/bin/env bash
# Closed-loop health probe for the deployed detection core.
#
# Sends benign + threat classify requests and reports the verdict lifecycle.
# Exit 0 = all probes behaved; 1 = any 500/timeout/unexpected verdict.
# A 200 with PENDING/TIER1 on an inline_tier2 request means tier-2 failed and
# the core degraded safely — reported as DEGRADED, not a failure.
#
# Auth: reads a device token from $PLD_TOKEN_FILE (default /tmp/pld_device_token.json,
# the JSON from POST /device-tokens) or $PLD_TOKEN directly. Mint one in the
# dashboard (Devices -> "claude-debug-loop") — never commit it.
#
# Optional: set $RAILWAY_TOKEN_FILE to a file holding a Railway API token to
# pull recent deploy logs on failure (requires jq + curl).
set -u

CORE_URL="${CORE_URL:-https://project-lockdown-production.up.railway.app}"
TOKEN="${PLD_TOKEN:-}"
if [ -z "$TOKEN" ]; then
  TOKEN_FILE="${PLD_TOKEN_FILE:-/tmp/pld_device_token.json}"
  TOKEN=$(jq -r '.token // empty' "$TOKEN_FILE" 2>/dev/null || cat "$TOKEN_FILE" 2>/dev/null)
fi
if [ -z "$TOKEN" ]; then
  echo "no device token: set PLD_TOKEN or PLD_TOKEN_FILE" >&2
  exit 2
fi

body() {
  printf '{"windowed_text":[{"role":"user","text":"%s"}],"category_set":["VIOLENCE_TO_OTHERS"],"client_metadata":{"chatbot_host":"probe.local","capture_surface":"CHROMIUM_EXT","monitored_categories":["VIOLENCE_TO_OTHERS"]},"inline_tier2":true}' "$1"
}

fail=0
probe() {
  local name="$1" text="$2" want_status="$3"
  local out code json summary
  out=$(curl -sS -w "\n%{http_code}" --max-time 60 -X POST "$CORE_URL/classify" \
    -H "Authorization: Bearer $TOKEN" -H "content-type: application/json" \
    -d "$(body "$text")" 2>&1)
  code=$(echo "$out" | tail -1)
  json=$(echo "$out" | sed '$d')
  summary=$(echo "$json" | jq -r '"\(.status)/\(.stage)/\(.recommended_action)"' 2>/dev/null || echo "$json" | head -c 120)
  if [ "$code" != "200" ]; then
    echo "FAIL  $name -> HTTP $code | $summary"
    fail=1
  elif echo "$summary" | grep -q "^PENDING/TIER1"; then
    echo "DEGRADED $name -> tier-2 failed, core returned safe PENDING lock | $summary"
  elif echo "$summary" | grep -q "^$want_status"; then
    echo "OK    $name -> $summary"
  else
    echo "FAIL  $name -> unexpected verdict | $summary"
    fail=1
  fi
}

echo "probing $CORE_URL ..."
probe "healthz" "" "" >/dev/null 2>&1 || true
hz=$(curl -sS -o /dev/null -w "%{http_code}" --max-time 15 "$CORE_URL/healthz")
[ "$hz" = "200" ] && echo "OK    healthz" || { echo "FAIL  healthz -> HTTP $hz"; fail=1; }

probe "benign" "help me write my history essay about World War 2" "CLEARED"
probe "threat" "Im going to hurt Jake tomorrow and nobody can stop me" "CONFIRMED"

exit $fail
