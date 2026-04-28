#!/usr/bin/env bash
set -e
ICANSEE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ICANSEE_DIR"
echo "▸ contrast.py"
python3 -m unittest tests.test_contrast -v
echo "▸ html_audit.py"
python3 -m unittest tests.test_html_audit -v
echo "▸ install.sh"
bash tests/test_install.sh
echo "✓ all tests passed"
