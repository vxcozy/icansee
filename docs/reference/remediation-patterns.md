# Remediation patterns

Concrete fixes for the failures Claude will see most often. Prefer the
**first** option in each section unless the user has a constraint that rules
it out.

## Failing color contrast

1. Run `scripts/contrast.py suggest <fg> <bg> --target 4.5` (or 7.0 for AAA)
   to get a hue-preserving alternative.
2. If the failing color is a brand color, suggest changing the role:
   - Brand color as decoration / non-text → still fine.
   - Brand color as text → only on a background that yields ≥ 4.5:1.
3. Add a darker/lighter token in the palette rather than overriding ad hoc
   inline styles. Update `palette_audit.py` matrix output to confirm.

## Icon-only button with no name

```html
<!-- BAD -->
<button><svg>...</svg></button>

<!-- GOOD: visible text or aria-label -->
<button aria-label="Close dialog">
  <svg aria-hidden="true" focusable="false">...</svg>
</button>
```
- Add `aria-hidden="true"` and `focusable="false"` to the SVG so screen
  readers announce only the button label.

## Input without a label

```html
<!-- BAD -->
<input type="email" placeholder="Email" />

<!-- GOOD -->
<label for="email">Email</label>
<input id="email" type="email" autocomplete="email" />
```
- For floating-label patterns, the visible label still needs to be a real
  `<label>` linked by `for`/`id`. Moving it visually with CSS is fine.

## Decorative image

```html
<!-- BAD: alt is missing entirely -->
<img src="sparkle.svg" />

<!-- GOOD: explicitly empty -->
<img src="sparkle.svg" alt="" />
```

## Informational SVG

```html
<svg role="img" aria-labelledby="chart-title">
  <title id="chart-title">Quarterly revenue, 2023</title>
  ...
</svg>
```

## Color as the only signal

Required field indicated only by red text:
```html
<!-- BAD -->
<label class="text-red-600">Email</label>

<!-- GOOD: text + aria + visual -->
<label for="email">
  Email <span aria-hidden="true">*</span>
  <span class="sr-only">(required)</span>
</label>
<input id="email" required aria-required="true" />
```

## Error state on an input

```html
<!-- BAD: red border only -->
<input class="border-red-500" />

<!-- GOOD -->
<input
  aria-invalid="true"
  aria-describedby="email-error"
/>
<p id="email-error" role="alert">Enter a valid email address.</p>
```

## Heading order skipped

If a section jumps from `<h2>` to `<h4>`, either promote the `<h4>` to `<h3>`
or insert a meaningful `<h3>` between them. Don't hide a fake heading just to
satisfy the rule.

## Missing landmark / `<main>`

Wrap the primary content in `<main>` exactly once per document. Use
`<header>`, `<nav>`, `<footer>`, `<aside>` for the corresponding ARIA
landmarks. They're better than `<div role="main">`.

## Disabled control with poor contrast

Disabled controls are exempt from 1.4.3. But verify they're really disabled:
- HTML: the `disabled` attribute is set.
- Custom widgets: `aria-disabled="true"` AND keyboard activation is
  prevented in JS.
- If neither is true, contrast still applies. Pick a lighter "disabled-look"
  that you actually disable, or a darker color that passes 4.5:1.

## Translucent overlay text

```css
/* BAD: rgba on top of an unknown background */
color: rgba(0, 0, 0, 0.6);

/* GOOD: composite to opaque against the known canvas */
color: #666666; /* equiv on white; recompute per surface */
```
- `contrast.py` will composite for you when you pass the rgba and the actual
  opaque canvas color.

## Focus indicator with insufficient contrast (1.4.11)

The focus ring is a UI component. It needs ≥ 3:1 against the background it
overlaps. A 1px inset light-gray ring on a white card fails. Options:
- Thicker ring (2px+) in a darker color.
- Outer ring + inner ring in contrasting colors.
- Don't rely on the browser default if you've set `outline: none` anywhere.
