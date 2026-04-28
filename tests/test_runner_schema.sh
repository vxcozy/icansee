#!/usr/bin/env bash
# Smoke tests for templates/parse-routes.mjs's routes.json schema parser.
#
# Runs the parser CLI against a series of routes.json fixtures and
# asserts the resolved {routes, modes} JSON.
#
# parse-routes.mjs is a standalone module with no external deps, so the
# schema test does not need playwright installed. node and python3 are
# hard requirements (the parser is JS, the test compares JSON via a
# Python canonicalize step). If either is missing, the test fails
# loudly rather than skipping silently, since both are required for
# icansee itself to function.

set -u

ICANSEE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PARSER="$ICANSEE_DIR/templates/parse-routes.mjs"

if ! command -v node >/dev/null 2>&1; then
  echo "axe-runner schema cases:"
  echo "  FAIL  node is not on PATH (required to run parse-routes.mjs)" >&2
  exit 1
fi
if ! command -v python3 >/dev/null 2>&1; then
  echo "axe-runner schema cases:"
  echo "  FAIL  python3 is not on PATH (required for canonical JSON compare)" >&2
  exit 1
fi

pass=0
fail=0
fails=()

# Compare two JSON strings structurally, not by raw bytes. JSON.stringify
# happens to be key-order stable, but we don't want the test to depend on
# that. Both sides are normalized through python3's json with sort_keys.
canonicalize_json() {
  python3 -c 'import json,sys; print(json.dumps(json.loads(sys.stdin.read()), sort_keys=True, separators=(",",":")))'
}

run_case() {
  # run_case <description> <routes.json contents> <expected JSON>
  local desc="$1" contents="$2" expected="$3"
  local tmp
  tmp="$(mktemp -d)"
  mkdir -p "$tmp/.icansee"
  printf '%s' "$contents" > "$tmp/.icansee/routes.json"
  local got
  got="$(cd "$tmp" && node "$PARSER" .icansee/routes.json 2>&1)"
  local rc=$?
  rm -rf "$tmp"

  if [ "$rc" -ne 0 ]; then
    fail=$((fail + 1))
    fails+=("$desc: runner exited $rc with output: $got")
    printf '  FAIL  %s (exit %d)\n        %s\n' "$desc" "$rc" "$got"
    return
  fi

  local got_canon expected_canon
  got_canon="$(printf '%s' "$got" | canonicalize_json 2>/dev/null)"
  expected_canon="$(printf '%s' "$expected" | canonicalize_json 2>/dev/null)"
  if [ -z "$got_canon" ] || [ -z "$expected_canon" ]; then
    fail=$((fail + 1))
    fails+=("$desc: canonicalize failed; got=[$got] expected=[$expected]")
    printf '  FAIL  %s (canonicalize failed)\n' "$desc"
    return
  fi

  if [ "$got_canon" = "$expected_canon" ]; then
    pass=$((pass + 1))
    printf '  PASS  %s -> %s\n' "$desc" "$got_canon"
  else
    fail=$((fail + 1))
    fails+=("$desc: expected $expected_canon, got $got_canon")
    printf '  FAIL  %s\n        expected: %s\n        got:      %s\n' \
      "$desc" "$expected_canon" "$got_canon"
  fi
}

run_invalid_case() {
  # run_invalid_case <description> <routes.json contents>
  # Expects the runner to exit 2 (config error) and never print parse-only JSON.
  local desc="$1" contents="$2"
  local tmp
  tmp="$(mktemp -d)"
  mkdir -p "$tmp/.icansee"
  printf '%s' "$contents" > "$tmp/.icansee/routes.json"
  local out rc
  out="$(cd "$tmp" && node "$PARSER" .icansee/routes.json 2>&1)"
  rc=$?
  rm -rf "$tmp"

  if [ "$rc" -eq 2 ]; then
    pass=$((pass + 1))
    printf '  PASS  %s -> rejected (exit 2)\n' "$desc"
  else
    fail=$((fail + 1))
    fails+=("$desc: expected exit 2, got $rc; output: $out")
    printf '  FAIL  %s (expected rejection, got exit %d)\n' "$desc" "$rc"
  fi
}

echo "axe-runner schema cases:"

run_case "legacy array form, single route" \
  '["/"]' \
  '{"routes":["/"],"modes":["light"]}'

run_case "legacy array form, multiple routes" \
  '["/", "/dashboard", "/settings"]' \
  '{"routes":["/","/dashboard","/settings"],"modes":["light"]}'

run_case "object form with explicit light+dark" \
  '{"routes": ["/"], "modes": ["light", "dark"]}' \
  '{"routes":["/"],"modes":["light","dark"]}'

run_case "object form with dark only" \
  '{"routes": ["/", "/x"], "modes": ["dark"]}' \
  '{"routes":["/","/x"],"modes":["dark"]}'

run_case "object form, modes omitted, defaults to light" \
  '{"routes": ["/", "/x"]}' \
  '{"routes":["/","/x"],"modes":["light"]}'

run_case "object form, empty modes array, defaults to light" \
  '{"routes": ["/"], "modes": []}' \
  '{"routes":["/"],"modes":["light"]}'

run_invalid_case "object form with invalid mode" \
  '{"routes": ["/"], "modes": ["light", "sepia"]}'

run_invalid_case "non-string route" \
  '[1, 2, 3]'

run_invalid_case "route missing leading slash" \
  '["dashboard"]'

run_invalid_case "route missing leading slash, object form" \
  '{"routes": ["/", "settings"], "modes": ["light"]}'

run_invalid_case "malformed JSON" \
  '{not json'

# routes.json absent (no fixture written) -> defaults to ["/"], ["light"].
no_routes_tmp="$(mktemp -d)"
got="$(cd "$no_routes_tmp" && node "$PARSER" .icansee/routes.json 2>&1)"
rc=$?
rm -rf "$no_routes_tmp"
expected_canon="$(printf '%s' '{"routes":["/"],"modes":["light"]}' | canonicalize_json)"
got_canon="$(printf '%s' "$got" | canonicalize_json 2>/dev/null)"
if [ "$rc" -eq 0 ] && [ "$got_canon" = "$expected_canon" ]; then
  pass=$((pass + 1))
  printf '  PASS  routes.json absent -> %s\n' "$got_canon"
else
  fail=$((fail + 1))
  fails+=("routes.json absent: expected $expected_canon (exit 0), got $got_canon (exit $rc)")
  printf '  FAIL  routes.json absent (exit %d)\n        expected: %s\n        got:      %s\n' \
    "$rc" "$expected_canon" "$got_canon"
fi

printf '\n%d passed, %d failed\n' "$pass" "$fail"
if [ "$fail" -gt 0 ]; then
  printf '\nFailures:\n'
  for f in "${fails[@]}"; do
    printf '  - %s\n' "$f"
  done
  exit 1
fi
exit 0
