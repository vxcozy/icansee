# How to audit design tokens for contrast

The pre-commit gate can check your color tokens against WCAG contrast
thresholds and fail the commit if any pair drops below AA. Useful when a
designer adds a new shade and you want to catch it before it's used in
500 components.

## When to do this

- You maintain a JSON or CSS file of color tokens.
- Designers add or tweak colors regularly.
- You want every new pair to pass AA without manual review.

## 1. Pick the file

Token files come in several shapes. The audit understands two:

**Flat JSON:**

```json
{
  "text": "#111827",
  "muted": "#9ca3af",
  "link": "#2563eb",
  "danger": "#ef4444",
  "bg": "#ffffff",
  "surface": "#f9fafb"
}
```

**DTCG-ish JSON** (Style Dictionary, Tokens Studio):

```json
{
  "text": { "value": "#111827" },
  "muted": { "value": "#9ca3af" }
}
```

**CSS custom properties:**

```css
:root {
  --text: #111827;
  --muted: #9ca3af;
  --link: #2563eb;
  --bg: #ffffff;
}
```

The CSS path picks up only top-level `--name: hex;` declarations. Nested
selectors and `var(...)` references aren't resolved.

## 2. Drop the file at the path the audit checks

The pre-commit gate looks for `.icansee/palette.json`. Either put your
tokens directly there, or symlink:

```bash
ln -s ../tokens/colors.json .icansee/palette.json
```

If your tokens are CSS, save them as `.icansee/palette.css` and rename the
hook reference (or symlink). The CSS extractor and JSON extractor both
trigger off the file extension.

## 3. Run the audit manually first

```bash
python3 ~/.claude/skills/icansee/scripts/palette_audit.py matrix .icansee/palette.json
```

Output is JSON. Each fg×bg pair gets a ratio, AA/AAA pass/fail flags, and
(for failing pairs) a suggested replacement that preserves hue.

To check only specific combinations:

```bash
python3 ~/.claude/skills/icansee/scripts/palette_audit.py pairs .icansee/palette.json \
  --pair text:bg \
  --pair muted:bg \
  --pair link:surface
```

## 4. Fix or accept findings

For each failing pair:

- **Fix**: replace the token value with the suggested color (or any color
  that passes), commit, the audit will pass next time.
- **Accept the failure** by removing the token from the matrix. For
  example, if `muted` is only ever used on a `surface` background, it
  doesn't need to pass against `bg`.

The audit doesn't know which pairs actually appear in your UI. It computes
the full matrix by default. Use `--foregrounds` and `--backgrounds` to
restrict:

```bash
python3 ~/.claude/skills/icansee/scripts/palette_audit.py matrix .icansee/palette.json \
  --foregrounds text,muted,link,danger \
  --backgrounds bg,surface
```

If you want this restricted check at pre-commit, the simplest path is to
maintain a smaller `.icansee/palette.json` that only contains the tokens
you actually pair. Two files are fine: your full token export, and a
trimmed audit file.

## 5. Wire it into pre-commit (already done if `.icansee/palette.json` exists)

The pre-commit hook checks `.icansee/palette.json` automatically. Any
commit touching anything will run the matrix audit and block on AA-normal
failures.

If you want the audit to run *only* when token files change, the simplest
shape is a separate hook layer, but that's beyond the gate's default. The
overhead of running the matrix on every commit is < 100ms, so the simpler
path usually wins.

## Verify the gate fires

Stage an intentionally bad token:

```bash
python3 -c 'import json; d=json.load(open(".icansee/palette.json")); d["bad"]="#999"; json.dump(d, open(".icansee/palette.json","w"))'
git add .icansee/palette.json
git commit -m "test"
```

You should see something like:

```
▸ Design tokens (icansee/palette_audit.py)
{
  "tokens_file": ".icansee/palette.json",
  "checked": ...,
  "failing_AA_normal": 1,
  ...
}
icansee: 1 token pair(s) failing AA normal contrast
```

Roll back the bad token, re-commit, the gate passes.
