#!/usr/bin/env bash
# icansee: rendered-DOM accessibility audit.
#
# Builds the project (if a build script exists), starts the app, runs the
# Playwright + @axe-core/playwright runner against every route in
# .icansee/routes.json across every configured color mode (light / dark),
# then shuts the server down. Exits non-zero on any axe finding.
#
# This is the layer that catches what static source can't: computed contrast
# through the CSS cascade, landmark coverage of the rendered tree, focus
# state on default page load, and (in v0.3+) dark-mode contrast via
# `prefers-color-scheme` emulation.
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

# -- pre-flight: check the runner is installed ------------------------------

RUNNER=".icansee/axe-runner.mjs"
if [ ! -f "$RUNNER" ]; then
  cat <<EOF >&2

icansee: missing $RUNNER. Re-run the installer:

          bash $ICANSEE_DIR/scripts/install.sh

EOF
  exit 2
fi

section() { printf "\n\033[1m▸ %s\033[0m\n" "$1"; }

# -- build ------------------------------------------------------------------

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

section "Serve: $SERVE_CMD"
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

# -- run the audit ----------------------------------------------------------

BASE_URL="$BASE_URL" node "$RUNNER"
status=$?

if [ "$status" -eq 0 ]; then
  exit 0
elif [ "$status" -eq 1 ]; then
  exit 1
else
  echo "icansee: ✗ rendered audit hit an infra error (see above)" >&2
  exit 2
fi
