#!/usr/bin/env python3
"""Audit a palette of design tokens for WCAG contrast compliance.

Reads tokens from one of:
  - JSON file: {"text": "#111", "muted": "#666", ...} or
               {"text": {"value": "#111"}, ...} (Style Dictionary / DTCG-ish)
  - CSS file: extracts top-level `--name: #hex;` custom properties

Then either:
  - matrix mode (default): computes the full foreground × background pair matrix
  - pairs mode: caller supplies explicit fg/bg pairs to check

Output is JSON with one entry per checked pair: ratio, levels passed, and
(for failing pairs) a suggested foreground that would pass AA normal.

Usage:
  palette_audit.py matrix tokens.json
  palette_audit.py matrix tokens.css --foregrounds text,muted --backgrounds bg,surface
  palette_audit.py pairs tokens.json --pair text:bg --pair muted:surface
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

# Reuse the contrast module from the same dir.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from contrast import (  # noqa: E402
    THRESHOLDS,
    composite,
    contrast_ratio,
    evaluate,
    parse_color,
    suggest_foreground,
    to_hex,
)


_CSS_VAR_RE = re.compile(
    r"--([\w-]+)\s*:\s*(#[0-9a-fA-F]{3,8}|rgba?\([^)]+\))\s*;"
)


def load_tokens(path: Path) -> dict[str, str]:
    text = path.read_text()
    if path.suffix.lower() == ".json":
        raw = json.loads(text)
        flat: dict[str, str] = {}
        for k, v in raw.items():
            if isinstance(v, str):
                flat[k] = v
            elif isinstance(v, dict) and "value" in v and isinstance(v["value"], str):
                flat[k] = v["value"]
            # else: skip nested groups; users can flatten before passing in
        return flat
    # Treat anything else as CSS
    return {m.group(1): m.group(2) for m in _CSS_VAR_RE.finditer(text)}


def split_csv(value: str | None) -> list[str] | None:
    if not value:
        return None
    return [s.strip() for s in value.split(",") if s.strip()]


def audit_pair(fg_name: str, fg_hex: str, bg_name: str, bg_hex: str) -> dict:
    fg = parse_color(fg_hex)
    bg = parse_color(bg_hex)
    if bg.a < 1.0:
        # Skip. Undefined without knowing what's beneath.
        return {
            "fg": fg_name,
            "bg": bg_name,
            "skipped": "background is not opaque",
        }
    fg_c = composite(fg, bg) if fg.a < 1.0 else fg
    ratio = contrast_ratio(fg_c, bg)
    entry = {
        "fg": fg_name,
        "fg_hex": fg_hex,
        "bg": bg_name,
        "bg_hex": bg_hex,
        **evaluate(ratio),
    }
    if not entry["passes"]["AA_normal"]:
        sugg = suggest_foreground(fg_c, bg, THRESHOLDS["AA_normal"])
        if sugg is not None:
            new_fg, new_ratio = sugg
            entry["suggested_fg"] = to_hex(new_fg)
            entry["suggested_ratio"] = round(new_ratio, 2)
    return entry


def cmd_matrix(args) -> int:
    tokens = load_tokens(Path(args.tokens))
    if not tokens:
        print(
            f"No color tokens found in {args.tokens}. Provide JSON of "
            "{name: hex} pairs or CSS with --custom-properties.",
            file=sys.stderr,
        )
        return 2
    fg_names = split_csv(args.foregrounds) or list(tokens)
    bg_names = split_csv(args.backgrounds) or list(tokens)
    missing = [n for n in (*fg_names, *bg_names) if n not in tokens]
    if missing:
        print(f"Tokens not found: {missing}", file=sys.stderr)
        return 2
    results = []
    for fg in fg_names:
        for bg in bg_names:
            if fg == bg:
                continue
            results.append(audit_pair(fg, tokens[fg], bg, tokens[bg]))
    summary = {
        "tokens_file": str(args.tokens),
        "checked": len(results),
        "failing_AA_normal": sum(
            1 for r in results if not r.get("passes", {}).get("AA_normal", True)
        ),
        "results": results,
    }
    print(json.dumps(summary, indent=2))
    return 0


def cmd_pairs(args) -> int:
    tokens = load_tokens(Path(args.tokens))
    results = []
    for spec in args.pair:
        if ":" not in spec:
            print(f"Bad --pair {spec!r}; expected fg:bg", file=sys.stderr)
            return 2
        fg, bg = spec.split(":", 1)
        if fg not in tokens or bg not in tokens:
            print(f"Token missing for pair {spec}", file=sys.stderr)
            return 2
        results.append(audit_pair(fg, tokens[fg], bg, tokens[bg]))
    print(json.dumps({"results": results}, indent=2))
    return 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="cmd", required=True)

    pm = sub.add_parser("matrix", help="Check every fg×bg pair (or filtered subset).")
    pm.add_argument("tokens")
    pm.add_argument(
        "--foregrounds",
        help="Comma-separated token names to use as foregrounds (default: all).",
    )
    pm.add_argument(
        "--backgrounds",
        help="Comma-separated token names to use as backgrounds (default: all).",
    )
    pm.set_defaults(func=cmd_matrix)

    pp = sub.add_parser("pairs", help="Check explicit fg:bg pairs.")
    pp.add_argument("tokens")
    pp.add_argument("--pair", action="append", required=True, help="fg:bg")
    pp.set_defaults(func=cmd_pairs)

    args = p.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
