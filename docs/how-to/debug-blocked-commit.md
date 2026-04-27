# How to debug a blocked commit

The gate fired on a commit and you're not sure what to do. This page walks
through the typical shape of pre-commit output and how to act on it.

## Read the output

A blocked commit looks like this:

```
▸ JSX / TSX (eslint-plugin-jsx-a11y)
src/components/SignUp.tsx
  17:5  error  An element with role="button" has no keyboard listener  jsx-a11y/click-events-have-key-events
  19:5  error  Form label must be associated with a control            jsx-a11y/label-has-associated-control

▸ Plain HTML (icansee/html_audit.py)
public/landing.html:14:2 [critical] image-alt: <img> missing alt; use alt="" for decorative images

3 finding(s)

icansee: ✗ a11y findings detected, commit blocked.
```

Each finding has:

- **File and position**: `path:line:col`.
- **Severity**: `[critical]`, `[serious]`, `[moderate]`, `[minor]`.
  Matches axe-core's impact ratings.
- **Rule id**: `jsx-a11y/click-events-have-key-events`, `image-alt`, etc.
- **Message**: one-sentence explanation.

## Decide whether the gate is right

It almost always is. But the rare case where it isn't:

- Disabled controls flagged for contrast. Verify the control actually
  has the `disabled` attribute or `aria-disabled="true"`. If yes,
  contrast is exempt. If no, fix it.
- Decorative images flagged for missing alt. The right answer is
  `alt=""`, not removing the gate. An empty alt is a deliberate signal.
- Brand colors failing contrast. See "Fix the most common findings"
  below. The gate is right, but the fix may be a token change rather
  than an inline color override.

If you're confident the gate is wrong (very rare), use `--no-verify` for
the commit and open a discussion to refine the rule set. Don't habituate
to bypassing.

## Fix the most common findings

### `image-alt`: `<img>` missing alt

```html
<!-- BAD -->
<img src="/banner.jpg">

<!-- GOOD: descriptive alt -->
<img src="/banner.jpg" alt="Q4 product launch">

<!-- GOOD: decorative -->
<img src="/sparkle.svg" alt="">
```

Decorative means: removing the image would lose nothing important. Spacers,
flourishes, repeated icons next to text labels.

### `button-name` / `link-name`: empty button or link

Icon-only buttons need a label:

```html
<button aria-label="Close dialog">
  <svg aria-hidden="true" focusable="false">...</svg>
</button>
```

Mark the SVG `aria-hidden` so screen readers announce only the button's
label, not the icon's path.

### `label`: `<input>` without an associated label

```html
<!-- BAD: placeholder is not a label -->
<input type="email" placeholder="Email" />

<!-- GOOD -->
<label for="email">Email</label>
<input id="email" type="email" autocomplete="email" />
```

### `color-contrast` (or the static gate's mention of contrast)

Run the contrast script with the actual values:

```bash
~/.claude/skills/icansee/scripts/contrast.py check "#777" "#fff"
```

You'll get the exact ratio and a pass/fail table. If failing, get a
hue-preserving suggestion:

```bash
~/.claude/skills/icansee/scripts/contrast.py suggest "#777" "#fff" --target 4.5
```

Apply the suggestion. If the failing color is a brand color you can't
change, switch the *role* it's playing. Brand color as text on most
backgrounds will keep failing; brand color as a non-text element (border,
icon, large heading) has a more lenient threshold.

### `aria-valid-attr` / `aria-roles`: typo'd ARIA

```html
<!-- BAD -->
<div role="clickable" aria-labl="x">

<!-- GOOD: real role and attribute -->
<div role="button" aria-label="x">
```

Don't add ARIA where native HTML works. `<button>` already has
`role="button"`; `<a href>` already has `role="link"`.

## Re-run before re-committing

After applying a fix:

```bash
~/.claude/skills/icansee/scripts/audit.sh --staged
```

This runs the same checks the hook will run, on whatever you've staged.
You'll see the same output, but without the commit attempt. Iterate until
it's clean, then commit.

## When the gate doesn't load at all

If `git commit` happens with no icansee output at all, the hook isn't
firing. Check:

```bash
ls -l "$(git rev-parse --git-path hooks)/pre-commit"
```

Should be executable and contain `icansee` somewhere. If missing, re-run
`install.sh`.

If you use husky, check `.husky/pre-commit` instead. Husky's hook config
sometimes silently overrides plain git hooks.

## Look up a rule

Every rule id is searchable in
[the static rules reference](../reference/static-rules.md), which says what
the rule checks and why. The axe-core reference is more authoritative:
https://github.com/dequelabs/axe-core/blob/develop/doc/rule-descriptions.md

## When the gate seems wrong on contrast

The gate uses the WCAG relative-luminance formula directly. Numbers should
match WebAIM's contrast checker, Chrome DevTools' a11y panel, and what
axe-core reports. If you're seeing a different number somewhere:

- Are you measuring against the right background? Translucent foregrounds
  must be composited against the actual canvas color, not white by reflex.
- Are you measuring computed cascade, or the source color? The static gate
  measures source values; the rendered audit (pre-push / CI) measures
  computed.
- Are you on a Mac with f.lux / Night Shift / a calibrated profile?
  Eyeballing rarely matches measured ratios.
