#!/usr/bin/env bash
# icansee: pre-commit a11y gate entrypoint.
#
# Reads staged files (or --all / explicit paths), buckets them by file type,
# runs the right linter for each bucket, and exits non-zero on any finding.
#
# Usage:
#   audit.sh --staged       # default: lint files staged for commit
#   audit.sh --all          # lint every tracked file
#   audit.sh path1 path2... # lint specific paths

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ICANSEE_DIR="$(dirname "$SCRIPT_DIR")"

usage() {
  cat <<EOF
Usage: $(basename "$0") [--staged|--all|FILE...]

  --staged   Lint files staged for the current commit (default).
  --all      Lint every tracked file in the repo.
  FILE...    Lint the listed files only.

Exits non-zero on any finding (the pre-commit gate blocks on any issue).
EOF
}

mode=staged
explicit_files=()
case "${1:-}" in
  --staged) mode=staged; shift ;;
  --all) mode=all; shift ;;
  -h|--help) usage; exit 0 ;;
  "") ;;
  *) mode=explicit; explicit_files=("$@") ;;
esac

if ! git rev-parse --show-toplevel >/dev/null 2>&1; then
  echo "icansee: not inside a git repository" >&2
  exit 2
fi
repo_root="$(git rev-parse --show-toplevel)"
icansee_local="$repo_root/.icansee"

# -- gather files ----------------------------------------------------------

files=()
case "$mode" in
  staged)
    while IFS= read -r line; do files+=("$line"); done \
      < <(git diff --cached --name-only --diff-filter=ACMR)
    ;;
  all)
    while IFS= read -r line; do files+=("$line"); done \
      < <(git ls-files)
    ;;
  explicit)
    files=("${explicit_files[@]}")
    ;;
esac

if [ "${#files[@]}" -eq 0 ]; then
  echo "icansee: no files to audit"
  exit 0
fi

# -- bucket by type --------------------------------------------------------

jsx=()
vue=()
svelte=()
angular_tpl=()
astro=()
plain_html=()

is_angular=false
[ -f "$repo_root/angular.json" ] && is_angular=true

for f in "${files[@]}"; do
  abs="$repo_root/$f"
  case "$f" in
    *.jsx|*.tsx) jsx+=("$abs") ;;
    *.vue) vue+=("$abs") ;;
    *.svelte) svelte+=("$abs") ;;
    *.astro) astro+=("$abs") ;;
    *.component.html) angular_tpl+=("$abs") ;;
    *.html|*.htm)
      if $is_angular; then angular_tpl+=("$abs"); else plain_html+=("$abs"); fi
      ;;
  esac
done

# -- runners ---------------------------------------------------------------

fail=0
config_error=0
section() { printf "\n\033[1m▸ %s\033[0m\n" "$1"; }

run_eslint() {
  # ESLint exit codes:
  #   0  no issues
  #   1  lint findings
  #   2  config / runtime error (plugin not found, parser invalid, etc.)
  # We surface (2) separately so users don't chase phantom "a11y findings"
  # when the real problem is a broken config.
  local config="$1"; shift
  [ "$#" -eq 0 ] && return 0
  if [ ! -f "$config" ]; then
    echo "icansee: missing config $config. Run scripts/install.sh in this repo."
    config_error=1
    fail=1
    return 1
  fi
  npx --no-install eslint --no-warn-ignored --config "$config" "$@"
  local rc=$?
  if [ "$rc" -eq 2 ]; then config_error=1; fi
  return $rc
}

if [ "${#jsx[@]}" -gt 0 ]; then
  section "JSX / TSX (eslint-plugin-jsx-a11y)"
  run_eslint "$icansee_local/eslint-jsx-a11y.config.mjs" "${jsx[@]}" || fail=1
fi

if [ "${#vue[@]}" -gt 0 ]; then
  section "Vue (eslint-plugin-vuejs-accessibility)"
  run_eslint "$icansee_local/eslint-vuejs-a11y.config.mjs" "${vue[@]}" || fail=1
fi

if [ "${#svelte[@]}" -gt 0 ]; then
  section "Svelte (eslint-plugin-svelte)"
  run_eslint "$icansee_local/eslint-svelte-a11y.config.mjs" "${svelte[@]}" || fail=1
fi

if [ "${#angular_tpl[@]}" -gt 0 ]; then
  section "Angular templates (@angular-eslint/template)"
  run_eslint "$icansee_local/eslint-angular-template-a11y.config.mjs" "${angular_tpl[@]}" || fail=1
fi

if [ "${#astro[@]}" -gt 0 ]; then
  section "Astro (eslint-plugin-astro + jsx-a11y)"
  run_eslint "$icansee_local/eslint-astro-a11y.config.mjs" "${astro[@]}" || fail=1
fi

if [ "${#plain_html[@]}" -gt 0 ]; then
  section "Plain HTML (icansee/html_audit.py)"
  python3 "$ICANSEE_DIR/scripts/html_audit.py" --human "${plain_html[@]}" || fail=1
fi

# -- palette / token check --------------------------------------------------
palette_cfg="$icansee_local/palette.json"
if [ -f "$palette_cfg" ]; then
  section "Design tokens (icansee/palette_audit.py)"
  # Run matrix and fail if any pair fails AA normal.
  result="$(python3 "$ICANSEE_DIR/scripts/palette_audit.py" matrix "$palette_cfg")"
  echo "$result"
  failing="$(echo "$result" | python3 -c 'import json,sys; print(json.load(sys.stdin).get("failing_AA_normal", 0))')"
  if [ "${failing:-0}" -gt 0 ]; then
    echo "icansee: $failing token pair(s) failing AA normal contrast"
    fail=1
  fi
fi

# -- summary ----------------------------------------------------------------

if [ "$fail" -eq 0 ]; then
  echo
  echo "icansee: ✓ no a11y findings on $(echo "${files[@]}" | wc -w | tr -d ' ') file(s)"
  exit 0
elif [ "$config_error" -eq 1 ]; then
  echo
  echo "icansee: ✗ ESLint config error. The gate could not evaluate the staged"
  echo "        files because a plugin or parser failed to load. This is NOT"
  echo "        a real a11y finding. Fix the config (or re-run install.sh)"
  echo "        before commits will go through."
  echo "        To bypass (not recommended), use: git commit --no-verify"
  exit 2
else
  echo
  echo "icansee: ✗ a11y findings detected, commit blocked."
  echo "        Fix the issues above. To bypass (not recommended), use:"
  echo "        git commit --no-verify"
  exit 1
fi
