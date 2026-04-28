#!/usr/bin/env bash
# icansee: install the pre-commit a11y gate (and optional CI workflow)
# into the current git repository.
#
# Detects the project's framework(s) from package.json + filesystem hints,
# installs the right ESLint plugin(s) as devDependencies, drops flat-config
# files into .icansee/, wires up the pre-commit hook (husky if present, plain
# git hook otherwise), and copies the GitHub Actions workflow for full
# axe-core CI.
#
# Idempotent. Safe to re-run after framework changes.
#
# Usage:
#   install.sh                     # full install: pre-commit + pre-push + CI
#   install.sh --no-ci             # skip the GH workflow
#   install.sh --no-hook           # skip the pre-commit hook
#   install.sh --no-pre-push       # skip the pre-push (rendered-DOM) hook
#   install.sh --print-detection   # detect only, print, exit

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ICANSEE_DIR="$(dirname "$SCRIPT_DIR")"

want_hook=true
want_pre_push=true
want_ci=true
print_only=false
for arg in "$@"; do
  case "$arg" in
    --no-hook) want_hook=false ;;
    --no-pre-push) want_pre_push=false ;;
    --no-ci) want_ci=false ;;
    --print-detection) print_only=true ;;
    -h|--help)
      sed -n '2,/^$/p' "$0" | sed 's/^# \?//'
      exit 0
      ;;
    *) echo "icansee: unknown arg $arg" >&2; exit 2 ;;
  esac
done

if ! git rev-parse --show-toplevel >/dev/null 2>&1; then
  echo "icansee: not inside a git repository" >&2
  exit 2
fi
repo_root="$(git rev-parse --show-toplevel)"
cd "$repo_root"

# -- detection --------------------------------------------------------------

frameworks=()
detect_dep() {
  local dep="$1"
  [ -f package.json ] || return 1
  python3 - "$dep" <<'PY'
import json, sys, pathlib
dep = sys.argv[1]
try:
    p = json.loads(pathlib.Path("package.json").read_text())
except Exception:
    sys.exit(1)
deps = {**p.get("dependencies", {}), **p.get("devDependencies", {}),
        **p.get("peerDependencies", {})}
sys.exit(0 if dep in deps else 1)
PY
}

has_files() {
  # has_files <ext1> [ext2 ...]
  # Recursively searches the repo for files matching any of the given
  # extensions. Uses `find` rather than bash globs because macOS ships
  # bash 3.2 (no globstar), and `compgen -G '**/*.tsx'` does not recurse
  # there.
  local exts=()
  for e in "$@"; do exts+=(-name "*.$e" -o); done
  unset 'exts[${#exts[@]}-1]'  # drop trailing -o
  find . -type f \( "${exts[@]}" \) -not -path '*/node_modules/*' \
    -not -path '*/.git/*' -print -quit 2>/dev/null | grep -q .
}

if detect_dep react || detect_dep next || detect_dep preact \
   || detect_dep solid-js || has_files tsx jsx; then
  frameworks+=("jsx")
fi
if detect_dep vue || detect_dep nuxt || has_files vue; then
  frameworks+=("vue")
fi
if detect_dep svelte || detect_dep '@sveltejs/kit' || has_files svelte; then
  frameworks+=("svelte")
fi
if detect_dep '@angular/core' || [ -f angular.json ]; then
  frameworks+=("angular")
fi
if detect_dep astro || has_files astro; then
  frameworks+=("astro")
fi
# Plain HTML support is implicit; html_audit.py runs without npm deps.

if [ "${#frameworks[@]}" -eq 0 ]; then
  frameworks+=("html-only")
fi

echo "icansee: detected frameworks: ${frameworks[*]}"
$print_only && exit 0

# -- package manager --------------------------------------------------------

pm=""
if [ -f pnpm-lock.yaml ]; then pm=pnpm
elif [ -f yarn.lock ]; then pm=yarn
elif [ -f bun.lockb ] || [ -f bun.lock ]; then pm=bun
elif [ -f package-lock.json ]; then pm=npm
elif [ -f package.json ]; then pm=npm
fi

install_dev() {
  [ -z "$pm" ] && return 0
  case "$pm" in
    npm) npm install --save-dev --no-audit --no-fund "$@" ;;
    pnpm) pnpm add --save-dev "$@" ;;
    yarn) yarn add --dev "$@" ;;
    bun) bun add --dev "$@" ;;
  esac
}

# -- copy configs and install plugins per framework -------------------------

mkdir -p .icansee
plugin_pkgs=()
for fw in "${frameworks[@]}"; do
  case "$fw" in
    jsx)
      cp "$ICANSEE_DIR/templates/eslint/jsx-a11y.config.mjs" .icansee/eslint-jsx-a11y.config.mjs
      plugin_pkgs+=(eslint-plugin-jsx-a11y @typescript-eslint/parser)
      ;;
    vue)
      cp "$ICANSEE_DIR/templates/eslint/vuejs-a11y.config.mjs" .icansee/eslint-vuejs-a11y.config.mjs
      plugin_pkgs+=(eslint-plugin-vuejs-accessibility vue-eslint-parser @typescript-eslint/parser)
      ;;
    svelte)
      cp "$ICANSEE_DIR/templates/eslint/svelte-a11y.config.mjs" .icansee/eslint-svelte-a11y.config.mjs
      plugin_pkgs+=(eslint-plugin-svelte svelte-eslint-parser @typescript-eslint/parser)
      ;;
    angular)
      cp "$ICANSEE_DIR/templates/eslint/angular-template-a11y.config.mjs" .icansee/eslint-angular-template-a11y.config.mjs
      plugin_pkgs+=('@angular-eslint/eslint-plugin-template' '@angular-eslint/template-parser')
      ;;
    astro)
      cp "$ICANSEE_DIR/templates/eslint/astro-a11y.config.mjs" .icansee/eslint-astro-a11y.config.mjs
      plugin_pkgs+=(eslint-plugin-astro eslint-plugin-jsx-a11y)
      ;;
    html-only)
      ;;
  esac
done

# Always need eslint itself if we're installing any plugin.
if [ "${#plugin_pkgs[@]}" -gt 0 ]; then
  if ! detect_dep eslint; then plugin_pkgs+=(eslint); fi
  echo "icansee: installing dev deps: ${plugin_pkgs[*]} (via $pm)"
  install_dev "${plugin_pkgs[@]}" || {
    echo "icansee: dependency install failed; ESLint checks won't run." >&2
  }
fi

# -- rendered-DOM audit deps (Playwright + axe) ----------------------------
#
# The pre-push and CI layers run .icansee/axe-runner.mjs, which imports
# `playwright` and `@axe-core/playwright`. To keep the gate self-contained
# (and to support plain-HTML projects with no package.json), we install
# the runner's deps INTO .icansee/, not the user's project root. Node's
# module resolver finds .icansee/node_modules naturally because the
# runner lives in the same directory. Playwright bundles a signed
# Chromium into ~/.cache/ms-playwright (shared across projects), so the
# per-project disk cost here is just ~5MB of JS.

if $want_pre_push || $want_ci; then
  cp "$ICANSEE_DIR/templates/axe-runner.mjs" .icansee/axe-runner.mjs
  cp "$ICANSEE_DIR/templates/parse-routes.mjs" .icansee/parse-routes.mjs
  chmod +x .icansee/axe-runner.mjs

  # Exact pins so every install.sh run resolves to the same versions
  # regardless of when it runs. Bump these in lockstep with icansee
  # releases and re-verify the smoke test before tagging.
  cat > .icansee/package.json <<'JSON'
{
  "name": "icansee-runner",
  "private": true,
  "type": "module",
  "description": "Self-contained deps for .icansee/axe-runner.mjs. Managed by icansee install.sh; do not hand-edit.",
  "dependencies": {
    "playwright": "1.59.1",
    "@axe-core/playwright": "4.11.2"
  }
}
JSON

  if ! command -v npm >/dev/null 2>&1; then
    echo "icansee: ✗ npm is not on PATH. The rendered audit needs npm to install" >&2
    echo "        playwright + @axe-core/playwright into .icansee/. Install Node," >&2
    echo "        then re-run this script." >&2
    exit 1
  fi

  # Capture install output so the user sees exactly why a failure happened
  # instead of a vague "rendered audit will fail" line.
  log="$(mktemp -t icansee-install.XXXXXX)"
  trap 'rm -f "$log"' EXIT

  echo "icansee: installing rendered-audit deps into .icansee/ (playwright, @axe-core/playwright)"
  if ! npm install --prefix .icansee --no-audit --no-fund >"$log" 2>&1; then
    echo "icansee: ✗ 'npm install --prefix .icansee' failed. Output below:" >&2
    echo "------------------------------------------------------------" >&2
    cat "$log" >&2
    echo "------------------------------------------------------------" >&2
    echo "icansee: rendered audit cannot run until this is resolved." >&2
    exit 1
  fi

  # Pull the chromium binary into Playwright's shared cache. Idempotent
  # and fast on subsequent runs.
  echo "icansee: ensuring Playwright chromium is installed"
  if ! (cd .icansee && npx --yes playwright install chromium >"$log" 2>&1); then
    echo "icansee: ✗ 'npx playwright install chromium' failed. Output below:" >&2
    echo "------------------------------------------------------------" >&2
    cat "$log" >&2
    echo "------------------------------------------------------------" >&2
    echo "icansee: rendered audit cannot run until this is resolved." >&2
    exit 1
  fi

  echo "icansee: rendered-audit runner installed at .icansee/axe-runner.mjs"
fi

# -- git hooks (pre-commit + pre-push) -------------------------------------

install_hook() {
  # install_hook <hook-name> <template>
  local name="$1" template="$2"
  local target=""
  if [ -d .husky ] && detect_dep husky; then
    target=".husky/$name"
    mkdir -p .husky
  else
    target="$(git rev-parse --git-path hooks)/$name"
    mkdir -p "$(dirname "$target")"
  fi
  sed "s|__ICANSEE_DIR__|$ICANSEE_DIR|g" "$template" > "$target"
  chmod +x "$target"
  echo "icansee: $name hook installed at $target"
}

if $want_hook; then
  install_hook pre-commit "$ICANSEE_DIR/templates/pre-commit"
fi

if $want_pre_push; then
  install_hook pre-push "$ICANSEE_DIR/templates/pre-push"
fi

# -- CI workflow ------------------------------------------------------------

if $want_ci; then
  mkdir -p .github/workflows
  cp "$ICANSEE_DIR/templates/github-workflow-a11y.yml" .github/workflows/a11y.yml
  if [ ! -f .icansee/routes.json ]; then
    cp "$ICANSEE_DIR/templates/routes.json" .icansee/routes.json
    echo "icansee: created .icansee/routes.json. Extend it with the routes to scan"
  fi
  echo "icansee: CI workflow installed at .github/workflows/a11y.yml"
  echo "        (translate to your CI provider if not on GitHub Actions;"
  echo "         see docs/reference/install-and-ci.md)"
fi

cat <<EOF

icansee install complete.
  Pre-commit:  blocks commits with any static a11y issue (~1–3s).
  Pre-push:    runs Playwright + axe-core against the built+served site,
               sweeping configured color modes (~30–90s).
  CI workflow: same rendered-DOM check, enforced at PR boundary.

Customize:
  .icansee/routes.json   routes (and color modes) the rendered audit scans.
                         Legacy: ["/", "/dashboard"]
                         v0.3+:  {"routes": ["/"], "modes": ["light", "dark"]}
  .icansee/env           set BUILD_CMD / SERVE_CMD / BASE_URL overrides

Try it:
  echo '<img src="x.png">' >> staged-test.html
  git add staged-test.html
  git commit -m "trigger gate"   # should fail with image-alt finding

To bypass (not recommended):
  git commit --no-verify
  git push --no-verify
EOF
