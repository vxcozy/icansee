#!/usr/bin/env bash
set -e
ICANSEE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ICANSEE_DIR"

# Pre-flight: every required tool checked once, up front. If any are
# missing, fail loudly here rather than letting the suite cascade into
# unhelpful "command not found" stack traces deep in a test case.
missing=()
for tool in bash node python3; do
  command -v "$tool" >/dev/null 2>&1 || missing+=("$tool")
done
if [ "${#missing[@]}" -gt 0 ]; then
  echo "✗ missing required tools: ${missing[*]}" >&2
  echo "  icansee tests need bash, node, and python3 on PATH." >&2
  exit 1
fi

echo "▸ contrast.py"
python3 -m unittest tests.test_contrast -v
echo "▸ html_audit.py"
python3 -m unittest tests.test_html_audit -v
echo "▸ install.sh"
bash tests/test_install.sh
echo "▸ axe-runner.mjs schema"
bash tests/test_runner_schema.sh
echo "✓ all tests passed"
