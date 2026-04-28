"""Tests for scripts/html_audit.py. Static HTML accessibility checker.

Drives the script as a subprocess and asserts on the JSON contract: the
clean fixture must produce zero findings, and the violations fixture must
fire a known regression set of rules.
"""

from __future__ import annotations

import json
import subprocess
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT = REPO_ROOT / "scripts" / "html_audit.py"
FIXTURES = REPO_ROOT / "tests" / "fixtures" / "html"


def run_audit(fixture: str, fail_on: str = "any") -> tuple[int, list]:
    """Run html_audit.py on a fixture, return (exit_code, findings_list)."""
    proc = subprocess.run(
        ["python3", str(SCRIPT), str(FIXTURES / fixture), "--fail-on", fail_on],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
    )
    findings = json.loads(proc.stdout) if proc.stdout.strip() else []
    return proc.returncode, findings


class TestCleanFixture(unittest.TestCase):
    def test_clean_html_produces_no_findings(self):
        code, findings = run_audit("clean.html")
        self.assertEqual(
            findings, [], f"expected no findings, got {len(findings)}: {findings}"
        )
        self.assertEqual(code, 0)


class TestViolationsFixture(unittest.TestCase):
    EXPECTED_RULES = {
        "html-has-lang",
        "image-alt",
        "button-name",
        "label",
        "link-name",
        "frame-title",
        "meta-refresh",
        "aria-roles",
        "aria-valid-attr",
        "aria-hidden-body",
        "blink",
        "document-title",
    }

    def setUp(self):
        self.code, self.findings = run_audit("violations.html", fail_on="any")

    def test_exit_code_is_one(self):
        self.assertEqual(self.code, 1)

    def test_has_findings(self):
        self.assertGreater(len(self.findings), 0)

    def test_all_expected_rules_fire(self):
        rules_found = {f["rule"] for f in self.findings}
        missing = self.EXPECTED_RULES - rules_found
        self.assertFalse(
            missing,
            f"expected rules did not fire: {sorted(missing)}; "
            f"got rules: {sorted(rules_found)}",
        )

    def test_findings_have_required_fields(self):
        for f in self.findings:
            for key in ("rule", "impact", "line", "col", "element", "message"):
                self.assertIn(key, f, f"finding missing key {key!r}: {f}")


if __name__ == "__main__":
    unittest.main()
