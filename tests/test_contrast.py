"""Tests for scripts/contrast.py: WCAG contrast math and the suggest helper.

Reference values are validated against WebAIM and axe-core. We invoke the CLI
via subprocess for the JSON contract, and import the module functions directly
where it's cleaner.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT = REPO_ROOT / "scripts" / "contrast.py"

# Make the script importable as a module too, for the unit-level checks.
sys.path.insert(0, str(REPO_ROOT / "scripts"))
import contrast  # noqa: E402


def run_check(fg: str, bg: str) -> dict:
    """Run `contrast.py check FG BG` and return the parsed JSON."""
    proc = subprocess.run(
        ["python3", str(SCRIPT), "check", fg, bg],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
        check=True,
    )
    return json.loads(proc.stdout)


def run_suggest(fg: str, bg: str, target: float) -> dict:
    proc = subprocess.run(
        ["python3", str(SCRIPT), "suggest", fg, bg, "--target", str(target)],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
        check=True,
    )
    return json.loads(proc.stdout)


class TestContrastReferenceRatios(unittest.TestCase):
    """Canonical ratios verified against WebAIM contrast checker."""

    def test_black_on_white(self):
        r = run_check("#000000", "#ffffff")
        self.assertAlmostEqual(r["ratio"], 21.0, delta=0.05)
        self.assertTrue(r["passes"]["AA_normal"])
        self.assertTrue(r["passes"]["AA_large"])
        self.assertTrue(r["passes"]["AAA_normal"])
        self.assertTrue(r["passes"]["AAA_large"])

    def test_blue_on_white(self):
        r = run_check("#0000ff", "#ffffff")
        self.assertAlmostEqual(r["ratio"], 8.59, delta=0.05)
        self.assertTrue(r["passes"]["AA_normal"])
        self.assertTrue(r["passes"]["AAA_normal"])

    def test_777_on_white_aa_normal_fails(self):
        r = run_check("#777777", "#ffffff")
        self.assertAlmostEqual(r["ratio"], 4.48, delta=0.05)
        self.assertFalse(r["passes"]["AA_normal"])
        self.assertTrue(r["passes"]["AA_large"])

    def test_767_on_white_aa_normal_passes(self):
        r = run_check("#767676", "#ffffff")
        self.assertAlmostEqual(r["ratio"], 4.54, delta=0.05)
        self.assertTrue(r["passes"]["AA_normal"])

    def test_595959_on_white_is_aaa(self):
        r = run_check("#595959", "#ffffff")
        self.assertAlmostEqual(r["ratio"], 7.0, delta=0.05)
        self.assertTrue(r["passes"]["AAA_normal"])

    def test_tailwind_gray_500(self):
        r = run_check("#6b7280", "#ffffff")
        self.assertAlmostEqual(r["ratio"], 4.83, delta=0.05)
        self.assertTrue(r["passes"]["AA_normal"])
        self.assertFalse(r["passes"]["AAA_normal"])


class TestAlphaCompositing(unittest.TestCase):
    """Translucent foregrounds must be composited before measuring."""

    def test_half_alpha_black_on_white(self):
        # rgba(0,0,0,0.5) over white composites to ~#808080, which gives ~3.95.
        fg = contrast.parse_color("rgba(0,0,0,0.5)")
        bg = contrast.parse_color("#ffffff")
        composited = contrast.composite(fg, bg)
        ratio = contrast.contrast_ratio(composited, bg)
        self.assertAlmostEqual(round(ratio, 2), 3.95, delta=0.05)


class TestSuggestSubcommand(unittest.TestCase):
    def test_suggest_777_target_7(self):
        # #777777 has hue 0/sat 0; darkening to L≈0.349 gives #595959 (ratio 7.0).
        out = run_suggest("#777777", "#ffffff", 7.0)
        self.assertIsNotNone(out["suggested"])
        self.assertEqual(out["suggested"], "#595959")
        self.assertGreaterEqual(out["suggested_ratio"], 7.0)

    def test_suggest_pink_meets_aa(self):
        out = run_suggest("#ff6699", "#ffffff", 4.5)
        self.assertIsNotNone(out["suggested"])
        # Verify the suggestion actually meets target by re-checking.
        verify = run_check(out["suggested"], "#ffffff")
        self.assertGreaterEqual(verify["ratio"], 4.5)


class TestModuleAPI(unittest.TestCase):
    """Direct calls into the module. Sanity-check the math and parsers."""

    def test_parse_short_hex(self):
        c = contrast.parse_color("#abc")
        self.assertEqual((c.r, c.g, c.b, c.a), (0xAA, 0xBB, 0xCC, 1.0))

    def test_parse_rgba(self):
        c = contrast.parse_color("rgba(10, 20, 30, 0.5)")
        self.assertEqual((c.r, c.g, c.b), (10, 20, 30))
        self.assertAlmostEqual(c.a, 0.5)

    def test_relative_luminance_white(self):
        white = contrast.parse_color("#ffffff")
        self.assertAlmostEqual(contrast.relative_luminance(white), 1.0, places=4)

    def test_relative_luminance_black(self):
        black = contrast.parse_color("#000000")
        self.assertAlmostEqual(contrast.relative_luminance(black), 0.0, places=4)


if __name__ == "__main__":
    unittest.main()
