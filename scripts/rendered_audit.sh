#!/usr/bin/env bash
# icansee: rendered-DOM accessibility audit.
#
# Builds the project (if a build script exists), starts the app, runs
# @axe-core/cli against every route in .icansee/routes.json, then shuts the
# server down. Exits non-zero on any axe finding.
#
# This is the layer that catches what static source can't: computed contrast
# through the CSS cascade, landmark coverage of the rendered tree, focus
# state on default page load. Same engine as the CI workflow and Vercel's
# Accessibility Audit Tool.
#
# Used by the pre-push hook. Also runnable directly:
#   scripts/rendered_audit.sh
#
# Env overrides (set in shell or .icansee/env):
#   BUILD_CMD    Defaults to `npm run build` if package.json has a build
#                script. Set to empty string to skip the build step.
#   SERVE_CMD    Defaults to `npm start` if package.json has a start script,
#                else `npx --yes serve -s . -p 3000`.
#   BASE_URL     Defaults to http://localhost:3000.
#   WAIT_TIMEOUT Server-ready timeout in ms (default 60000).

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ICANSEE_DIR="$(dirname "$SCRIPT_DIR")"

if ! git rev-parse --show-toplevel >/dev/null 2>&1; then
  echo "icansee: not inside a git repository" >&2
  exit 2
fi
repo_root="$(git rev-parse --show-toplevel)"
cd "$repo_root"

# -- load .icansee/env if present (user overrides) --------------------------
[ -f .icansee/env ] && set -a && source .icansee/env && set +a

# -- detect build / serve commands ------------------------------------------

has_pkg_script() {
  [ -f package.json ] || return 1
  python3 - "$1" <<'PY' 2>/dev/null
import json, sys, pathlib
try:
    p = json.loads(pathlib.Path("package.json").read_text())
except Exception:
    sys.exit(1)
sys.exit(0 if sys.argv[1] in p.get("scripts", {}) else 1)
PY
}

if [ -z "${BUILD_CMD+x}" ]; then
  if has_pkg_script build; then BUILD_CMD="npm run build"; else BUILD_CMD=""; fi
fi

if [ -z "${SERVE_CMD+x}" ]; then
  if has_pkg_script start; then
    SERVE_CMD="npm start"
  elif has_pkg_script preview; then
    SERVE_CMD="npm run preview"
  else
    SERVE_CMD="npx --yes serve -s . -p 3000"
  fi
fi

BASE_URL="${BASE_URL:-http://localhost:3000}"
WAIT_TIMEOUT="${WAIT_TIMEOUT:-60000}"

# -- routes -----------------------------------------------------------------

routes_file=".icansee/routes.json"
if [ ! -f "$routes_file" ]; then
  echo "icansee: $routes_file missing. Defaulting to [\"/\"]"
  routes='/'
else
  routes="$(python3 -c 'import json,sys; print(" ".join(json.load(open(sys.argv[1]))))' "$routes_file")"
fi

# -- build ------------------------------------------------------------------

section() { printf "\n\033[1m▸ %s\033[0m\n" "$1"; }

if [ -n "$BUILD_CMD" ]; then
  section "Build: $BUILD_CMD"
  if ! eval "$BUILD_CMD"; then
    echo "icansee: build failed. Cannot run rendered audit" >&2
    exit 1
  fi
else
  echo "icansee: no build step (BUILD_CMD empty / no scripts.build)"
fi

# -- start app --------------------------------------------------------------

# -- pre-flight: check for a Chrome-class browser ---------------------------

# @axe-core/cli launches Chrome via chromedriver. If neither is reachable,
# the user gets a thousand-line Selenium stack trace. Pre-flight so we can
# print one helpful sentence instead.

CHROME_PATHS=(
  "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
  "/Applications/Chromium.app/Contents/MacOS/Chromium"
  "$(command -v google-chrome 2>/dev/null)"
  "$(command -v chromium 2>/dev/null)"
)
have_chrome=false
for p in "${CHROME_PATHS[@]}"; do
  [ -n "$p" ] && [ -x "$p" ] && have_chrome=true && break
done

if ! $have_chrome; then
  cat <<'EOF' >&2

icansee: rendered audit needs a Chrome-class browser (Chrome, Chromium).
        None found at the standard paths. Install one of:

          # macOS (recommended)
          brew install --cask google-chrome

          # Linux (Debian/Ubuntu)
          sudo apt-get install -y google-chrome-stable
          # or
          sudo apt-get install -y chromium-browser

        Then re-run the push (or this script directly).
EOF
  exit 2
fi

section "Serve: $SERVE_CMD"
# Run the server in its own process group so we can kill the whole tree.
# `setsid` isn't on macOS by default; fall back to plain background.
( $SERVE_CMD ) >/tmp/icansee-serve.log 2>&1 &
APP_PID=$!

cleanup() {
  if kill -0 "$APP_PID" 2>/dev/null; then
    # Kill the process group if we can; otherwise just the leader.
    kill -- "-$APP_PID" 2>/dev/null || kill "$APP_PID" 2>/dev/null
    wait "$APP_PID" 2>/dev/null
  fi
}
trap cleanup EXIT INT TERM

# Wait for the server to come up.
section "Wait for $BASE_URL (timeout ${WAIT_TIMEOUT}ms)"
if ! npx --yes wait-on "$BASE_URL" --timeout "$WAIT_TIMEOUT"; then
  echo "icansee: server didn't come up in ${WAIT_TIMEOUT}ms" >&2
  echo "--- last 30 lines of server log ---" >&2
  tail -n 30 /tmp/icansee-serve.log >&2 || true
  exit 1
fi

# -- run axe per route ------------------------------------------------------

fail=0
infra_error=0
AXE_LOG="$(mktemp -t icansee-axe.XXXXXX)"

for route in $routes; do
  url="${BASE_URL}${route}"
  section "axe-core: $url"
  # Capture combined output so we can detect ChromeDriver / version errors
  # that don't represent real a11y findings.
  if npx --yes @axe-core/cli "$url" \
        --tags wcag2a,wcag2aa,wcag21a,wcag21aa \
        --exit 2>&1 | tee -a "$AXE_LOG"; then
    :
  else
    fail=1
    if grep -qE "session not created|chromedriver|cannot find Chrome binary|Chrome instance exited|This version of ChromeDriver only supports Chrome version" "$AXE_LOG"; then
      infra_error=1
    fi
  fi
done

# -- summary ----------------------------------------------------------------

if [ "$fail" -eq 0 ]; then
  echo
  echo "icansee: ✓ rendered-DOM audit clean across all routes"
  rm -f "$AXE_LOG"
  exit 0
elif [ "$infra_error" -eq 1 ]; then
  echo
  echo "icansee: ✗ ChromeDriver / Chrome version mismatch or missing binary."
  echo "        This is NOT a real a11y finding. Sync the versions with:"
  echo
  echo "          npx browser-driver-manager install chrome"
  echo
  echo "        Or pass an explicit chromedriver path:"
  echo "          npx @axe-core/cli <url> --chromedriver-path /path/to/chromedriver"
  echo
  echo "        See docs/reference/install-and-ci.md for details."
  rm -f "$AXE_LOG"
  exit 2
else
  echo
  echo "icansee: ✗ rendered-DOM audit found issues, push blocked."
  echo "        Fix the issues above. To bypass (not recommended):"
  echo "        git push --no-verify"
  rm -f "$AXE_LOG"
  exit 1
fi
