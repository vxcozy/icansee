# WCAG contrast thresholds

The numbers Claude needs when answering "does this pass?". Match the
WCAG 2.2 spec and what axe-core enforces.

## 1.4.3 Contrast (Minimum), Level AA

| Content                    | Required ratio |
| -------------------------- | -------------- |
| Body text (normal)         | **4.5 : 1**    |
| Large text                 | **3 : 1**      |

**Large text** = 18pt+ regular, **or** 14pt+ bold. In CSS terms with a
16px base, that's roughly `font-size: 24px` (regular) or
`font-size: 18.66px` with `font-weight: 700+`. Anything smaller falls
under the 4.5:1 rule.

## 1.4.6 Contrast (Enhanced), Level AAA

| Content                    | Required ratio |
| -------------------------- | -------------- |
| Body text (normal)         | **7 : 1**      |
| Large text                 | **4.5 : 1**    |

## 1.4.11 Non-text Contrast, Level AA

**3 : 1** against adjacent colors for:

- **UI components**: visual information needed to identify or operate a
  control. Includes borders of inputs, the focus ring, the
  checked/unchecked state of a checkbox, the thumb of a slider, and the
  boundary of a button when not conveyed by text alone.
- **Graphical objects**: parts of a chart or icon required to understand
  it (the bars of a bar chart against the plot background, for
  instance).

Decorative borders, dividers, and shadows are **not** subject to 1.4.11.

## 1.4.1 Use of Color, Level A

Color must not be the **only** visual means of conveying information,
indicating an action, prompting a response, or distinguishing an
element. Examples that fail:

- Required form fields shown only by red label text.
- Errors shown only by red borders with no icon, text, or aria
  attribute.
- Inline links indicated only by color (also covered by
  `link-in-text-block`).

## 2.5.8 Target Size (Minimum), WCAG 2.2 AA

Pointer targets must be **24 × 24 CSS px** or larger, except where the
target is inline in a sentence, the user-agent default, or the target is
essential. Spacing also counts: a smaller target with a 24px-radius
exclusion zone is OK.

## What "incidental" means (exempt from 1.4.3 and 1.4.6)

- **Disabled** form controls (with the `disabled` attribute, not just
  styled to look disabled).
- Pure decoration. Text that is not visible to anyone, or is part of a
  picture that has significant other visual content.
- Logotypes. Text that is part of a logo or brand name.

## Operational notes for Claude

- Always composite a translucent foreground (`rgba(...)`, `#rrggbbaa`,
  `opacity` < 1) over the **actual** opaque canvas before measuring.
  `contrast.py` does this automatically when you pass both colors.
- Gradient backgrounds: measure the foreground against the **worst-case**
  stop it overlaps. axe-core uses the same heuristic.
- Text on images and video: not statically checkable. Flag it as needing
  manual review and recommend a solid-color overlay or text shadow.
- Do not "round up" near a threshold. 4.49 : 1 fails AA; say so.
