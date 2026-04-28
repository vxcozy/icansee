#!/usr/bin/env bash
# Smoke tests for scripts/install.sh framework detection.
#
# Each case: build a temp git repo with a fake project shape, run
# `install.sh --print-detection`, and assert the detected frameworks
# list. Counts pass/fail and exits non-zero on any failure.

set -u

ICANSEE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
INSTALL="$ICANSEE_DIR/scripts/install.sh"

pass=0
fail=0
fails=()

# Bash version (kept around for any future os-specific gating; not currently
# used because install.sh now uses `find` for filesystem hints, which works on
# macOS bash 3.2 too).
bash_major="${BASH_VERSION%%.*}"

run_case() {
  # run_case <description> <expected-frameworks> <setup-shell-snippet>
  local desc="$1" expected="$2" setup="$3"
  local tmp
  tmp="$(mktemp -d)"
  (
    cd "$tmp" || exit 1
    git init -q
    eval "$setup"
    bash "$INSTALL" --print-detection 2>&1
  ) > "$tmp/.out" 2>&1
  local out
  out="$(cat "$tmp/.out")"
  rm -rf "$tmp"

  # Expected line: "icansee: detected frameworks: <expected>"
  local got
  got="$(printf '%s\n' "$out" | sed -n 's/^icansee: detected frameworks: //p')"
  if [ "$got" = "$expected" ]; then
    pass=$((pass + 1))
    printf '  PASS  %s -> %s\n' "$desc" "$got"
  else
    fail=$((fail + 1))
    fails+=("$desc: expected [$expected], got [$got]")
    printf '  FAIL  %s\n        expected: [%s]\n        got:      [%s]\n' \
      "$desc" "$expected" "$got"
    printf '        full output:\n%s\n' "$out" | sed 's/^/          /'
  fi
}

skip_case() {
  local desc="$1" reason="$2"
  printf '  SKIP  %s: %s\n' "$desc" "$reason"
}

echo "install.sh detection cases:"

run_case "empty repo" "html-only" ":"

run_case "package.json with react" "jsx" \
  "echo '{\"dependencies\": {\"react\": \"^18.0.0\"}}' > package.json"

run_case "package.json with vue" "vue" \
  "echo '{\"dependencies\": {\"vue\": \"^3.0.0\"}}' > package.json"

run_case "package.json with svelte" "svelte" \
  "echo '{\"devDependencies\": {\"svelte\": \"^4.0.0\"}}' > package.json"

run_case "angular.json present" "angular" \
  "echo '{}' > angular.json"

run_case "package.json with astro" "astro" \
  "echo '{\"dependencies\": {\"astro\": \"^4.0.0\"}}' > package.json"

run_case "react + svelte (mixed deps)" "jsx svelte" \
  "echo '{\"dependencies\": {\"react\": \"^18\", \"svelte\": \"^4\"}}' > package.json"

# install.sh now uses `find` for filesystem hints, so this test runs on
# any bash version (including macOS's stock 3.2).
run_case "filesystem hint: app.tsx, no package.json" "jsx" \
  "touch app.tsx"
run_case "filesystem hint: nested app.tsx in src/, no package.json" "jsx" \
  "mkdir -p src && touch src/app.tsx"
run_case "filesystem hint: deeply nested .vue, no package.json" "vue" \
  "mkdir -p src/components/widgets && touch src/components/widgets/X.vue"

printf '\n%d passed, %d failed\n' "$pass" "$fail"
if [ "$fail" -gt 0 ]; then
  printf '\nFailures:\n'
  for f in "${fails[@]}"; do
    printf '  - %s\n' "$f"
  done
  exit 1
fi
exit 0
