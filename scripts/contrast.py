#!/usr/bin/env python3
"""WCAG 2 contrast ratio calculator.

Implements the relative-luminance and contrast formulas from
https://www.w3.org/TR/WCAG22/#dfn-contrast-ratio so that ratios reported here
match what axe-core, Chrome DevTools, and the WCAG quick reference report.

Subcommands:
  check    foreground background [--text-size normal|large] [--alpha-bg HEX]
  suggest  foreground background [--target 4.5] [--direction auto|darker|lighter]
  pair     foreground background   (one-line human-readable summary)

Output is JSON unless --human is passed.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass

# WCAG thresholds. 1.4.11 (non-text) is 3.0 for UI components and graphical objects.
THRESHOLDS = {
    "AA_normal": 4.5,
    "AA_large": 3.0,
    "AAA_normal": 7.0,
    "AAA_large": 4.5,
    "non_text": 3.0,
}


# ---------- color parsing ---------------------------------------------------


@dataclass(frozen=True)
class RGBA:
    r: int  # 0-255
    g: int
    b: int
    a: float = 1.0  # 0.0-1.0


_HEX_RE = re.compile(r"^#?([0-9a-fA-F]+)$")
_RGB_RE = re.compile(
    r"^rgba?\(\s*([\d.]+)\s*,\s*([\d.]+)\s*,\s*([\d.]+)\s*"
    r"(?:,\s*([\d.]+)\s*)?\)$"
)


def parse_color(s: str) -> RGBA:
    """Parse #rgb / #rgba / #rrggbb / #rrggbbaa or rgb()/rgba() into an RGBA."""
    s = s.strip()
    m = _HEX_RE.match(s)
    if m:
        h = m.group(1)
        if len(h) == 3:
            r, g, b = (int(c * 2, 16) for c in h)
            return RGBA(r, g, b, 1.0)
        if len(h) == 4:
            r, g, b, a = (int(c * 2, 16) for c in h)
            return RGBA(r, g, b, a / 255)
        if len(h) == 6:
            r, g, b = (int(h[i : i + 2], 16) for i in (0, 2, 4))
            return RGBA(r, g, b, 1.0)
        if len(h) == 8:
            r, g, b, a = (int(h[i : i + 2], 16) for i in (0, 2, 4, 6))
            return RGBA(r, g, b, a / 255)
        raise ValueError(f"Unrecognized hex color: {s!r}")
    m = _RGB_RE.match(s)
    if m:
        r, g, b = (int(round(float(m.group(i)))) for i in (1, 2, 3))
        a = float(m.group(4)) if m.group(4) else 1.0
        return RGBA(r, g, b, a)
    raise ValueError(f"Unrecognized color: {s!r}")


def to_hex(c: RGBA) -> str:
    if c.a == 1.0:
        return f"#{c.r:02x}{c.g:02x}{c.b:02x}"
    return f"#{c.r:02x}{c.g:02x}{c.b:02x}{int(round(c.a * 255)):02x}"


# ---------- alpha compositing ----------------------------------------------


def composite(fg: RGBA, bg: RGBA) -> RGBA:
    """Composite a possibly-translucent fg over an opaque bg (Porter–Duff "over")."""
    if fg.a == 1.0:
        return fg
    if bg.a != 1.0:
        # Caller error. The underlying canvas must be opaque to compute a
        # meaningful contrast ratio. Tell them.
        raise ValueError(
            "Background must be fully opaque to composite. "
            "Pick the actual page/canvas color underneath."
        )
    a = fg.a
    return RGBA(
        r=int(round(fg.r * a + bg.r * (1 - a))),
        g=int(round(fg.g * a + bg.g * (1 - a))),
        b=int(round(fg.b * a + bg.b * (1 - a))),
        a=1.0,
    )


# ---------- WCAG formulas --------------------------------------------------


def _channel_lum(v: int) -> float:
    s = v / 255.0
    return s / 12.92 if s <= 0.04045 else ((s + 0.055) / 1.055) ** 2.4


def relative_luminance(c: RGBA) -> float:
    if c.a != 1.0:
        raise ValueError("Composite translucent colors before measuring luminance.")
    return (
        0.2126 * _channel_lum(c.r)
        + 0.7152 * _channel_lum(c.g)
        + 0.0722 * _channel_lum(c.b)
    )


def contrast_ratio(fg: RGBA, bg: RGBA) -> float:
    l1 = relative_luminance(fg)
    l2 = relative_luminance(bg)
    lighter, darker = (l1, l2) if l1 >= l2 else (l2, l1)
    return (lighter + 0.05) / (darker + 0.05)


# ---------- HSL helpers (for the suggest subcommand) -----------------------


def rgb_to_hsl(c: RGBA) -> tuple[float, float, float]:
    r, g, b = c.r / 255, c.g / 255, c.b / 255
    mx, mn = max(r, g, b), min(r, g, b)
    l = (mx + mn) / 2
    if mx == mn:
        return 0.0, 0.0, l
    d = mx - mn
    s = d / (2 - mx - mn) if l > 0.5 else d / (mx + mn)
    if mx == r:
        h = ((g - b) / d) % 6
    elif mx == g:
        h = (b - r) / d + 2
    else:
        h = (r - g) / d + 4
    return h * 60, s, l


def hsl_to_rgb(h: float, s: float, l: float) -> RGBA:
    c = (1 - abs(2 * l - 1)) * s
    x = c * (1 - abs(((h / 60) % 2) - 1))
    m = l - c / 2
    if 0 <= h < 60:
        rp, gp, bp = c, x, 0
    elif 60 <= h < 120:
        rp, gp, bp = x, c, 0
    elif 120 <= h < 180:
        rp, gp, bp = 0, c, x
    elif 180 <= h < 240:
        rp, gp, bp = 0, x, c
    elif 240 <= h < 300:
        rp, gp, bp = x, 0, c
    else:
        rp, gp, bp = c, 0, x
    return RGBA(
        int(round((rp + m) * 255)),
        int(round((gp + m) * 255)),
        int(round((bp + m) * 255)),
        1.0,
    )


def suggest_foreground(
    fg: RGBA, bg: RGBA, target: float, direction: str = "auto"
) -> tuple[RGBA, float] | None:
    """Find the nearest foreground (hue/saturation preserved) that meets `target`.

    Adjusts L in HSL. Returns (color, achieved_ratio) or None if unreachable
    even at pure black/white in the chosen direction.
    """
    h, s, _ = rgb_to_hsl(fg)
    bg_l = relative_luminance(bg)

    if direction == "auto":
        # Move away from the background's luminance.
        direction = "darker" if bg_l > 0.179 else "lighter"

    # Binary search L on [0, fg_l] (darker) or [fg_l, 1] (lighter).
    fg_h, fg_s, fg_l = rgb_to_hsl(fg)
    lo, hi = (0.0, fg_l) if direction == "darker" else (fg_l, 1.0)
    # Check the extreme first; if it doesn't pass, nothing in range will.
    extreme_l = lo if direction == "darker" else hi
    extreme = hsl_to_rgb(fg_h, fg_s, extreme_l)
    if contrast_ratio(extreme, bg) < target:
        return None

    best = extreme
    best_ratio = contrast_ratio(extreme, bg)
    for _ in range(40):  # 1e-12 precision, way more than needed
        mid = (lo + hi) / 2
        candidate = hsl_to_rgb(fg_h, fg_s, mid)
        ratio = contrast_ratio(candidate, bg)
        if ratio >= target:
            best, best_ratio = candidate, ratio
            # Walk back toward original L to minimize visual change.
            if direction == "darker":
                lo = mid
            else:
                hi = mid
        else:
            if direction == "darker":
                hi = mid
            else:
                lo = mid
    return best, best_ratio


# ---------- evaluation -----------------------------------------------------


def evaluate(ratio: float) -> dict:
    return {
        "ratio": round(ratio, 2),
        "passes": {
            "AA_normal": ratio >= THRESHOLDS["AA_normal"],
            "AA_large": ratio >= THRESHOLDS["AA_large"],
            "AAA_normal": ratio >= THRESHOLDS["AAA_normal"],
            "AAA_large": ratio >= THRESHOLDS["AAA_large"],
            "non_text_1_4_11": ratio >= THRESHOLDS["non_text"],
        },
    }


def best_level(ratio: float, text_size: str) -> str:
    """Highest level passed: 'AAA', 'AA', or 'fail'."""
    aaa = THRESHOLDS["AAA_large" if text_size == "large" else "AAA_normal"]
    aa = THRESHOLDS["AA_large" if text_size == "large" else "AA_normal"]
    if ratio >= aaa:
        return "AAA"
    if ratio >= aa:
        return "AA"
    return "fail"


# ---------- CLI ------------------------------------------------------------


def cmd_check(args) -> int:
    fg = parse_color(args.foreground)
    bg = parse_color(args.background)
    composited_fg = composite(fg, bg) if fg.a < 1.0 else fg
    ratio = contrast_ratio(composited_fg, bg)
    result = {
        "foreground": args.foreground,
        "background": args.background,
        "composited_foreground": to_hex(composited_fg),
        **evaluate(ratio),
        "best_level": {
            "normal_text": best_level(ratio, "normal"),
            "large_text": best_level(ratio, "large"),
        },
        "thresholds": THRESHOLDS,
    }
    if args.human:
        p = result["passes"]
        print(
            f"{args.foreground} on {args.background}: "
            f"{result['ratio']}:1: "
            f"AA normal {'PASS' if p['AA_normal'] else 'FAIL'}, "
            f"AA large {'PASS' if p['AA_large'] else 'FAIL'}, "
            f"AAA normal {'PASS' if p['AAA_normal'] else 'FAIL'}, "
            f"AAA large {'PASS' if p['AAA_large'] else 'FAIL'}, "
            f"1.4.11 {'PASS' if p['non_text_1_4_11'] else 'FAIL'}"
        )
    else:
        print(json.dumps(result, indent=2))
    return 0


def cmd_suggest(args) -> int:
    fg = parse_color(args.foreground)
    bg = parse_color(args.background)
    fg_c = composite(fg, bg) if fg.a < 1.0 else fg
    current_ratio = contrast_ratio(fg_c, bg)
    suggestion = suggest_foreground(fg_c, bg, args.target, args.direction)
    out = {
        "foreground": args.foreground,
        "background": args.background,
        "current_ratio": round(current_ratio, 2),
        "target": args.target,
        "direction": args.direction,
    }
    if suggestion is None:
        out["suggested"] = None
        out["reason"] = (
            f"Target {args.target}:1 unreachable from this hue/saturation in "
            f"the {args.direction} direction. Try direction=auto or pick a "
            f"different background."
        )
    else:
        new_fg, new_ratio = suggestion
        out["suggested"] = to_hex(new_fg)
        out["suggested_ratio"] = round(new_ratio, 2)
    print(json.dumps(out, indent=2))
    return 0


def cmd_pair(args) -> int:
    args.human = True
    return cmd_check(args)


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="cmd", required=True)

    pc = sub.add_parser("check", help="Report ratio and AA/AAA pass/fail.")
    pc.add_argument("foreground")
    pc.add_argument("background")
    pc.add_argument("--human", action="store_true")
    pc.set_defaults(func=cmd_check)

    ps = sub.add_parser(
        "suggest", help="Find nearest foreground (hue preserved) that meets target."
    )
    ps.add_argument("foreground")
    ps.add_argument("background")
    ps.add_argument("--target", type=float, default=4.5)
    ps.add_argument("--direction", choices=["auto", "darker", "lighter"], default="auto")
    ps.set_defaults(func=cmd_suggest)

    pp = sub.add_parser("pair", help="One-line human summary (alias for check --human).")
    pp.add_argument("foreground")
    pp.add_argument("background")
    pp.set_defaults(func=cmd_pair)

    args = p.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
