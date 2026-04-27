# Statically reviewable axe-core rules (WCAG 2.0 / 2.1 A and AA)

Rules in this list can be checked by reading source. Rules that
genuinely require a rendered DOM (`bypass`, `region`,
`scrollable-region-focusable`, `frame-tested`) are out of scope for
static review. Note them as "needs runtime axe-core" and move on.

For each rule below: what to grep for, what passes, what fails. Treat
anything ambiguous as "needs review", not "pass".

---

## Color and visual

### `color-contrast` (WCAG 1.4.3, AA)

- **Source signal**: any text element with explicit `color` and a
  resolvable background (inline style, CSS class, design token, or
  inherited).
- **Action**: call `scripts/contrast.py check <fg> <bg>`. Compare against
  the text's effective size to choose the AA threshold.
- **Fails**: ratio < 4.5 (normal) / < 3.0 (large).
- **Common false alarm**: utility-class systems where the parent
  element defines the background. Walk up the tree.

### `link-in-text-block` (WCAG 1.4.1, A)

- **Source signal**: `<a>` inside a paragraph or other text block whose
  only distinguishing style is `color`.
- **Passes** if any of: underline (`text-decoration: underline`), bold
  weight, background color, or a 3:1 contrast ratio against surrounding
  text *and* a non-color cue on hover/focus.
- **Fails**: same color family with no other indicator.

---

## Text alternatives

### `image-alt` (WCAG 1.1.1, A)

- `<img>` with **no** `alt`, `aria-label`, `aria-labelledby`, **and** no
  `role="presentation"` / `role="none"` → fail.
- `alt=""` is a **pass** for decorative images and is the correct value,
  not a missing attribute.

### `input-image-alt` (WCAG 1.1.1, A)

- `<input type="image">` must have `alt`, `aria-label`, or
  `aria-labelledby`.

### `area-alt` (WCAG 2.4.4, A)

- `<area>` inside `<map>` needs `alt` (or `aria-label[ledby]`).

### `object-alt` (WCAG 1.1.1, A)

- `<object>` needs accessible inner text or `aria-label[ledby]`.

### `svg-img-alt` (WCAG 1.1.1, A)

- `<svg role="img">` needs `<title>` as the **first child**, or
  `aria-label`.
- Decorative SVG should have `aria-hidden="true"` and not `role="img"`.

### `role-img-alt` (WCAG 1.1.1, A)

- Any `role="img"` element needs an accessible name.

### `video-caption` (WCAG 1.2.2, A)

- `<video>` should have `<track kind="captions">` for prerecorded
  content. "Needs review" if you can't see the asset; flag it.

---

## Forms

### `label` (WCAG 4.1.2 / 1.3.1, A)

- Every `<input>` (except `type="hidden"`, `type="button"`,
  `type="submit"`, `type="reset"`, `type="image"`), `<select>`, and
  `<textarea>` needs one of:
  - `<label for="id">` referencing it,
  - wrapping `<label>`,
  - `aria-label`,
  - `aria-labelledby`.
- `placeholder` is **not** a label.

### `select-name` (WCAG 4.1.2, A)

- Same as `label` but specifically `<select>`.

### `button-name` (WCAG 4.1.2, A)

- `<button>` needs visible text content **or** `aria-label[ledby]`
  **or** a child `<img alt="...">` with non-empty alt.
- Icon-only buttons (`<button><svg/></button>`) without an accessible
  name fail.

### `input-button-name` (WCAG 4.1.2, A)

- `<input type="button|submit|reset">` needs a non-empty `value`.

### `form-field-multiple-labels` (WCAG 3.3.2, A)

- One control should not have two `<label for>` references.

### `autocomplete-valid` (WCAG 1.3.5, AA, WCAG 2.1)

- If `autocomplete` is set, the value must be from the WHATWG token
  list (`name`, `email`, `tel`, `street-address`, `cc-number`, ...).
  Custom values fail.

---

## ARIA

### `aria-allowed-attr` (WCAG 4.1.2, A)

- An ARIA attribute must be allowed on the element's role. For
  example, `aria-checked` on a `<div role="button">` is fine; on a
  `<div role="link">` it isn't.

### `aria-required-attr` (WCAG 4.1.2, A)

- Roles with required attrs: `checkbox`/`switch` need `aria-checked`,
  `combobox` needs `aria-expanded`, `slider` needs `aria-valuenow`,
  and so on.

### `aria-valid-attr` / `aria-valid-attr-value` (WCAG 4.1.2, A)

- `aria-*` names must be real ARIA attributes, and their values must
  match the spec (booleans true/false, idrefs that exist, enums from
  the allowed set).

### `aria-roles` (WCAG 4.1.2, A)

- `role="..."` must be a valid ARIA role. `role="button"` is good;
  `role="clickable"` is invalid.

### `aria-hidden-focus` (WCAG 4.1.2, A)

- An element with `aria-hidden="true"` must not contain focusable
  descendants (links, buttons, inputs, anything with `tabindex >= 0`).

### `aria-hidden-body` (WCAG 4.1.2 / 1.3.1, A)

- `<body aria-hidden="true">` is never correct.

### `aria-command-name` / `aria-input-field-name` / `aria-toggle-field-name` / `aria-tab-name` / `aria-tooltip-name` / `aria-meter-name` / `aria-progressbar-name` (WCAG 4.1.2 / 1.1.1, A)

- Custom widgets
  (`role="button|link|menuitem|checkbox|switch|textbox|combobox|listbox|searchbox|tab|tooltip|meter|progressbar"`)
  need an accessible name (text content, `aria-label`, or
  `aria-labelledby`).

### `aria-prohibited-attr` (WCAG 4.1.2, A)

- Some roles forbid certain ARIA attrs (`aria-label` on
  `role="presentation"`, for example).

### `aria-deprecated-role` (WCAG 4.1.2, A)

- Roles like `directory` are deprecated; use a current equivalent.

### `nested-interactive` (WCAG 4.1.2, A)

- Don't put `<button>` inside `<a>`, or two interactive elements
  inside each other.

---

## Structure and semantics

### `html-has-lang` (WCAG 3.1.1, A)

- `<html>` must have `lang`.

### `html-lang-valid` (WCAG 3.1.1, A)

- `lang` must be a valid BCP-47 tag (`en`, `en-US`, `pt-BR`).

### `valid-lang` (WCAG 3.1.2, AA)

- Same rule for `lang` attributes inside the document.

### `html-xml-lang-mismatch` (WCAG 3.1.1, A)

- If both `lang` and `xml:lang` are present, base languages must match.

### `document-title` (WCAG 2.4.2, A)

- `<title>` exists and is non-empty.

### `frame-title` (WCAG 4.1.2, A)

- `<iframe>` and `<frame>` need a non-empty `title` (or
  `aria-label[ledby]`).

### `frame-title-unique` (WCAG 4.1.2, A)

- Two frames with the same title fail; titles must be distinguishable.

### `frame-focusable-content` (WCAG 2.1.1, A)

- A frame containing focusable content must not have `tabindex="-1"`
  on the frame itself.

### `meta-refresh` (WCAG 2.2.1, A)

- `<meta http-equiv="refresh" content="N; ...">` with N > 0 fails
  (except N=0 for redirects, which is permitted by axe).

### `meta-viewport` (WCAG 1.4.4, AA)

- `<meta name="viewport">` must not contain `user-scalable=no` or
  `maximum-scale` < 2.

### `avoid-inline-spacing` (WCAG 1.4.12, AA, WCAG 2.1)

- Inline `style="line-height|letter-spacing|word-spacing"` with
  `!important` prevents user spacing overrides and fails.

### `definition-list` / `dlitem` / `list` / `listitem` (WCAG 1.3.1, A)

- `<dt>`/`<dd>` only inside `<dl>`, `<li>` only inside
  `<ul>`/`<ol>`/`<menu>`, `<dl>` may only contain `<dt>`, `<dd>`,
  scripting/template, or grouping `<div>`.

### `td-headers-attr` / `th-has-data-cells` (WCAG 1.3.1, A)

- `<td headers="...">` ids must point at `<th>` elements in the same
  table.
- Every `<th>` should describe at least one data cell.

### `summary-name` (WCAG 4.1.2, A)

- `<summary>` needs visible text content.

### `duplicate-id-aria` (WCAG 4.1.2, A)

- Any `id` referenced by
  `aria-labelledby`/`aria-describedby`/`for=` etc. must be unique on
  the page.

---

## Time-based and motion

### `blink` (WCAG 2.2.2, A)

- Don't use `<blink>`.

### `marquee` (WCAG 2.2.2, A)

- Don't use `<marquee>`.

### `no-autoplay-audio` (WCAG 1.4.2, A)

- `<video autoplay>` or `<audio autoplay>` longer than 3 seconds
  must offer a control to stop or mute.

### `server-side-image-map` (WCAG 2.1.1, A)

- `<img ismap>` (server-side maps) is keyboard-inaccessible.

---

## Needs runtime axe-core (skip in static review)

- `bypass`: checks for skip links, requires layout.
- `region`: checks landmark coverage of all rendered content.
- `scrollable-region-focusable`: needs computed overflow.
- `frame-tested`: runs axe inside each frame.

If the user has a live URL, recommend:

```
npx @axe-core/cli <url> --tags wcag2a,wcag2aa,wcag21a,wcag21aa
```
